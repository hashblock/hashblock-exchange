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

from sawtooth_processor_test.message_factory import MessageFactory

from protobuf.setting_pb2 import SettingPayload
from protobuf.setting_pb2 import Settings
from modules.address import Address


class SettingMessageFactory(object):

    def __init__(self, signer=None):
        self._asset_addr = Address(Address.FAMILY_ASSET)
        self._setting_addr = Address(Address.FAMILY_SETTING)
        self._factory = MessageFactory(
            family_name=Address.NAMESPACE_SETTING,
            family_version="0.1.0",
            namespace=[self._setting_addr.ns_family],
            signer=signer)

    @property
    def public_key(self):
        return self._factory.get_public_key()

    def create_tp_register(self):
        return self._factory.create_tp_register()

    def create_tp_response(self, status):
        return self._factory.create_tp_response(status)

    def _create_tp_process_request(self, dimension, payload):
        address = self._setting_addr.settings(dimension)
        inputs = [address, self._asset_addr.candidates(dimension)]
        outputs = [address, self._asset_addr.candidates(dimension)]
        return self._factory.create_tp_process_request(
            payload.SerializeToString(), inputs, outputs, [])

    def create_payload_request(self, settings, dimension, action):
        payload = SettingPayload(
            action=action,
            dimension=dimension,
            data=settings.SerializeToString())
        return self._create_tp_process_request(dimension, payload)

    def create_setting_transaction(self, auth_keys, thresh, dimension, action):
        setting = Settings(auth_list=auth_keys, threshold=thresh)
        return self.create_payload_request(setting, dimension, action)

    def create_get_request(self, address):
        return self._factory.create_get_request([address])

    def create_get_response(self, address, data=None):
        return self._factory.create_get_response({address: data})

    def create_set_request(self, address, setting=None):
        return self._factory.create_set_request({address: setting})

    def create_set_response(self, address):
        return self._factory.create_set_response([address])

    def create_add_event_request(self, key):
        return self._factory.create_add_event_request(
            "hashblock.setting/update",
            [("updated", key)])

    def create_add_event_response(self):
        return self._factory.create_add_event_response()
