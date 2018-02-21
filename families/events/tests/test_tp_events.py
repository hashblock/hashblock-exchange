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

from protobuf.events_pb2 import EventPayload
from protobuf.events_pb2 import InitiateEvent
from protobuf.events_pb2 import ReciprocateEvent

from hashblock_events_test.events_message_factory \
    import EventMessageFactory

from hashblock_processor_test.transaction_processor_test_case \
    import TransactionProcessorTestCase


def _to_hash(value):
    return hashlib.sha256(value).hexdigest()


class TestEvent(TransactionProcessorTestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.factory = EventMessageFactory()

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

    def _initiate(self, key, value):
        print('sending initiate...')
        self.validator.send(self.factory.create_initiate_transaction(
            key, value, "somenonce"))

    def _reciprocate(self, proposal_id, unit, vote):
        print('sending reciprocate...')
        self.validator.send(self.factory.create_reciprocate_transaction(
            proposal_id, unit, vote))

    @property
    def _public_key(self):
        return self.factory.public_key
