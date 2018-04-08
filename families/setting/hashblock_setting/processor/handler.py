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
from protobuf.setting_pb2 import Settings

from sdk.python.address import Address

LOGGER = logging.getLogger(__name__)

# Number of seconds to wait for state operations to succeed
STATE_TIMEOUT_SEC = 10


class SettingTransactionHandler(TransactionHandler):

    _addresser = Address(Address.FAMILY_SETTING)
    _actions = [SettingPayload.CREATE, SettingPayload.UPDATE]

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
        setting = Settings()
        setting.ParseFromString(setting_payload.data)
        if setting_payload.action in self._actions:
            return self._set_setting(
                auth_keys,
                public_key,
                context,
                setting_payload.dimension,
                self._addresser.settings(setting_payload.dimension),
                setting)
        else:
            raise InvalidTransaction(
                "Payload 'action' must be one of {CREATE, UPDATE")

    def _validate_threshold(self, setting, auth_keys):
        """Valudate the threshold setting
        """
        pass

    def _validate_authorization(self, context, setting, dimension):
        """Valudate the authorization list setting
        """
        pass

    def _get_auth_keys(self, context, dimension):
        """Retrieve the authorization keys for this dimension
        """
        address = self._addresser.settings(dimension)
        result = _get_setting(context, address)
        if result:
            return _string_tolist(result.auth_list)
        return result

    def _set_setting(
        self, auth_keys, public_key,
            context, dimension, address, setting):
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


def _string_tolist(s):
    """Convert the authorization comma separated string to list
    """
    return [v.strip() for v in s.split(',') if v]


def _get_setting(context, address, default_value=None):
    """Get a hashblock settings from the block
    """
    setting = Settings()
    try:
        results = context.get_state([address], timeout=STATE_TIMEOUT_SEC)
    except FutureTimeoutError:
        LOGGER.warning(
            'Timeout occured on context.get_state([%s])',
            address)
        raise InternalError('Unable to get {}'.format(address))

    LOGGER.debug("_gs results = {}".format(results))
    if results:
        setting.ParseFromString(results[0].data)
        return setting
    return default_value
