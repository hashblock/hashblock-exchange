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

from modules.address import Address

_asset_addr = Address(Address.FAMILY_ASSET)
_setting_addr = Address(Address.FAMILY_SETTING)

VOTER2 = "59c272cb554c7100dd6c1e38b5c77f158146be29373329e503bfcb81e70d1ddd"


EMPTY_CANDIDATES = AssetCandidates(candidates=[]).SerializeToString()


class TestAsset(TransactionProcessorTestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.factory = AssetMessageFactory()
        cls.setting = Settings(
            auth_list=','.join([cls.factory.public_key, VOTER2]),
            threshold='2').SerializeToString()
        cls.unit = Unit(system="imperial", key='unity', value='1')
        cls.resource = Resource(system="imperial", key='peanuts', value='food')

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

    def _expect_add_event(self, address):
        received = self.validator.expect(
            self.factory.create_add_event_request(address))

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

    def _set_empty_candidates(self, dimension):
        self._expect_set(
            _asset_addr.candidates(dimension),
            EMPTY_CANDIDATES)

    def _propose(self, asset, dimension):
        self.validator.send(self.factory.create_proposal_transaction(
            asset, dimension, "somenonce"))

    def _vote(self, proposal_id, asset, dimension, vote):
        self.validator.send(self.factory.create_vote_transaction(
            proposal_id, asset, dimension, vote))

    def _unset_vote(self, proposal_id, asset, dimension, vote):
        self.validator.send(self.factory.create_unset_vote_transaction(
            proposal_id, asset, dimension, vote))

    @property
    def _public_key(self):
        return self.factory.public_key

    def _proposal_id(self, asset, dimension):
        return _asset_addr.asset_item(
            dimension, asset.system, asset.key)

    def _build_first_candidate(self, pkey, asset, dimension):
        proposal_id = self._proposal_id(asset, dimension)
        proposal = AssetProposal(
            asset=asset.SerializeToString(),
            type=AssetProposal.UNIT
            if dimension is Address.DIMENSION_UNIT
            else AssetProposal.RESOURCE,
            nonce="somenonce")
        record = AssetCandidate.VoteRecord(
            public_key=pkey,
            vote=AssetVote.VOTE_ACCEPT)
        return AssetCandidates(candidates=[
            AssetCandidate(
                proposal_id=proposal_id,
                proposal=proposal,
                votes=[record])]).SerializeToString()

    def test_bad_authlist(self):
        """Bad auth_list, good threshold
        """
        self._propose(self.unit, Address.DIMENSION_UNIT)
        self._expect_get(
            _setting_addr.settings(Address.DIMENSION_UNIT),
            Settings(
                auth_list='',
                threshold='2').SerializeToString())
        self._expect_invalid_transaction()

    def test_bad_threshold(self):
        """Good auth_list, bad threshold
        """
        self._propose(self.unit, Address.DIMENSION_UNIT)
        self._expect_get(
            _setting_addr.settings(Address.DIMENSION_UNIT),
            Settings(
                auth_list=','.join([self._public_key, VOTER2]),
                threshold='').SerializeToString())
        self._expect_invalid_transaction()

    def test_not_authorized(self):
        """Bad auth_list, good threshold
        """
        self._propose(self.unit, Address.DIMENSION_UNIT)
        self._expect_get(
            _setting_addr.settings(Address.DIMENSION_UNIT),
            Settings(
                auth_list=','.join([VOTER2]),
                threshold='2').SerializeToString())
        self._expect_invalid_transaction()

    def _test_valid_propose(self, asset, dimension):
        """Sunny day proposal for asset type
        """
        self._propose(asset, dimension)
        self._get_setting(dimension)
        self._get_empty_candidates(dimension)
        self._expect_set(
            _asset_addr.candidates(dimension),
            self._build_first_candidate(
                self._public_key,
                asset,
                dimension))
        self._expect_ok()

    def test_propose_asset_unit(self):
        """Test a valid proposition for unit-of-measure asset
        This assumes basic setting and empty candidates in state
        """
        self._test_valid_propose(self.unit, Address.DIMENSION_UNIT)

    def test_propose_asset_resource(self):
        """Test a valid proposition for resource asset
        This assumes basic setting and empty candidates in state
        """
        self._test_valid_propose(self.resource, Address.DIMENSION_RESOURCE)

    def _setup_vote_get_setting(self, asset, dimension, vote):
        proposal_id = self._proposal_id(asset, dimension)
        self._vote(
            proposal_id,
            asset,
            dimension,
            vote)
        self._get_setting(dimension)
        return proposal_id

    def _setup_vote(self, asset, dimension, vote, voter):
        proposal_id = self._setup_vote_get_setting(
            asset, dimension, vote)
        self._expect_get(
            _asset_addr.candidates(dimension),
            self._build_first_candidate(
                voter,
                asset,
                dimension))
        return proposal_id

    def _setup_unset_vote_get_setting(self, asset, dimension, vote, voter):
        proposal_id = self._proposal_id(asset, dimension)
        self._unset_vote(
            proposal_id,
            asset,
            dimension,
            vote)
        self._get_setting(dimension)
        self._expect_get(
            _asset_addr.candidates(dimension),
            self._build_first_candidate(
                voter,
                asset,
                dimension))
        return proposal_id

    def _test_valid_accept_vote(self, asset, dimension):
        x = asset.SerializeToString()
        proposal_id = self._setup_vote(
            asset,
            dimension,
            AssetVote.VOTE_ACCEPT,
            VOTER2)
        self._expect_set(proposal_id, x)
        self._expect_add_event(proposal_id)
        self._set_empty_candidates(dimension)
        self._expect_ok()

    def _test_valid_reject_vote(self, asset, dimension):
        self._setup_vote(
            asset,
            dimension,
            AssetVote.VOTE_REJECT,
            VOTER2)
        self._set_empty_candidates(dimension)
        self._expect_ok()

    def _test_valid_unset_vote(self, asset, dimension):
        self._setup_unset_vote_get_setting(
            asset,
            dimension,
            AssetVote.VOTE_UNSET,
            self._public_key)
        # Expect set of candidates with at least one valid vote to be
        # preserved, otherwise we should have empty candidates
        self._set_empty_candidates(dimension)
        self._expect_ok()

    # Proposing and voting for two authorized, threshold 2
    # Assume 2 authorized voters with threshold 2
    # Also checks UNSET
    # All Sunny Day
    def test_vote_accept_unit(self):
        """Test a valid vote for unit-of-measure asset
        This assumes setting and candidates in state
        """
        self._test_valid_accept_vote(self.unit, Address.DIMENSION_UNIT)

    def test_vote_accept_resource(self):
        """Test a valid vote for resource asset
        This assumes setting and candidates in state
        """
        self._test_valid_accept_vote(self.resource, Address.DIMENSION_RESOURCE)

    def test_vote_reject_unit(self):
        """Test a valid reject vote for unit-of-measure asset
        """
        self._test_valid_reject_vote(self.unit, Address.DIMENSION_UNIT)

    def test_vote_reject_resource(self):
        """Test a valid reject vote for resource asset
        """
        self._test_valid_reject_vote(self.resource, Address.DIMENSION_RESOURCE)

    def test_vote_unset_unit(self):
        """Test a valid unset vote for unit asset proposal
        """
        self._test_valid_unset_vote(self.unit, Address.DIMENSION_UNIT)

    def test_vote_unset_resource(self):
        """Test a valid unset vote for resource asset proposal
        """
        self._test_valid_unset_vote(self.resource, Address.DIMENSION_RESOURCE)

    def _build_disjoint_candidate(self, proposal_id, voter, asset, dimension):
        proposal = AssetProposal(
            asset=asset.SerializeToString(),
            type=AssetProposal.UNIT
            if dimension is Address.DIMENSION_UNIT
            else AssetProposal.RESOURCE,
            nonce="somenonce")
        record = AssetCandidate.VoteRecord(
            public_key=voter,
            vote=AssetVote.VOTE_ACCEPT)
        return AssetCandidates(candidates=[
            AssetCandidate(
                proposal_id=proposal_id,
                proposal=proposal,
                votes=[record])]).SerializeToString()

    # All the negative tests follow
    def test_vote_unset_vote_not_exist(self):
        """Tests unset vote where previous vote does not exist
        """
        self._setup_unset_vote_get_setting(
            self.unit,
            Address.DIMENSION_UNIT,
            AssetVote.VOTE_UNSET,
            VOTER2)
        self._expect_invalid_transaction()

    def test_vote_proposal_id_not_found(self):
        """Test disjoint proposal id between vote and candidates
        """
        uproposal_id = self._proposal_id(
            self.unit,
            Address.DIMENSION_UNIT)
        rproposal_id = self._proposal_id(
            self.resource,
            Address.DIMENSION_RESOURCE)
        self._vote(
            uproposal_id,
            self.unit,
            Address.DIMENSION_UNIT,
            AssetVote.VOTE_ACCEPT)
        self._get_setting(Address.DIMENSION_UNIT)
        self._expect_get(
            _asset_addr.candidates(Address.DIMENSION_UNIT),
            self._build_disjoint_candidate(
                rproposal_id,
                self._public_key,
                self.unit,
                Address.DIMENSION_UNIT))
        self._expect_invalid_transaction()

    def test_vote_dupe_voter(self):
        """Test trying to vote twice
        """
        self._setup_vote(
            self.unit,
            Address.DIMENSION_UNIT,
            AssetVote.VOTE_ACCEPT,
            self._public_key)
        self._expect_invalid_transaction()
