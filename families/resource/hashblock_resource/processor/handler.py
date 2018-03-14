# ------------------------------------------------------------------------------
# Copyright 2018 Frank V. Castellucci
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ------------------------------------------------------------------------------

import logging
import hashlib
import base64
from functools import lru_cache


from sawtooth_sdk.processor.handler import TransactionHandler
from sawtooth_sdk.messaging.future import FutureTimeoutError
from sawtooth_sdk.processor.exceptions import InvalidTransaction
from sawtooth_sdk.processor.exceptions import InternalError

from protobuf.resource_pb2 import ResourcePayload
from protobuf.resource_pb2 import ResourceProposal
from protobuf.resource_pb2 import ResourceVote
from protobuf.resource_pb2 import ResourceCandidate
from protobuf.resource_pb2 import ResourceCandidates
from protobuf.resource_pb2 import Resource

LOGGER = logging.getLogger(__name__)

ADDRESS_PREFIX = 'resource'
FAMILY_NAME = 'hashblock_resource'

RESOURCE_ADDRESS_PREFIX = hashlib.sha512(
    FAMILY_NAME.encode('utf-8')).hexdigest()[0:6]


# Number of seconds to wait for state operations to succeed
STATE_TIMEOUT_SEC = 10


class ResourceTransactionHandler(TransactionHandler):

    @property
    def family_name(self):
        return FAMILY_NAME

    @property
    def family_versions(self):
        return ['0.1.0']

    @property
    def namespaces(self):
        return [RESOURCE_ADDRESS_PREFIX]

    def apply(self, transaction, context):
        txn_header = transaction.header
        public_key = txn_header.signer_public_key

        auth_keys = _get_auth_keys(context)
        if auth_keys and public_key not in auth_keys:
            raise InvalidTransaction(
                '{} is not authorized to change units'.format(public_key))

        resource_payload = ResourcePayload()
        resource_payload.ParseFromString(transaction.payload)

        if resource_payload.action == ResourcePayload.PROPOSE:
            return self._apply_proposal(
                auth_keys, public_key, resource_payload.data, context)
        elif resource_payload.action == ResourcePayload.VOTE:
            return self._apply_vote(public_key, resource_payload.data,
                                    auth_keys, context)
        else:
            raise InvalidTransaction(
                "'action' must be one of {PROPOSE, VOTE} in 'Ballot' mode")

    def _apply_proposal(self, auth_keys, public_key,
                        resource_proposal_data, context):
        resource_proposal = ResourceProposal()
        resource_proposal.ParseFromString(resource_proposal_data)

        proposal_id = hashlib.sha256(resource_proposal_data).hexdigest()

        approval_threshold = _get_approval_threshold(context)

        _validate_resource(
            auth_keys,
            resource_proposal.code,
            resource_proposal.value)

        if approval_threshold > 1:
            resource_candidates = _get_resource_candidates(context)

            existing_candidate = _first(
                resource_candidates.candidates,
                lambda candidate: candidate.proposal_id == proposal_id)

            if existing_candidate is not None:
                raise InvalidTransaction(
                    'Duplicate proposal for {}'.format(
                        resource_proposal.code))

            record = ResourceCandidate.VoteRecord(
                public_key=public_key,
                vote=ResourceVote.ACCEPT)
            resource_candidates.candidates.add(
                proposal_id=proposal_id,
                proposal=resource_proposal,
                votes=[record]
            )

            LOGGER.debug('Proposal made to set %s to %s',
                         resource_proposal.code,
                         resource_proposal.value)
            _save_resource_candidates(context, resource_candidates)
        else:
            _set_resource_value(
                context,
                resource_proposal.code,
                resource_proposal.value)

    def _apply_vote(self, public_key,
                    resource_vote_data, authorized_keys, context):
        resource_vote = ResourceVote()
        resource_vote.ParseFromString(resource_vote_data)
        proposal_id = resource_vote.proposal_id

        resource_candidates = _get_resource_candidates(context)
        candidate = _first(
            resource_candidates.candidates,
            lambda candidate: candidate.proposal_id == proposal_id)

        if candidate is None:
            raise InvalidTransaction(
                "Proposal {} does not exist.".format(proposal_id))

        candidate_index = _index_of(resource_candidates.candidates, candidate)

        approval_threshold = _get_approval_threshold(context)

        vote_record = _first(candidate.votes,
                             lambda record: record.public_key == public_key)
        if vote_record is not None:
            raise InvalidTransaction(
                '{} has already voted'.format(public_key))

        candidate.votes.add(
            public_key=public_key,
            vote=resource_vote.vote)

        accepted_count = 0
        rejected_count = 0
        for vote_record in candidate.votes:
            if vote_record.vote == ResourceVote.ACCEPT:
                accepted_count += 1
            elif vote_record.vote == ResourceVote.REJECT:
                rejected_count += 1

        if accepted_count >= approval_threshold:
            _set_resource_value(
                context,
                candidate.proposal.code,
                candidate.proposal.value)
            del resource_candidates.candidates[candidate_index]
        elif rejected_count >= approval_threshold or \
                (rejected_count + accepted_count) == len(authorized_keys):
            LOGGER.debug('Proposal for %s was rejected',
                         candidate.proposal.code)
            del resource_candidates.candidates[candidate_index]
        else:
            LOGGER.debug('Vote recorded for %s',
                         candidate.proposal.code)

        _save_resource_candidates(context, resource_candidates)


def _get_resource_candidates(context):
    value = _get_resource_value(context, 'hashblock.resource.vote.proposals')
    if not value:
        return ResourceCandidates(candidates={})

    unit_candidates = ResourceCandidates()
    unit_candidates.ParseFromString(base64.b64decode(value))
    return unit_candidates


def _save_resource_candidates(context, resource_candidates):
    _set_resource_value(
        context,
        'hashblock.resource.vote.proposals',
        base64.b64encode(resource_candidates.SerializeToString()))


def _get_approval_threshold(context):
    return int(_get_resource_value(
        context, 'hashblock.resource.vote.approval_threshold', 1))


def _get_auth_keys(context):
    value = _get_resource_value(
        context, 'hashblock.resource.vote.authorized_keys', '')
    return _split_ignore_empties(value)


def _split_ignore_empties(value):
    return [v.strip() for v in value.split(',') if v]


def _validate_resource(auth_keys, resource_code, value):
    if not auth_keys and \
            resource_code != 'hashblock.resource.vote.authorized_keys':
        raise InvalidTransaction(
            'Cannot set {} until authorized_keys is set.'.format(resource_code))

    if resource_code == 'hashblock.resource.vote.authorized_keys':
        if not _split_ignore_empties(value):
            raise InvalidTransaction('authorized_keys must not be empty.')

    if resource_code == 'hashblock.resource.vote.approval_threshold':
        threshold = None
        try:
            threshold = int(value)
        except ValueError:
            raise InvalidTransaction('approval_threshold must be an integer')

        if threshold > len(auth_keys):
            raise InvalidTransaction(
                'approval_threshold must be less than or equal to number of '
                'authorized_keys')

    if resource_code == 'hashblock.resource.vote.proposals':
        raise InvalidTransaction(
            'Setting hashblock.resource.vote.proposals is read-only')


def _get_resource_value(context, key, default_value=None):
    address = _make_resource_key(key)
    resource_entry = _get_resource_entry(context, address)
    for entry in resource_entry.entries:
        if key == entry.key:
            return entry.value

    return default_value


def _set_resource_value(context, key, value):
    address = _make_resource_key(key)
    setting = _get_resource_entry(context, address)

    old_value = None
    old_entry_index = None
    for i, entry in enumerate(setting.entries):
        if key == entry.key:
            old_value = entry.value
            old_entry_index = i

    if old_entry_index is not None:
        setting.entries[old_entry_index].value = value
    else:
        setting.entries.add(key=key, value=value)

    try:
        addresses = list(context.set_state(
            {address: setting.SerializeToString()},
            timeout=STATE_TIMEOUT_SEC))
    except FutureTimeoutError:
        LOGGER.warning(
            'Timeout occured on context.set_state([%s, <value>])', address)
        raise InternalError('Unable to set {}'.format(key))

    if len(addresses) != 1:
        LOGGER.warning(
            'Failed to save value on address %s', address)
        raise InternalError(
            'Unable to save config value {}'.format(key))
    if setting != 'hashblock.resource.vote.proposals':
        LOGGER.info('Resource setting %s changed from %s to %s',
                    key, old_value, value)
    context.add_event(
        event_type="hashblock.resource.update",
        attributes=[("updated", key)])


def _get_resource_entry(context, address):
    resource_setting = Resource()

    try:
        entries_list = context.get_state([address], timeout=STATE_TIMEOUT_SEC)
    except FutureTimeoutError:
        LOGGER.warning('Timeout occured on context.get_state([%s])', address)
        raise InternalError('Unable to get {}'.format(address))

    if entries_list:
        resource_setting.ParseFromString(entries_list[0].data)

    return resource_setting


def _to_hash(value):
    return hashlib.sha256(value.encode()).hexdigest()


def _first(a_list, pred):
    return next((x for x in a_list if pred(x)), None)


def _index_of(iterable, obj):
    return next((i for i, x in enumerate(iterable) if x == obj), -1)


_MAX_KEY_PARTS = 4
_ADDRESS_PART_SIZE = 16
_EMPTY_PART = _to_hash('')[:_ADDRESS_PART_SIZE]


@lru_cache(maxsize=128)
def _make_resource_key(key):
    # split the key into 4 parts, maximum
    key_parts = key.split('.', maxsplit=_MAX_KEY_PARTS - 1)
    # compute the short hash of each part
    addr_parts = [_to_hash(x)[:_ADDRESS_PART_SIZE] for x in key_parts]
    # pad the parts with the empty hash, if needed
    addr_parts.extend([_EMPTY_PART] * (_MAX_KEY_PARTS - len(addr_parts)))

    return RESOURCE_ADDRESS_PREFIX + ''.join(addr_parts)
