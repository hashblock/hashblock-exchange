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
import base64

from protobuf.unit_pb2 import UnitProposal
from protobuf.unit_pb2 import UnitVote
from protobuf.unit_pb2 import UnitCandidate
from protobuf.unit_pb2 import UnitCandidates

from hashblock_units_test.units_message_factory \
    import UnitMessageFactory

from sawtooth_processor_test.transaction_processor_test_case \
    import TransactionProcessorTestCase


def _to_hash(value):
    return hashlib.sha256(value).hexdigest()


EMPTY_CANDIDATES = UnitCandidates(candidates=[]).SerializeToString()


class TestUnit(TransactionProcessorTestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.factory = UnitMessageFactory()

    def _expect_get(self, key, value=None):
        received = self.validator.expect(
            self.factory.create_get_request(key))
        self.validator.respond(
            self.factory.create_get_response(key, value),
            received)

    def _expect_set(self, key, expected_value):
        received = self.validator.expect(
            self.factory.create_set_request(key, expected_value))
        self.validator.respond(
            self.factory.create_set_response(key), received)

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

    def _propose(self, key, value):
        self.validator.send(self.factory.create_proposal_transaction(
            key, value, "somenonce"))

    def _vote(self, proposal_id, unit, vote):
        self.validator.send(self.factory.create_vote_proposal(
            proposal_id, unit, vote))

    @property
    def _public_key(self):
        return self.factory.public_key

    def test_set_value_bad_approval_threshold(self):
        """
        Tests setting an invalid approval_threshold.
        """
        self._propose("hashblock.units.vote.approval_threshold", "foo")

        self._expect_get('hashblock.units.vote.authorized_keys',
                         self._public_key)
        self._expect_get('hashblock.units.vote.approval_threshold')

        self._expect_invalid_transaction()

    def test_set_value_too_large_approval_threshold(self):
        """
        Tests setting an approval_threshold that is larger than the set of
        authorized keys.  This should return an invalid transaction.
        """
        self._propose("hashblock.units.vote.approval_threshold", "2")

        self._expect_get('hashblock.units.vote.authorized_keys',
                         self._public_key)
        self._expect_get('hashblock.units.vote.approval_threshold')

        self._expect_invalid_transaction()

    def test_set_value_empty_authorized_keys(self):
        """
        Tests unit an empty set of authorized keys.

        Empty authorized keys should result in an invalid transaction.
        """
        self._propose("hashblock.units.vote.authorized_keys", "")

        self._expect_get('hashblock.units.vote.authorized_keys',
                         self._public_key)
        self._expect_get('hashblock.units.vote.approval_threshold')

        self._expect_invalid_transaction()

    def test_allow_set_authorized_keys_when_initially_empty(self):
        """Tests that the authorized keys may be set if initially empty.
        """
        self._propose("hashblock.units.vote.authorized_keys",
                      self._public_key)

        self._expect_get('hashblock.units.vote.authorized_keys')
        self._expect_get('hashblock.units.vote.approval_threshold')

        # Check that it is set
        self._expect_get('hashblock.units.vote.authorized_keys')
        self._expect_set('hashblock.units.vote.authorized_keys',
                         self._public_key)

        self._expect_add_event('hashblock.units.vote.authorized_keys')

        self._expect_ok()

    def test_reject_units_when_auth_keys_is_empty(self):
        """Tests that when auth keys is empty, only auth keys maybe set.
        """
        self._propose('my.config.unit', 'myvalue')

        self._expect_get('hashblock.units.vote.authorized_keys')
        self._expect_get('hashblock.units.vote.approval_threshold')

        self._expect_invalid_transaction()

    def test_set_value_proposals(self):
        """
        Tests setting the unit of hashblock.units.vote.proposals, which is
        only an internally set structure.
        """
        self._propose('hashblock.units.vote.proposals', EMPTY_CANDIDATES)

        self._expect_get('hashblock.units.vote.authorized_keys',
                         self._public_key)
        self._expect_get('hashblock.units.vote.approval_threshold')

        self._expect_invalid_transaction()

    def test_propose(self):
        """
        Tests proposing a value in ballot mode.
        """
        self._propose('my.config.unit', 'myvalue')

        self._expect_get('hashblock.units.vote.authorized_keys',
                         self._public_key)
        self._expect_get('hashblock.units.vote.approval_threshold', '2')
        self._expect_get('hashblock.units.vote.proposals')

        proposal = UnitProposal(
            code='my.config.unit',
            value='myvalue',
            nonce='somenonce'
        )
        proposal_id = _to_hash(proposal.SerializeToString())
        record = UnitCandidate.VoteRecord(
            public_key=self._public_key,
            vote=UnitVote.ACCEPT)
        candidate = UnitCandidate(
            proposal_id=proposal_id,
            proposal=proposal,
            votes=[record])

        candidates = UnitCandidates(candidates=[candidate])

        # Get's again to update the entry
        self._expect_get('hashblock.units.vote.proposals')
        self._expect_set('hashblock.units.vote.proposals',
                         base64.b64encode(candidates.SerializeToString()))

        self._expect_add_event('hashblock.units.vote.proposals')

        self._expect_ok()

    def test_vote_approved(self):
        """
        Tests voting on a given unit, where the unit is approved
        """
        proposal = UnitProposal(
            code='my.config.unit',
            value='myvalue',
            nonce='somenonce'
        )
        proposal_id = _to_hash(proposal.SerializeToString())
        record = UnitCandidate.VoteRecord(
            public_key="some_other_public_key",
            vote=UnitVote.ACCEPT)
        candidate = UnitCandidate(
            proposal_id=proposal_id,
            proposal=proposal,
            votes=[record])

        candidates = UnitCandidates(candidates=[candidate])

        self._vote(proposal_id, 'my.config.unit', UnitVote.ACCEPT)

        self._expect_get('hashblock.units.vote.authorized_keys',
                         self._public_key + ',some_other_public_key')
        self._expect_get('hashblock.units.vote.proposals',
                         base64.b64encode(candidates.SerializeToString()))
        self._expect_get('hashblock.units.vote.approval_threshold', '2')

        # the vote should pass
        self._expect_get('my.config.unit')
        self._expect_set('my.config.unit', 'myvalue')

        self._expect_add_event("my.config.unit")

        # expect to update the proposals
        self._expect_get('hashblock.units.vote.proposals',
                         base64.b64encode(candidates.SerializeToString()))
        self._expect_set('hashblock.units.vote.proposals',
                         base64.b64encode(EMPTY_CANDIDATES))

        self._expect_add_event('hashblock.units.vote.proposals')

        self._expect_ok()

    def test_vote_counted(self):
        """
        Tests voting on a given unit, where the vote is counted only.
        """
        proposal = UnitProposal(
            code='my.config.unit',
            value='myvalue',
            nonce='somenonce'
        )
        proposal_id = _to_hash(proposal.SerializeToString())
        record = UnitCandidate.VoteRecord(
            public_key="some_other_public_key",
            vote=UnitVote.ACCEPT)
        candidate = UnitCandidate(
            proposal_id=proposal_id,
            proposal=proposal,
            votes=[record])

        candidates = UnitCandidates(candidates=[candidate])

        self._vote(proposal_id, 'my.config.unit', UnitVote.ACCEPT)

        self._expect_get('hashblock.units.vote.authorized_keys',
                         self._public_key +
                         ',some_other_public_key,third_public_key')
        self._expect_get('hashblock.units.vote.proposals',
                         base64.b64encode(candidates.SerializeToString()))
        self._expect_get('hashblock.units.vote.approval_threshold', '3')

        # expect to update the proposals
        self._expect_get('hashblock.units.vote.proposals',
                         base64.b64encode(candidates.SerializeToString()))

        record = UnitCandidate.VoteRecord(
            public_key="some_other_public_key",
            vote=UnitVote.ACCEPT)
        new_record = UnitCandidate.VoteRecord(
            public_key=self._public_key,
            vote=UnitVote.ACCEPT)
        candidate = UnitCandidate(
            proposal_id=proposal_id,
            proposal=proposal,
            votes=[record, new_record])

        updated_candidates = UnitCandidates(candidates=[candidate])
        self._expect_set(
            'hashblock.units.vote.proposals',
            base64.b64encode(updated_candidates.SerializeToString()))

        self._expect_add_event('hashblock.units.vote.proposals')

        self._expect_ok()

    def test_vote_rejected(self):
        """
        Tests voting on a given unit, where the unit is rejected.
        """
        proposal = UnitProposal(
            code='my.config.unit',
            value='myvalue',
            nonce='somenonce'
        )
        proposal_id = _to_hash(proposal.SerializeToString())
        candidate = UnitCandidate(
            proposal_id=proposal_id,
            proposal=proposal,
            votes=[
                UnitCandidate.VoteRecord(
                    public_key='some_other_public_key',
                    vote=UnitVote.ACCEPT),
                UnitCandidate.VoteRecord(
                    public_key='a_rejectors_public_key',
                    vote=UnitVote.REJECT)
            ])

        candidates = UnitCandidates(candidates=[candidate])

        self._vote(proposal_id, 'my.config.unit', UnitVote.REJECT)

        self._expect_get(
            'hashblock.units.vote.authorized_keys',
            self._public_key + ',some_other_public_key,a_rejectors_public_key')
        self._expect_get('hashblock.units.vote.proposals',
                         base64.b64encode(candidates.SerializeToString()))
        self._expect_get('hashblock.units.vote.approval_threshold', '2')

        # expect to update the proposals
        self._expect_get('hashblock.units.vote.proposals',
                         base64.b64encode(candidates.SerializeToString()))
        self._expect_set('hashblock.units.vote.proposals',
                         base64.b64encode(EMPTY_CANDIDATES))

        self._expect_add_event('hashblock.units.vote.proposals')

        self._expect_ok()

    def test_vote_rejects_a_tie(self):
        """
        Tests voting on a given unit, where there is a tie for accept and
        for reject, with no remaining auth keys.
        """
        proposal = UnitProposal(
            code='my.config.unit',
            value='myvalue',
            nonce='somenonce'
        )
        proposal_id = _to_hash(proposal.SerializeToString())
        candidate = UnitCandidate(
            proposal_id=proposal_id,
            proposal=proposal,
            votes=[
                UnitCandidate.VoteRecord(
                    public_key='some_other_public_key',
                    vote=UnitVote.ACCEPT),
            ])

        candidates = UnitCandidates(candidates=[candidate])

        self._vote(proposal_id, 'my.config.unit', UnitVote.REJECT)

        self._expect_get('hashblock.units.vote.authorized_keys',
                         self._public_key + ',some_other_public_key')
        self._expect_get('hashblock.units.vote.proposals',
                         base64.b64encode(candidates.SerializeToString()))
        self._expect_get('hashblock.units.vote.approval_threshold', '2')

        # expect to update the proposals
        self._expect_get('hashblock.units.vote.proposals',
                         base64.b64encode(candidates.SerializeToString()))
        self._expect_set('hashblock.units.vote.proposals',
                         base64.b64encode(EMPTY_CANDIDATES))

        self._expect_add_event('hashblock.units.vote.proposals')

        self._expect_ok()

    def test_authorized_keys_accept_no_approval_threshhold(self):
        """
        Tests setting a unit with auth keys and no approval threshhold
        """
        self._propose("foo.bar.count", "1")

        self._expect_get('hashblock.units.vote.authorized_keys',
                         'some_key,' + self._public_key)
        self._expect_get('hashblock.units.vote.approval_threshold')

        # check the old unit and set the new one
        self._expect_get('foo.bar.count')
        self._expect_set('foo.bar.count', '1')

        self._expect_add_event('foo.bar.count')

        self._expect_ok()

    def test_authorized_keys_wrong_key_no_approval(self):
        """
        Tests setting a unit with a non-authorized key and no approval type
        """
        self._propose("foo.bar.count", "1")

        self._expect_get('hashblock.units.vote.authorized_keys',
                         'some_key,some_other_key')

        self._expect_invalid_transaction()
