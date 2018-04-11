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
        return self._dimension

    @dimension.setter
    def dimension(self, dimension):
        self._dimension = dimension
        self._asset_type = AssetType.type_instance(dimension)

    def apply(self, transaction, context):
        txn_header = transaction.header
        public_key = txn_header.signer_public_key

        asset_payload = AssetPayload()
        asset_payload.ParseFromString(transaction.payload)
        self.dimension = asset_payload.dimension
        LOGGER.debug("Received transaction for {}".format(self.dimension))

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
        if approval_threshold > 1:
            asset_candidates = self._get_candidates(context)
            LOGGER.debug("Candidates = {}".format(asset_candidates))
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
            self.asset_type.asset_from_proposal(asset_proposal)
            _set_asset(context, self.asset_type)
            LOGGER.debug('Set asset {}'.format(self.asset_type.asset))

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
        self.asset_type.asset_from_proposal(candidate.proposal)
        for vote_record in candidate.votes:
            if vote_record.vote == AssetVote.ACCEPT:
                accepted_count += 1
            elif vote_record.vote == AssetVote.REJECT:
                rejected_count += 1

        if accepted_count >= approval_threshold:
            _set_asset(context, self.asset_type)
            LOGGER.debug('Set asset {}'.format(self.asset_type.asset))
            del asset_candidates.candidates[candidate_index]
        elif rejected_count >= approval_threshold or \
                (rejected_count + accepted_count) == len(authorized_keys):
            LOGGER.debug(
                'Proposal for {} was rejected'.format(self.asset_type.asset))
            del asset_candidates.candidates[candidate_index]
        else:
            LOGGER.debug('Vote recorded for {}'.format(self.asset_type.asset))
            _set_candidates(context, asset_candidates)

    def _get_candidates(self, context):
        candidates = _get_candidates(
            context,
            self.asset_type.candidates_address)
        if not candidates:
            raise InvalidTransaction(
                'Candidates for {} '
                'must exist.'.format(self.dimension))

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
                'must not be empty.'.format(self.dimension))

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
                'must not be empty.'.format(self.dimension))


def _validate_asset(auth_keys, units_code, value):
    pass


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


def _set_candidates(context, address, candidates):
    addresses = _set_state(context, address, candidates)
    if len(addresses) != 1:
        LOGGER.warning(
            'Failed to save candidates on address %s', address)
        raise InternalError(
            'Unable to save candidate block value {}'.format(candidates))


def _set_asset(context, asset_type):
    # Use address to see if entry type exists
    # If exists, update with current type entry
    # set entry

    # Get an empty from the type
    # Get the address and pass to _get_asset_entry
    address = asset_type.asset_address
    addresses = list(_set_state(address, asset_type.asset))

    if len(addresses) != 1:
        LOGGER.warning(
            'Failed to save value on address %s', address)
        raise InternalError(
            'Unable to save asset {}'.format(address))
    context.add_event(
        event_type="hashbloc.asset/update",
        attributes=[("updated", address)])


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


def _string_tolist(s):
    """Convert the authorization comma separated string to list
    """
    return [v.strip() for v in s.split(',') if v]


def _first(a_list, pred):
    return next((x for x in a_list if pred(x)), None)


def _index_of(iterable, obj):
    return next((i for i, x in enumerate(iterable) if x == obj), -1)
