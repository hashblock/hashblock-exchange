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

from sawtooth_processor_test.message_factory import MessageFactory
from protobuf.events_pb2 import EventPayload
from protobuf.events_pb2 import InitiateEvent
from protobuf.events_pb2 import ReciprocateEvent

from hashblock_events.processor import FAMILY_NAME
from hashblock_events.processor import EVENTS_ADDRESS_PREFIX

LOGGER = logging.getLogger(__name__)

_MAX_KEY_PARTS = 4
_ADDRESS_PART_SIZE = 16


class EventMessageFactory(object):
    def __init__(self, signer=None):
        self._factory = MessageFactory(
            family_name=FAMILY_NAME,
            family_version="0.1.0",
            namespace=[EVENTS_ADDRESS_PREFIX],
            signer=signer)

    @property
    def public_key(self):
        return self._factory.get_public_key()

    def _key_to_address(self, key):
        key_parts = key.split('.', maxsplit=_MAX_KEY_PARTS - 1)
        key_parts.extend([''] * (_MAX_KEY_PARTS - len(key_parts)))

        def _short_hash(in_str):
            return self._factory.sha256(in_str.encode())[:16]

        return self._factory.namespace + \
            ''.join(_short_hash(x) for x in key_parts)

    def create_tp_register(self):
        return self._factory.create_tp_register()

    def create_tp_response(self, status):
        return self._factory.create_tp_response(status)

    def _create_tp_process_request(self, code, payload):
        inputs = [
            self._key_to_address('hashblock.events.initiate'),
            self._key_to_address('hashblock.events.reciprocate'),
            self._key_to_address(code)
        ]

        outputs = [
            self._key_to_address('hashblock.events.initiate'),
            self._key_to_address('hashblock.events.reciprocate'),
            self._key_to_address(code)
        ]

        return self._factory.create_tp_process_request(
            payload.SerializeToString(), inputs, outputs, [])

    def create_initiate_transaction(
        self, code, version, plus,
            minus, quantity, nonce):
        initiate = InitiateEvent(
            version=version, plus=plus,
            minus=minus, nonce=nonce)
        payload = EventPayload(
            action=EventPayload.INITIATE_EVENT,
            data=initiate.SerializeToString())

        return self._create_tp_process_request(code, payload)

    def create_reciprocate_transaction(self, proposal_id, code, vote):
        vote = ReciprocateEvent(proposal_id=proposal_id, vote=vote)
        payload = EventPayload(
            action=EventPayload.RECIPROCATE_EVENT,
            data=vote.SerializeToString())

        return self._create_tp_process_request(code, payload)

    def create_get_request(self, code):
        addresses = [self._key_to_address(code)]
        return self._factory.create_get_request(addresses)

    def create_get_response(self, code, value=None):
        address = self._key_to_address(code)

        if value is not None:
            entry = Unit.Entry(key=code, value=value)
            data = Unit(entries=[entry]).SerializeToString()
        else:
            data = None

        return self._factory.create_get_response({address: data})

    def create_set_request(self, code, value=None):
        address = self._key_to_address(code)

        if value is not None:
            entry = Unit.Entry(key=code, value=value)
            data = Unit(entries=[entry]).SerializeToString()
        else:
            data = None

        return self._factory.create_set_request({address: data})

    def create_set_response(self, code):
        addresses = [self._key_to_address(code)]
        return self._factory.create_set_response(addresses)

    def create_add_event_request(self, key):
        return self._factory.create_add_event_request(
            "events/update",
            [("updated", key)])

    def create_add_event_response(self):
        return self._factory.create_add_event_response()
