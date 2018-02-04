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

from protobuf.unit_pb2 import UOMPayload
from protobuf.unit_pb2 import UOMProposal
from protobuf.unit_pb2 import UOMVote
from protobuf.unit_pb2 import UOMCandidate
from protobuf.unit_pb2 import UOMCandidates
from protobuf.units_pb2 import UOM

LOGGER = logging.getLogger(__name__)


# The config namespace is special: it is not derived from a hash.
SETTINGS_NAMESPACE = '000000'

# Number of seconds to wait for state operations to succeed
STATE_TIMEOUT_SEC = 10


class UOMTransactionHandler(TransactionHandler):
    @property
    def family_name(self):
        return 'sawtooth_uom'

    @property
    def family_versions(self):
        return ['1.0']

    @property
    def namespaces(self):
        return [SETTINGS_NAMESPACE]

    def apply(self, transaction, context):
        txn_header = transaction.header
        public_key = txn_header.signer_public_key

        auth_keys = _get_auth_keys(context)
        if auth_keys and public_key not in auth_keys:
            raise InvalidTransaction(
                '{} is not authorized to change settings'.format(public_key))

        uom_payload = UOMPayload()
        uom_payload.ParseFromString(transaction.payload)

        if uom_payload.action == UOMPayload.PROPOSE:
            return self._apply_proposal(
                auth_keys, public_key, uom_payload.data, context)
        elif uom_payload.action == UOMPayload.VOTE:
            return self._apply_vote(public_key, uom_payload.data,
                                    auth_keys, context)
        else:
            raise InvalidTransaction(
                "'action' must be one of {PROPOSE, VOTE} in 'Ballot' mode")

    def _apply_proposal(self, auth_keys, public_key,
                        uom_proposal_data, context):
        uom_proposal = UOMProposal()
        uom_proposal.ParseFromString(uom_proposal_data)

        proposal_id = hashlib.sha256(uom_proposal_data).hexdigest()

        approval_threshold = _get_approval_threshold(context)

        _validate_uom(
            auth_keys,
            uom_proposal.setting,
            uom_proposal.value)

        if approval_threshold > 1:
            uom_candidates = _get_uom_candidates(context)

            existing_candidate = _first(
                uom_candidates.candidates,
                lambda candidate: candidate.proposal_id == proposal_id)

            if existing_candidate is not None:
                raise InvalidTransaction(
                    'Duplicate proposal for {}'.format(
                        uom_proposal.setting))

            record = UOMCandidate.VoteRecord(
                public_key=public_key,
                vote=UOMVote.ACCEPT)
            uom_candidates.candidates.add(
                proposal_id=proposal_id,
                proposal=uom_proposal,
                votes=[record]
            )

            LOGGER.debug('Proposal made to set %s to %s',
                         uom_proposal.setting,
                         uom_proposal.value)
            _save_uom_candidates(context, uom_candidates)
        else:
            _set_uom_value(
                context,
                uom_proposal.setting,
                uom_proposal.value)

    def _apply_vote(self, public_key,
                    uom_vote_data, authorized_keys, context):
        uom_vote = UOMVote()
        uom_vote.ParseFromString(uom_vote_data)
        proposal_id = uom_vote.proposal_id

        uom_candidates = _get_uom_candidates(context)
        candidate = _first(
            uom_candidates.candidates,
            lambda candidate: candidate.proposal_id == proposal_id)

        if candidate is None:
            raise InvalidTransaction(
                "Proposal {} does not exist.".format(proposal_id))

        candidate_index = _index_of(uom_candidates.candidates, candidate)

        approval_threshold = _get_approval_threshold(context)

        vote_record = _first(candidate.votes,
                             lambda record: record.public_key == public_key)
        if vote_record is not None:
            raise InvalidTransaction(
                '{} has already voted'.format(public_key))

        candidate.votes.add(
            public_key=public_key,
            vote=uom_vote.vote)

        accepted_count = 0
        rejected_count = 0
        for vote_record in candidate.votes:
            if vote_record.vote == UOMVote.ACCEPT:
                accepted_count += 1
            elif vote_record.vote == UOMVote.REJECT:
                rejected_count += 1

        if accepted_count >= approval_threshold:
            _set_uom_value(
                context,
                candidate.proposal.setting,
                candidate.proposal.value)
            del uom_candidates.candidates[candidate_index]
        elif rejected_count >= approval_threshold or \
                (rejected_count + accepted_count) == len(authorized_keys):
            LOGGER.debug('Proposal for %s was rejected',
                         candidate.proposal.setting)
            del uom_candidates.candidates[candidate_index]
        else:
            LOGGER.debug('Vote recorded for %s',
                         candidate.proposal.setting)

        _save_uom_candidates(context, uom_candidates)


def _get_uom_candidates(context):
    value = _get_uom_value(context, 'sawtooth.uom.vote.proposals')
    if not value:
        return UOMCandidates(candidates={})

    setting_candidates = UOMCandidates()
    setting_candidates.ParseFromString(base64.b64decode(value))
    return setting_candidates


def _save_uom_candidates(context, uom_candidates):
    _set_uom_value(
        context,
        'sawtooth.uom.vote.proposals',
        base64.b64encode(uom_candidates.SerializeToString()))


def _get_approval_threshold(context):
    return int(_get_uom_value(
        context, 'sawtooth.uom.vote.approval_threshold', 1))


def _get_auth_keys(context):
    value = _get_uom_value(
        context, 'sawtooth.uom.vote.authorized_keys', '')
    return _split_ignore_empties(value)


def _split_ignore_empties(value):
    return [v.strip() for v in value.split(',') if v]


def _validate_uom(auth_keys, uom_setting, value):
    if not auth_keys and \
            uom_setting != 'sawtooth.uom.vote.authorized_keys':
        raise InvalidTransaction(
            'Cannot set {} until authorized_keys is set.'.format(uom_setting))

    if uom_setting == 'sawtooth.uom.vote.authorized_keys':
        if not _split_ignore_empties(value):
            raise InvalidTransaction('authorized_keys must not be empty.')

    if uom_setting == 'sawtooth.uom.vote.approval_threshold':
        threshold = None
        try:
            threshold = int(value)
        except ValueError:
            raise InvalidTransaction('approval_threshold must be an integer')

        if threshold > len(auth_keys):
            raise InvalidTransaction(
                'approval_threshold must be less than or equal to number of '
                'authorized_keys')

    if uom_setting == 'sawtooth.uom.vote.proposals':
        raise InvalidTransaction(
            'Setting sawtooth.uom.vote.proposals is read-only')


def _get_uom_value(context, key, default_value=None):
    address = _make_uom_key(key)
    uom_entry = _get_uom_entry(context, address)
    for entry in uom_entry.entries:
        if key == entry.key:
            return entry.value

    return default_value


def _set_uom_value(context, key, value):
    address = _make_uom_key(key)
    setting = _get_uom_entry(context, address)

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
    if setting != 'sawtooth.uom.vote.proposals':
        LOGGER.info('UOM setting %s changed from %s to %s',
                    key, old_value, value)
    context.add_event(
        event_type="uom/update",
        attributes=[("updated", key)])


def _get_uom_entry(context, address):
    uom_setting = UOM()

    try:
        entries_list = context.get_state([address], timeout=STATE_TIMEOUT_SEC)
    except FutureTimeoutError:
        LOGGER.warning('Timeout occured on context.get_state([%s])', address)
        raise InternalError('Unable to get {}'.format(address))

    if entries_list:
        uom_setting.ParseFromString(entries_list[0].data)

    return uom_setting


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
def _make_uom_key(key):
    # split the key into 4 parts, maximum
    key_parts = key.split('.', maxsplit=_MAX_KEY_PARTS - 1)
    # compute the short hash of each part
    addr_parts = [_to_hash(x)[:_ADDRESS_PART_SIZE] for x in key_parts]
    # pad the parts with the empty hash, if needed
    addr_parts.extend([_EMPTY_PART] * (_MAX_KEY_PARTS - len(addr_parts)))

    return SETTINGS_NAMESPACE + ''.join(addr_parts)
