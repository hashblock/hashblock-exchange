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

import hashlib

from protobuf.setting_pb2 import Settings
from protobuf.asset_pb2 import AssetProposal
from protobuf.asset_pb2 import AssetVote
from protobuf.asset_pb2 import AssetCandidate
from protobuf.asset_pb2 import AssetCandidates
from protobuf.asset_pb2 import Unit
from protobuf.asset_pb2 import Resource

from hashblock_asset_test.asset_message_factory \
    import AssetMessageFactory

from sawtooth_processor_test.transaction_processor_test_case \
    import TransactionProcessorTestCase

from sdk.python.address import Address

_asset_addr = Address(Address.FAMILY_ASSET)
_setting_addr = Address(Address.FAMILY_SETTING)


def _to_hash(value):
    return hashlib.sha256(value).hexdigest()


EMPTY_CANDIDATES = AssetCandidates(candidates=[]).SerializeToString()


class TestAsset(TransactionProcessorTestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.factory = AssetMessageFactory()
        cls.setting_keys = [
            cls.factory.public_key,
            "59c272cb554c7100dd6c1e38b5c77f158146be29373329e503bfcb81e70d1ddd"]
        cls.setting = Settings(
            auth_list=','.join(cls.setting_keys),
            threshold='2').SerializeToString()

    def _expect_get(self, address, data):
        received = self.validator.expect(
            self.factory.create_get_request(address))
        self.validator.respond(
            self.factory.create_get_response(address, data),
            received)

    def _expect_set(self, address, expected_value):
        received = self.validator.expect(
            self.factory.create_set_request(address, expected_value))
        self.validator.respond(
            self.factory.create_set_response(address), received)

    def _expect_add_event(self, key):
        received = self.validator.expect(
            self.factory.create_add_event_request(key))

        self.validator.respond(
            self.factory.create_add_event_response(),
            received)

    def _expect_ok(self):
        self.validator.expect(self.factory.create_tp_response("OK"))

    def _expect_invalid_transaction(self):
        self.validator.expect(
            self.factory.create_tp_response("INVALID_TRANSACTION"))

    def _expect_internal_error(self):
        self.validator.expect(
            self.factory.create_tp_response("INTERNAL_ERROR"))

    def _get_setting(self, dimension):
        self._expect_get(
            _setting_addr.settings(dimension),
            self.setting)

    def _get_empty_candidates(self, dimension):
        self._expect_get(
            _asset_addr.candidates(dimension),
            EMPTY_CANDIDATES)

    def _propose(self, asset, dimension):
        self.validator.send(self.factory.create_proposal_transaction(
            asset, dimension, "somenonce"))

    def _vote(self, proposal_id, asset, dimension, vote):
        self.validator.send(self.factory.create_vote_transaction(
            proposal_id, asset, dimension, vote))

    @property
    def _public_key(self):
        return self.factory.public_key

    def _build_first_candidate(self, asset, dimension):
        proposal_id = _asset_addr.asset_item(
            dimension, asset.system, asset.key)
        proposal = AssetProposal(
            asset=asset.SerializeToString(),
            type=AssetProposal.UNIT
            if dimension is Address.DIMENSION_UNIT
            else AssetProposal.RESOURCE,
            nonce="somenonce")
        record = AssetCandidate.VoteRecord(
            public_key=self._public_key,
            vote=AssetVote.ACCEPT)
        return AssetCandidates(candidates=[
            AssetCandidate(
                proposal_id=proposal_id,
                proposal=proposal,
                votes=[record])]).SerializeToString()

    def _test_valid_propose(self, asset, dimension):
        """Sunny day proposal for asset type
        """
        self._propose(asset, dimension)
        self._get_setting(dimension)
        self._get_empty_candidates(dimension)
        self._expect_set(
            _asset_addr.candidates(dimension),
            self._build_first_candidate(
                asset,
                dimension))
        self._expect_ok()

    def test_propose_asset_unit(self):
        """Test a valid proposition for unit-of-measure asset
        This assumes basic setting and empty candidates in state
        """
        unit = Unit(system="imperial", key='unity', value='1')
        self._test_valid_propose(unit, Address.DIMENSION_UNIT)

    def test_propose_asset_resource(self):
        """Test a valid proposition for resource asset
        This assumes basic setting and empty candidates in state
        """
        resource = Resource(system="imperial", key='peanuts', value='food')
        self._test_valid_propose(resource, Address.DIMENSION_RESOURCE)

    # def test_vote_asset_unit(self):
    #     """Test a valid vote for unit-of-measure asset
    #     This assumes setting and candidates in state
    #     """
    #     pass


    # def test_vote_asset_resource(self):
    #     """Test a valid vote for resource asset
    #     This assumes setting and candidates in state
    #     """
    #     pass
