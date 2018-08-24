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

# from ecies import aes_encrypt, aes_decrypt

from sawtooth_sdk.messaging.future import FutureTimeoutError
from sawtooth_sdk.processor.exceptions import InternalError
from sawtooth_signing.secp256k1 import (
    Secp256k1PrivateKey, Secp256k1PublicKey)

STATE_TIMEOUT_SEC = 10
LOGGER = logging.getLogger(__name__)


class StateDataNotFound(BaseException):
    pass


class State():
    def __init__(self, context=None):
        self._context = context

    @property
    def context(self):
        return self._context

    def get_state_data(self, address):
        """Standard merkle trie get_state using address"""
        try:
            exchange_list = self.context.get_state(
                [address], timeout=STATE_TIMEOUT_SEC)
        except FutureTimeoutError:
            raise InternalError(
                'Timeout on getting {}'.format(address))
        if len(exchange_list) != 1:
            raise StateDataNotFound(
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
            raise StateDataNotFound(
                'Unable to save exchange for address {}'.
                format(address))

    @staticmethod
    def get_private_secp256k1(private_hex_string):
        """Return and instance of a sawtooth private key"""
        return Secp256k1PrivateKey.from_hex(private_hex_string)

    @staticmethod
    def get_public_hex_secp256k1(public_hex_string):
        """Return and instance of a sawtooth public key"""
        return Secp256k1PublicKey.from_hex(public_hex_string)

    @staticmethod
    def get_secret(private_str, public_str):
        """Creates a diffe-hellman secret"""
        priv = State.get_private_secp256k1(private_str)
        pub = State.get_public_hex_secp256k1(public_str)
        return pub.secp256k1_public_key.ecdh(priv.as_bytes())

    @staticmethod
    def encrypt_object_with(object, secret):
        # return aes_encrypt(secret, object)
        return object

    @staticmethod
    def decrypt_object_with(object, secret):
        # return aes_decrypt(secret, object)
        return object

    def encrypt_from(self, object, private_str, public_str):
        """Encrypts a blob"""
        return object
        # return aes_encrypt(State.get_secret(private_str, public_str), object)

    def decrypt_for(self, object, private_str, public_str):
        """Decryptes a byte string blob"""
        return object
        # return aes_decrypt(State.get_secret(private_str, public_str), object)
