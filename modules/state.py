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

from cryptography.fernet import Fernet
from base64 import b64encode, b64decode
from sawtooth_sdk.messaging.future import FutureTimeoutError
from sawtooth_sdk.processor.exceptions import InternalError

from modules.config import encrypt_key, load_hashblock_config

STATE_TIMEOUT_SEC = 10
LOGGER = logging.getLogger(__name__)
load_hashblock_config()


class State():
    def __init__(self, context=None):
        self._context = context
        self._encrypter = Fernet(encrypt_key())
        LOGGER.debug("Encrypter = {}".format(self._encrypter))

    @property
    def context(self):
        return self._context

    @property
    def encrypter(self):
        return self._encrypter

    def _get_state_data(self, address):
        """Standard merkle trie get_state using address"""
        try:
            exchange_list = self.context.get_state(
                [address], timeout=STATE_TIMEOUT_SEC)
        except FutureTimeoutError:
            raise InternalError(
                'Timeout on getting {}'.format(address))
        if len(exchange_list) != 1:
            raise InternalError(
                'Data does not exists for {}'.format(address))
        return exchange_list

    def get(self, returnObject, address):
        """Simple get and deserialize"""
        returnObject.ParseFromString(
            self._get_state_data(address)[0].data)
        return returnObject

    def set(self, object, address):
        try:
            addresses = self.context.set_state(
                {address: object},
                timeout=STATE_TIMEOUT_SEC)
        except FutureTimeoutError:
            raise InternalError(
                'Unable to set {}'.format(address))
        if len(addresses) != 1:
            raise InternalError(
                'Unable to save exchange for address {}'.
                format(address))

    def decrypt(self, object):
        """General purpose decrypting"""
        return self.encrypter.decrypt(object)

    def encrypt(self, object):
        """General purpose encrypting"""
        return self.encrypter.encrypt(object)

    def get_encrypted(self, returnObject, address):
        """Get encrypted and deserialize"""
        returnObject.ParseFromString(
            self.decrypt(
                self._get_state_data(address)[0].data))
        return returnObject
