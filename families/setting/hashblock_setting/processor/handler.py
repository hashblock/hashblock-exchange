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

from sawtooth_sdk.processor.handler import TransactionHandler
from sawtooth_sdk.messaging.future import FutureTimeoutError
from sawtooth_sdk.processor.exceptions import InvalidTransaction
from sawtooth_sdk.processor.exceptions import InternalError

from protobuf.setting_pb2 import SettingPayload
from protobuf.setting_pb2 import Setting

from sdk.python.address import Address

LOGGER = logging.getLogger(__name__)

# Number of seconds to wait for state operations to succeed
STATE_TIMEOUT_SEC = 10


class SettingTransactionHandler(TransactionHandler):

    _addresser = Address(Address.FAMILY_SETTING)
    _actions = {
        SettingPayload.SETTING_THRESHOLD: Address.SETTING_APPTHRESH,
        SettingPayload.SETTING_AUTHORIZATIONS: Address.SETTING_AUTHKEYS
    }

    @property
    def family_name(self):
        return Address.NAMESPACE_SETTING

    @property
    def family_versions(self):
        return ['1.0.0']

    @property
    def namespaces(self):
        return [self._addresser.ns_family]

    def apply(self, transaction, context):
        txn_header = transaction.header
        public_key = txn_header.signer_public_key

        setting_payload = SettingPayload()
        setting_payload.ParseFromString(transaction.payload)

        auth_keys = self._get_auth_keys(context, setting_payload.dimension)
        if auth_keys and public_key not in auth_keys:
            raise InvalidTransaction(
                '{} is not authorized to change setting'.format(public_key))

        setting = Setting()
        setting.ParseFromString(setting_payload.data)
        return _set_setting(
            context,
            self._addresser.settings(
                setting_payload.dimension,
                self._actions[setting_payload.action]),
            setting)

    def _get_auth_keys(self, context, dimension):
        """Retrieve the authorization keys for this dimension
        """
        address = self._addresser.settings(dimension, Address.SETTING_AUTHKEYS)
        result = _get_setting(context, address)
        if result:
            return [v.strip() for v in result.value.split(',') if v]
        return result


def _set_setting(context, address, setting):
    """Change the hashblock settings on the block
    """
    try:
        context.set_state(
            {address: setting.SerializeToString()},
            timeout=STATE_TIMEOUT_SEC)
    except FutureTimeoutError:
        LOGGER.warning(
            'Timeout occured on set_state([%s, <value>])',
            address)
        raise InternalError('Unable to set {}'.format(address))


def _get_setting(context, address, default_value=None):
    """Get a hashblock settings from the block
    """
    setting = Setting()
    try:
        results = context.get_state([address], timeout=STATE_TIMEOUT_SEC)
    except FutureTimeoutError:
        LOGGER.warning(
            'Timeout occured on context.get_state([%s])',
            address)
        raise InternalError('Unable to get {}'.format(address))

    if results:
        setting.ParseFromString(results[0].data)
        return setting
    return default_value
