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
from protobuf.asset_pb2 import AssetCandidates
from protobuf.unit_pb2 import UnitCandidates

from modules.address import Address

LOGGER = logging.getLogger(__name__)

# Number of seconds to wait for state operations to succeed
STATE_TIMEOUT_SEC = 10


class SettingTransactionHandler(TransactionHandler):

    _actions = [SettingPayload.CREATE, SettingPayload.UPDATE]

    def __init__(self):
        self._addresser = Address.setting_addresser()
        self._uaddresser = Address.unit_addresser()
        self._aaddresser = Address.asset_addresser()
        self._auth_list = None
        self._action = None

    @property
    def addresser(self):
        return self._addresser

    @property
    def family_name(self):
        return self.addresser.family_ns_name

    @property
    def family_versions(self):
        return self.addresser.family_versions

    @property
    def namespaces(self):
        return [self.addresser.family_ns_hash]

    @property
    def action(self):
        return self._action

    @action.setter
    def action(self, action):
        self._action = action

    @property
    def dimension(self):
        return self._dimension

    @dimension.setter
    def dimension(self, dim):
        self._dimension = dim
        self.address = dim

    @property
    def address(self):
        return self._address

    @address.setter
    def address(self, dim):
        self._address = self.addresser.settings(dim)

    @property
    def auth_list(self):
        return self._auth_list

    @auth_list.setter
    def auth_list(self, alist):
        self._auth_list = alist

    def apply(self, transaction, context):
        txn_header = transaction.header
        public_key = txn_header.signer_public_key

        setting_payload = SettingPayload()
        setting_payload.ParseFromString(transaction.payload)
        self.dimension = setting_payload.dimension
        setting = Settings()
        setting.ParseFromString(setting_payload.data)
        self.action = setting_payload.action
        if self.action in self._actions:
            self._validate_transaction(context, public_key)
        else:
            raise InvalidTransaction(
                "Payload 'action' must be one of {CREATE, UPDATE")

        return self._set_setting(public_key, context, setting)

    def _validate_transaction(self, context, public_key):
        self._get_auth_list(context)
        if self.action == SettingPayload.CREATE:
            if self.auth_list:
                raise InvalidTransaction(
                    'Settings for {} already exist'.
                    format(self.dimension))
        elif not self.auth_list:
            raise InvalidTransaction(
                'Settings not in place for {}'.
                format(self.dimension))
        elif public_key not in self.auth_list:
                raise InvalidTransaction(
                    '{} is not authorized to change setting'.
                    format(public_key))
        else:
            return public_key

    def _validate_create(self, context, setting):
        """Valudate the setting during a create
        """
        if self.auth_list:
            raise InvalidTransaction(
                "Settings already exists, can't re-create")
        elif not setting.auth_list or not setting.threshold:
            raise InvalidTransaction(
                "Both auth_list and threshold are required")

        auth_keys = _string_tolist(setting.auth_list)
        threshold = int(setting.threshold)
        if threshold <= 0:
            raise InvalidTransaction(
                "Threshold must be greater than 0")
        elif threshold > len(auth_keys):
            raise InvalidTransaction(
                'Threshold must be less than'
                ' count of auth_list keys')

    def _validate_update(self, context, setting):
        pass

    def _get_auth_list(self, context):
        """Retrieve the authorization keys for this dimension
        """
        result = _get_setting(context, self.address)
        if result:
            self.auth_list = _string_tolist(result.auth_list)
            return self.auth_list
        else:
            self.auth_list = None
        return result

    def _create_candidates(self, context):
        candidates = UnitCandidates(candidates=[]) \
            if self.dimension == "unit" else AssetCandidates(candidates=[])
        LOGGER.debug("Dimension for candidates = {}".format(self.dimension))
        caddr = self._uaddresser if self.dimension == "unit" \
            else self._aaddresser
        try:
            context.set_state(
                {caddr.candidate_address: candidates.SerializeToString()},
                timeout=STATE_TIMEOUT_SEC)
        except FutureTimeoutError:
            LOGGER.warning(
                'Timeout occured on set_state([%s, <value>])',
                caddr)
            raise InternalError('Unable to set {}'.format(caddr))

    def _set_setting(self, public_key, context, setting):
        """Change the hashblock settings on the block
        """
        LOGGER.debug("Processing setting payload")

        if self.action == SettingPayload.CREATE:
            self._validate_create(context, setting)
        else:
            self._validate_update(context, setting)
        try:
            context.set_state(
                {self.address: setting.SerializeToString()},
                timeout=STATE_TIMEOUT_SEC)
        except FutureTimeoutError:
            LOGGER.warning(
                'Timeout occured on set_state([%s, <value>])',
                self.address)
            raise InternalError(
                'Unable to set {}'.format(self.address))
        if self.action == SettingPayload.CREATE:
            self._create_candidates(context)


def _string_tolist(s):
    """Convert the authorization comma separated string to list
    """
    return [v.strip() for v in s.split(',') if v]


def _get_setting(context, address, default_value=None):
    """Get a hashblock settings from the block
    """
    setting = Settings()
    results = _get_state(context, address)
    if results:
        setting.ParseFromString(results[0].data)
        return setting
    return default_value


def _get_candidates(context, address, default_value=None):
    """Get a hashblock settings from the block
    """
    candidates = AssetCandidates()
    results = _get_state(context, address)
    if results:
        candidates.ParseFromString(results[0].data)
        return candidates
    return default_value


def _get_state(context, address):
    try:
        results = context.get_state([address], timeout=STATE_TIMEOUT_SEC)
    except FutureTimeoutError:
        LOGGER.warning(
            'Timeout occured on context.get_setting([%s])',
            address)
        raise InternalError('Unable to get {}'.format(address))
    return results
