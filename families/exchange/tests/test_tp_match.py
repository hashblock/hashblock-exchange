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

import uuid

from protobuf.match_pb2 import MatchEvent
from protobuf.match_pb2 import Quantity
from protobuf.match_pb2 import Ratio
from protobuf.match_pb2 import UTXQ
from protobuf.match_pb2 import MTXQ

from modules.config import load_hashblock_config, valid_signer

from hashblock_match_test.match_message_factory \
    import MatchMessageFactory

from sawtooth_processor_test.transaction_processor_test_case \
    import TransactionProcessorTestCase

from modules.address import Address


class TestEvent(TransactionProcessorTestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.factory = MatchMessageFactory()
        cls._match_addr = Address(Address.FAMILY_MATCH)
        load_hashblock_config()

    def _expect_get(self, address, data=None):
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

    def _expect_add_event(self, key, attributes):
        received = self.validator.expect(
            self.factory.create_add_event_request(key, attributes))
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

    def _initiate(self, initiate_event, ukey, command):
        self.validator.send(self.factory.create_initiate_transaction(
            initiate_event,
            ukey,
            command))

    def _reciprocate(self, reciprocate_event, ukey, mkey, command):
        self.validator.send(self.factory.create_reciprocate_transaction(
            reciprocate_event, ukey, mkey, command))

    @property
    def _public_key(self):
        return self.factory.public_key

    # e.g. 5, 2 3 (ask)
    #      10, 5, 7 (tell)
    #      2, 5, 7 (numerator)
    #      1, 2, 3 (denominator)
    def _build_quantity(self, quantity, vUnit, vResource):
        return Quantity(
            value=quantity.to_bytes(2, byteorder='little'),
            valueUnit=vUnit.to_bytes(2, byteorder='little'),
            resourceUnit=vResource.to_bytes(2, byteorder='little'))

    def _build_ratio(self, numerator, denominator):
        return Ratio(numerator=numerator, denominator=denominator)

    def _build_initate_event(self, quantity, matched=False):
        return UTXQ(
            plus=valid_signer('church').encode(),
            minus=valid_signer('turing').encode(),
            quantity=quantity,
            matched=matched)

    def _build_reciprocate_event(self, ratio, quantity):
        return MTXQ(
            plus=valid_signer('turing').encode(),
            minus=valid_signer('church').encode(),
            ratio=ratio,
            quantity=quantity)

    def _ask_five_bags_peanuts(self):
        init = self._build_initate_event(self._build_quantity(5, 2, 3))
        ukey = self._match_addr.txq_item(
            Address.DIMENSION_UTXQ,
            'ask',
            str(uuid.uuid4()))
        sinit = init.SerializeToString()
        return (init, ukey, sinit)

    def _tell_tenusd_for_five_bags_peanuts(self):
        recip = self._build_reciprocate_event(
            self._build_ratio(
                self._build_quantity(2, 5, 7),
                self._build_quantity(1, 2, 3)),
            self._build_quantity(10, 5, 7))
        mkey = self._match_addr.txq_item(
            Address.DIMENSION_MTXQ,
            'tell',
            str(uuid.uuid4()))
        return (recip, mkey)

    def test_valid_initiate(self):
        """Sunny day initiate - Ask cost for 5 bags of peanuts
        """
        init, ukey, sinit = self._ask_five_bags_peanuts()
        self._initiate(
            init,
            ukey,
            MatchEvent.UTXQ_ASK)
        self._expect_set(ukey, sinit)
        self._expect_add_event(
            "hashblock.match.ask",
            [("status", "completed"), ("unbalanced_address", ukey)])
        self._expect_ok()

    def test_valid_reciprocate(self):
        """Sunny day reciprocate - Tell $10 for 5 bags of peanuts
        """
        init, ukey, sinit = self._ask_five_bags_peanuts()
        recip, mkey = self._tell_tenusd_for_five_bags_peanuts()
        self._reciprocate(recip, ukey, mkey, MatchEvent.MTXQ_TELL)
        self._expect_get(ukey, sinit)
        init.matched = True
        self._expect_set(ukey, init.SerializeToString())
        recip.unmatched.CopyFrom(init)
        srecip = recip.SerializeToString()
        self._expect_set(mkey, srecip)
        self._expect_add_event(
            "hashblock.match.tell",
            [
                ("status", "completed"),
                ("unbalanced_address", ukey),
                ("balanced_address", mkey)])
        self._expect_ok()

    def test_ill_formed_initiate(self):
        """Test not well formed initiate payload
        """
        init = UTXQ(
            plus=b'public key',
            minus=b'minus')
        ukey = self._match_addr.txq_item(
            Address.DIMENSION_UTXQ,
            'ask',
            str(uuid.uuid4()))
        self._initiate(
            init,
            ukey,
            MatchEvent.UTXQ_ASK)
        self._expect_invalid_transaction()

    def test_ill_formed_reciprocate(self):
        """Test not well formed reciprocate payload
        """
        init, ukey, sinit = self._ask_five_bags_peanuts()
        recip = MTXQ(
            plus=b'public key',
            minus=b'minus',
            quantity=self._build_quantity(10, 5, 7))
        mkey = self._match_addr.txq_item(
            Address.DIMENSION_MTXQ,
            'tell',
            str(uuid.uuid4()))
        self._reciprocate(recip, ukey, mkey, MatchEvent.MTXQ_TELL)
        self._expect_get(ukey, sinit)
        self._expect_invalid_transaction()

    def test_matched_already(self):
        """Test attempt to match on already matched initiate
        """
        init, ukey, sinit = self._ask_five_bags_peanuts()
        recip, mkey = self._tell_tenusd_for_five_bags_peanuts()
        self._reciprocate(recip, ukey, mkey, MatchEvent.MTXQ_TELL)
        init.matched = True
        self._expect_get(ukey, init.SerializeToString())
        self._expect_invalid_transaction()

    def test_invalid_match(self):
        """Test unmatchable event
        """
        init, ukey, sinit = self._ask_five_bags_peanuts()
        recip = self._build_reciprocate_event(
            self._build_ratio(
                self._build_quantity(2, 5, 7),
                self._build_quantity(1, 2, 3)),
            self._build_quantity(11, 5, 7))
        mkey = self._match_addr.txq_item(
            Address.DIMENSION_MTXQ,
            'tell',
            str(uuid.uuid4()))
        self._reciprocate(recip, ukey, mkey, MatchEvent.MTXQ_TELL)
        self._expect_get(ukey, sinit)
        self._expect_invalid_transaction()
