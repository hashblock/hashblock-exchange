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

from protobuf.asset_pb2 import AssetCandidates
from protobuf.setting_pb2 import Settings
from protobuf.setting_pb2 import SettingPayload

from modules.address import Address

from hashblock_setting_test.setting_message_factory \
    import SettingMessageFactory

from sawtooth_processor_test.transaction_processor_test_case \
    import TransactionProcessorTestCase


VOTER2 = "59c272cb554c7100dd6c1e38b5c77f158146be29373329e503bfcb81e70d1ddd"
EMPTY_CANDIDATES = AssetCandidates(candidates=[]).SerializeToString()

_asset_addr = Address(Address.FAMILY_ASSET)
_setting_addr = Address(Address.FAMILY_SETTING)


class TestSetting(TransactionProcessorTestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.factory = SettingMessageFactory()
        cls.setting = Settings(
            auth_list=','.join([cls.factory.public_key, VOTER2]),
            threshold='2')

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

    def _get_empty_candidates(self, dimension):
        self._expect_get(
            _asset_addr.candidates(dimension),
            EMPTY_CANDIDATES)

    def _set_default_settings(self, dimension, action):
        self.validator.send(self.factory.create_payload_request(
            self.setting, dimension, action))

    def _set_setting(self, auth_list, threshold, dimension, action):
        self.validator.send(self.factory.create_setting_transaction(
            auth_list, threshold, dimension, action))

    @property
    def _public_key(self):
        return self.factory.public_key

    def test_valid_settings(self):
        """Sunny day settings create
        """
        # Start the transaction
        self._set_default_settings(
            Address.DIMENSION_UNIT,
            SettingPayload.CREATE)
        # Fetch an empty authorization/threshold setting
        self._expect_get(
            _setting_addr.settings(Address.DIMENSION_UNIT))
        # Set the settings
        self._expect_set(
            _setting_addr.settings(Address.DIMENSION_UNIT),
            self.setting.SerializeToString())
        # Set the candidates
        self._expect_set(
            _asset_addr.candidates(Address.DIMENSION_UNIT),
            EMPTY_CANDIDATES)
        self._expect_ok()

    def test_setting_create_exist(self):
        """Test behavior of create when settings exist
        """
        self._set_default_settings(
            Address.DIMENSION_UNIT,
            SettingPayload.CREATE)
        # Fetch an empty authorization/threshold setting
        self._expect_get(
            _setting_addr.settings(Address.DIMENSION_UNIT),
            self.setting.SerializeToString())
        self._expect_invalid_transaction()

    def test_bad_threshold(self):
        """Test when threshold is not a number
        """
        self._set_setting(
            ','.join([self._public_key, VOTER2]),
            "",
            Address.DIMENSION_UNIT,
            SettingPayload.CREATE)
        # Fetch an empty authorization/threshold setting
        self._expect_get(
            _setting_addr.settings(Address.DIMENSION_UNIT))
        self._expect_invalid_transaction()

    def test_threshold_too_small(self):
        """Test a threshold less than or equal to zero
        """
        self._set_setting(
            ','.join([self._public_key, VOTER2, VOTER2]),
            "0",
            Address.DIMENSION_UNIT,
            SettingPayload.CREATE)
        # Fetch an empty authorization/threshold setting
        self._expect_get(
            _setting_addr.settings(Address.DIMENSION_UNIT))
        self._expect_invalid_transaction()

    def test_authlist_too_small(self):
        """Test when threshold exceeds size of authorization list
        """
        self._set_setting(
            ','.join([self._public_key, VOTER2]),
            "3",
            Address.DIMENSION_UNIT,
            SettingPayload.CREATE)
        # Fetch an empty authorization/threshold setting
        self._expect_get(
            _setting_addr.settings(Address.DIMENSION_UNIT))
        self._expect_invalid_transaction()
