# ------------------------------------------------------------------------------
# Copyright 2018 Frank V. Castellucci and Arthur Greef
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

from protobuf.setting_pb2 import Settings
from protobuf.asset_pb2 import AssetPayload
from protobuf.asset_pb2 import AssetProposal
from protobuf.asset_pb2 import AssetVote
from protobuf.asset_pb2 import AssetCandidate
from protobuf.asset_pb2 import AssetCandidates
from processor.asset_type import AssetType

from sdk.python.address import Address

LOGGER = logging.getLogger(__name__)
ADDRESS = ''


# Number of seconds to wait for state operations to succeed
STATE_TIMEOUT_SEC = 10


class AssetTransactionHandler(TransactionHandler):

    def __init__(self):
        self._addresser = Address(Address.FAMILY_ASSET)
        self._auth_list = None
        self._action = None

    @property
    def family_name(self):
        return Address.NAMESPACE_ASSET

    @property
    def family_versions(self):
        return ['1.0.0']

    @property
    def namespaces(self):
        return [Address(Address.FAMILY_ASSET).ns_family]

    @property
    def asset_type(self):
        return self._asset_type

    @property
    def dimension(self):
        return [self._dimension]

    @dimension.setter
    def dimension(self, dimension):
        self._dimension = dimension
        self._asset_type = AssetType.type_instance(dimension)

    def apply(self, transaction, context):
        txn_header = transaction.header
        public_key = txn_header.signer_public_key

        asset_payload = AssetPayload()
        asset_payload.ParseFromString(transaction.payload)
        self.domain = asset_payload.domain

        auth_keys = self._get_auth_keys(context, self.asset_type)
        if auth_keys and public_key not in auth_keys:
            raise InvalidTransaction(
                '{} is not authorized to change asset'.format(public_key))

        if asset_payload.action == AssetPayload.PROPOSE:
            return self._apply_proposal(
                public_key,
                asset_payload.data,
                context)
        elif asset_payload.action == AssetPayload.VOTE:
            return self._apply_vote(
                public_key,
                asset_payload.data,
                auth_keys,
                context)
        else:
            raise InvalidTransaction(
                "'action' must be one of {PROPOSE, VOTE}")

    def _apply_proposal(self, public_key,
                        asset_proposal_data, context):
        asset_proposal = AssetProposal()
        asset_proposal.ParseFromString(asset_proposal_data)

        proposal_id = hashlib.sha256(asset_proposal_data).hexdigest()
        approval_threshold = self._get_approval_threshold(
            context,
            self.asset_type)

        # _validate_asset(
        #     auth_keys,
        #     asset_proposal.code,
        #     asset_proposal.value)

        if approval_threshold > 1:
            asset_candidates = self._get_candidates(context)

            existing_candidate = _first(
                asset_candidates.candidates,
                lambda candidate: candidate.proposal_id == proposal_id)

            if existing_candidate is not None:
                raise InvalidTransaction(
                    'Duplicate proposal for {}'.format(
                        asset_proposal.type))

            record = AssetCandidate.VoteRecord(
                public_key=public_key,
                vote=AssetVote.ACCEPT)
            asset_candidates.candidates.add(
                proposal_id=proposal_id,
                proposal=asset_proposal,
                votes=[record]
            )

            LOGGER.debug('Proposal made to create {}'
                         .format(asset_proposal.asset))
            self._set_candidates(context, asset_candidates)
        else:
            _set_asset_entry(
                context,
                asset_proposal.type,
                asset_proposal.asset)

    def _apply_vote(self, public_key,
                    asset_vote_data, authorized_keys, context):
        asset_vote = AssetVote()
        asset_vote.ParseFromString(asset_vote_data)
        proposal_id = asset_vote.proposal_id

        asset_candidates = self._get_candidates(context)
        candidate = _first(
            asset_candidates.candidates,
            lambda candidate: candidate.proposal_id == proposal_id)

        if candidate is None:
            raise InvalidTransaction(
                "Proposal {} does not exist.".format(proposal_id))

        candidate_index = _index_of(asset_candidates.candidates, candidate)

        approval_threshold = self._get_approval_threshold(context)

        vote_record = _first(candidate.votes,
                             lambda record: record.public_key == public_key)
        if vote_record is not None:
            raise InvalidTransaction(
                '{} has already voted'.format(public_key))

        candidate.votes.add(
            public_key=public_key,
            vote=asset_vote.vote)

        accepted_count = 0
        rejected_count = 0
        for vote_record in candidate.votes:
            if vote_record.vote == AssetVote.ACCEPT:
                accepted_count += 1
            elif vote_record.vote == AssetVote.REJECT:
                rejected_count += 1

        if accepted_count >= approval_threshold:
            _set_units_value(
                context,
                candidate.proposal.code,
                candidate.proposal.value)
            del asset_candidates.candidates[candidate_index]
        elif rejected_count >= approval_threshold or \
                (rejected_count + accepted_count) == len(authorized_keys):
            LOGGER.debug('Proposal for %s was rejected',
                         candidate.proposal.code)
            del asset_candidates.candidates[candidate_index]
        else:
            LOGGER.debug('Vote recorded for %s',
                         candidate.proposal.code)

        _set_candidates(context, asset_candidates)

    def _get_candidates(self, context):
        candidates = _get_candidates(
            context,
            self.asset_type.candidates_address)
        if not candidates:
            raise InvalidTransaction(
                'Proposals for {} '
                'must exist.'.format(self.domain))

        return candidates

    def _set_candidates(self, context, candidates):
        _set_candidates(
            context,
            self.asset_type.candidates_address, candidates)
        pass

    def _get_auth_keys(self, context, asset_type):
        """Retrieve the authorization keys for dimension
        """
        if not asset_type.settings:
            asset_type.settings = _get_setting(
                context,
                asset_type.setting_address)

        if asset_type.settings:
            return _string_tolist(asset_type.settings.auth_list)
        else:
            raise InvalidTransaction(
                'Asset auth_list settings for {} '
                'must not be empty.'.format(self.domain))

    def _get_approval_threshold(self, context, asset_type):
        """Retrieve the threshold setting for dimension
        """
        if not asset_type.settings:
            asset_type.settings = _get_setting(
                context,
                asset_type.setting_address)

        if asset_type.settings:
            return int(asset_type.settings.threshold)
        else:
            raise InvalidTransaction(
                'Asset threshold settings for {} '
                'must not be empty.'.format(self.domain))


def _save_units_candidates(context, units_candidates):
    _set_units_value(
        context,
        'hashblock.units.vote.proposals',
        base64.b64encode(units_candidates.SerializeToString()))


def _split_ignore_empties(value):
    return [v.strip() for v in value.split(',') if v]


def _validate_asset(auth_keys, units_code, value):
    pass


def _get_units_value(context, asset, address, default_value=None):
    units_entry = _get_asset_entry(context, address)
    for entry in units_entry.entries:
        if key == entry.key:
            return entry.value

    return default_value


def _set_units_value(context, key, value):
    address = _make_units_key(key)
    setting = _get_units_entry(context, address)

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
    if setting != 'hashblock.units.vote.proposals':
        LOGGER.info('Unit setting %s changed from %s to %s',
                    key, old_value, value)
    context.add_event(
        event_type="units/update",
        attributes=[("updated", key)])


def _set_asset_entry(context, asset_type):
    # Use address to see if entry type exists
    # If exists, update with current type entry
    # set entry

    # Get an empty from the type
    # Get the address and pass to _get_asset_entry

    pass


def _get_asset_entry(context, asset, address):

    try:
        entries_list = context.get_state([address], timeout=STATE_TIMEOUT_SEC)
    except FutureTimeoutError:
        LOGGER.warning('Timeout occured on context.get_state([%s])', address)
        raise InternalError('Unable to get {}'.format(address))

    if entries_list:
        asset.ParseFromString(entries_list[0].data)

    return asset


def _string_tolist(s):
    """Convert the authorization comma separated string to list
    """
    return [v.strip() for v in s.split(',') if v]


def _get_setting(context, address, default_value=None):
    """Get a hashblock settings from the block
    """
    setting = Settings()
    results = _get_state(context, address)
    if results:
        setting.ParseFromString(results[0].data)
        return setting
    return default_value


def _get_candidates(context, address, default_value=None):
    candidates = AssetCandidates()
    results = _get_state(context, address)
    if results:
        candidates.ParseFromString(results[0].data)
        return candidates
    return default_value


def _set_candidates(context, address, candidates):
    addresses = _set_state(context, address, candidates)
    if len(addresses) != 1:
        LOGGER.warning(
            'Failed to save candidates on address %s', address)
        raise InternalError(
            'Unable to save candidate block value {}'.format(candidates))


def _get_state(context, address):
    try:
        results = context.get_state([address], timeout=STATE_TIMEOUT_SEC)
    except FutureTimeoutError:
        raise InternalError('State timeout: Unable to get {}'.format(address))
    return results


def _set_state(context, address, object):
    try:
        addresses = list(context.set_state(
            {address: object.SerializeToString()},
            timeout=STATE_TIMEOUT_SEC))
    except FutureTimeoutError:
        raise InternalError('State timeout: Unable to set {}'.format(object))

    return addresses


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
def _make_units_key(key):
    # split the key into 4 parts, maximum
    key_parts = key.split('.', maxsplit=_MAX_KEY_PARTS - 1)
    # compute the short hash of each part
    addr_parts = [_to_hash(x)[:_ADDRESS_PART_SIZE] for x in key_parts]
    # pad the parts with the empty hash, if needed
    addr_parts.extend([_EMPTY_PART] * (_MAX_KEY_PARTS - len(addr_parts)))

    return ADDRESS + ''.join(addr_parts)
