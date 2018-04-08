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

from sawtooth_processor_test.message_factory import MessageFactory
from protobuf.unit_pb2 import UnitPayload
from protobuf.unit_pb2 import UnitProposal
from protobuf.unit_pb2 import UnitVote
from protobuf.units_pb2 import Unit

from protobuf.setting_pb2 import SettingPayload
from protobuf.setting_pb2 import Setting
from sdk.python.address import Address

LOGGER = logging.getLogger(__name__)

_MAX_KEY_PARTS = 4
_ADDRESS_PART_SIZE = 16


class SettingMessageFactory(object):
    _addresser = Address(Address.FAMILY_SETTING)

    def __init__(self, signer=None):
        self._factory = MessageFactory(
            family_name=Address.NAMESPACE_SETTING,
            family_version="1.0.0",
            namespace=[self._addresser.ns_family],
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

    def _create_tp_process_request(self, dimension, payload):

        inputs = [
            self._addresser.settings(dimension, Address.SETTING_AUTHKEYS),
            self._addresser.settings(dimension, Address.SETTING_APPTHRESH)]

        outputs = [
            self._addresser.settings(dimension, Address.SETTING_AUTHKEYS),
            self._addresser.settings(dimension, Address.SETTING_APPTHRESH)]

        return self._factory.create_tp_process_request(
            payload.SerializeToString(), inputs, outputs, [])

    def create_setting_transaction(self, key, value, dimension, action):
        setting = Setting(key=key, value=value)
        payload = SettingPayload(
            action=action,
            dimension=dimension,
            data=setting.SerializeToString())
        return self._create_tp_process_request(dimension, payload)

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
            "units/update",
            [("updated", key)])

    def create_add_event_response(self):
        return self._factory.create_add_event_response()
