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
from protobuf.match_pb2 import MatchEvent

from modules.address import Address

LOGGER = logging.getLogger(__name__)


class MatchMessageFactory(object):

    def __init__(self, signer=None):
        self._match_addr = Address(Address.FAMILY_MATCH)
        self._factory = MessageFactory(
            family_name=Address.NAMESPACE_MATCH,
            family_version="0.1.0",
            namespace=[self._match_addr.ns_family],
            signer=signer)

    @property
    def public_key(self):
        return self._factory.get_public_key()

    def create_tp_register(self):
        return self._factory.create_tp_register()

    def create_tp_response(self, status):
        return self._factory.create_tp_response(status)

    def _create_tp_process_request(self, payload, ukey, mkey=None):
        if mkey:
            inputs = [ukey]
            outputs = [ukey, mkey]
        else:
            inputs = []
            outputs = [ukey]

        return self._factory.create_tp_process_request(
            payload.SerializeToString(), inputs, outputs, [])

    def create_initiate_transaction(self, initiate_event, ukey, command):
        payload = MatchEvent(
            action=command,
            ukey=ukey,
            data=initiate_event.SerializeToString())
        return self._create_tp_process_request(payload, ukey)

    def create_reciprocate_transaction(
        self,
        reciprocate_event,
        ukey,
        mkey,
            command):
        payload = MatchEvent(
            action=command,
            ukey=ukey,
            mkey=mkey,
            data=reciprocate_event.SerializeToString())
        return self._create_tp_process_request(payload, ukey, mkey)

    def create_get_request(self, address):
        return self._factory.create_get_request([address])

    def create_get_response(self, address, data=None):
        return self._factory.create_get_response({address: data})

    def create_set_request(self, address, data=None):
        return self._factory.create_set_request({address: data})

    def create_set_response(self, address):
        return self._factory.create_set_response([address])

    def create_add_event_request(self, key, attributes):
        return self._factory.create_add_event_request(
            key,
            attributes)

    def create_add_event_response(self):
        return self._factory.create_add_event_response()
