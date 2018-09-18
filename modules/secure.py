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

from pythemis.skeygen import KEY_PAIR_TYPE, GenerateKeyPair
from pythemis.smessage import SMessage
from sawtooth_signing import create_context
from modules.exceptions import CliException

LOGGER = logging.getLogger()


class Secure(object):

    @staticmethod
    def read_keyfile(key_filename):
        try:
            with open(key_filename, 'r') as key_file:
                key_file_key = key_file.read().strip()
        except IOError as e:
            raise CliException('Unable to read key file: {}'.format(str(e)))
        return key_file_key

    @staticmethod
    def sawtooth_key_pair():
        LOGGER.info("Generating sawtooth key pair")
        context = create_context('secp256k1')
        private_key = context.new_random_private_key()
        public_key = context.get_public_key(private_key)
        return private_key, public_key

    @staticmethod
    def encrypting_key_pair():
        """Generate new themis encryping key pair"""
        LOGGER.info("Generating encryption key pair")
        pair = GenerateKeyPair(KEY_PAIR_TYPE.EC)
        return pair.export_private_key(), pair.export_public_key()

    @staticmethod
    def get_secret(private_key, public_key):
        """Creates a diffe-hellman themis SMessage object"""
        LOGGER.debug("ECDH Encrypt/Decrypt object")
        return SMessage(private_key, public_key)

    @staticmethod
    def encrypt_object_with(object, secret):
        """Encrypt object with provided SMessage"""
        LOGGER.debug("Encrypting object")
        return secret.wrap(object)

    @staticmethod
    def decrypt_object_with(object, secret):
        """Decrypt object with provided SMessage"""
        LOGGER.debug("Decrypting object")
        return secret.unwrap(object)
