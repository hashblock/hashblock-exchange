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

import sys
import os
from yaml import load

from modules.exceptions import CliException, AuthException
from sawtooth_signing import create_context
from sawtooth_signing import CryptoFactory
from sawtooth_signing import ParseError
from sawtooth_signing.secp256k1 import Secp256k1PrivateKey


REST_CONFIG = None
ENVIRONMENT_KEYS_PATH = 'HASHBLOCK_KEYS'
ENVIRONMENT_CFGR_PATH = 'HASHBLOCK_CONFIG'
DEFAULT_KEYS_PATH = '/project/keys'
DEFAULT_CFGR_PATH = '/project/configs'
CFGR_FILE = 'hashblock_config.yaml'
UNKNOWN_OWNER = '__unknown_key_owner_value__'
UNKNOWN_SIGNER = '__unknown_key_signer_value__'
UNKNOWN_SUBMITTER = '__unknown_key_submitter_value__'


def sawtooth_rest_host():
    """Retrieve sawtooth rest-api url"""
    return REST_CONFIG['rest']['hosts']['swrest-connect']


def valid_signer(signer_name):
    """Attempts to resolve a singer key by name"""
    result = None
    for key, value in REST_CONFIG['rest']['signer_keys'].items():
        if key == signer_name:
            result = value
            break
    if not result:
        raise AuthException
    return result


def valid_submitter(submitter_name):
    """Attempts to resolve a submitter signer object by name"""
    result = None
    for key, value in REST_CONFIG['rest']['submitters'].items():
        if key == submitter_name:
            result = value
            break
    if not result:
        raise AuthException
    return result


def valid_encryptor(encryptor_name):
    result = None
    for key, value in REST_CONFIG['rest']['encryptors'].items():
        if key == encryptor_name:
            result = value
            break
    if not result:
        raise AuthException
    return result


def key_owner(key_value):
    """Reverse lookup by key_value"""
    result = UNKNOWN_OWNER
    for key, value in REST_CONFIG['rest']['signer_keys'].items():
        if value == key_value:
            result = key
            break
    return result


def __read_signer(key_filename):
    """Reads the given file as a hex key.

    Args:
        key_filename: The filename where the key is stored. If None,
            defaults to the default key for the current user.

    Returns:
        Signer: the signer

    Raises:
        CliException: If unable to read the file.
    """

    try:
        with open(key_filename, 'r') as key_file:
            signing_key = key_file.read().strip()
    except IOError as e:
        raise CliException('Unable to read key file: {}'.format(str(e)))

    try:
        private_key = Secp256k1PrivateKey.from_hex(signing_key)
    except ParseError as e:
        raise CliException('Unable to read key in file: {}'.format(str(e)))

    context = create_context('secp256k1')
    crypto_factory = CryptoFactory(context)
    return crypto_factory.new_signer(private_key)


def __load_cfg_and_keys(configfile):
    """Reads the configuration file and converts any priv keys to public"""
    print("Reading {} from {}".format(configfile, DEFAULT_CFGR_PATH))
    try:
        with open(os.path.join(DEFAULT_CFGR_PATH, configfile), 'r') as f:
            doc = load(f)
    except IOError:
        print("Could not read {}".format(configfile))
        raise

    signer_keys = {}
    submitter_keys = {}
    encryptor_keys = {}
    # iterate through keys to load public keys
    for key, value in doc['rest']['signers'].items():
        signer = __read_signer(os.path.join(DEFAULT_KEYS_PATH, value))
        submitter_keys[key] = signer
        signer_keys[key] = signer.get_public_key().as_hex()

    for key, value in doc['rest']['encryption'].items():
        encryptor = __read_signer(os.path.join(DEFAULT_KEYS_PATH), value)
        encryptor_keys[key] = encryptor

    doc['rest']['signer_keys'] = signer_keys
    doc['rest']['submitters'] = submitter_keys
    doc['rest']['encryptors'] = encryptor_keys
    return doc


def load_hashblock_config():
    """Load the hashblock-rest configuration file

    Will also check environment var for key resolution
    """
    global REST_CONFIG
    global DEFAULT_KEYS_PATH
    global DEFAULT_CFGR_PATH

    if os.environ.get(ENVIRONMENT_KEYS_PATH):
        DEFAULT_KEYS_PATH = os.environ.get(ENVIRONMENT_KEYS_PATH)
    if os.environ.get(ENVIRONMENT_CFGR_PATH):
        DEFAULT_CFGR_PATH = os.environ.get(ENVIRONMENT_CFGR_PATH)

    if not os.path.exists(DEFAULT_KEYS_PATH):
        raise ValueError("/project/keys directory not found")
    if not os.path.exists(DEFAULT_CFGR_PATH):
        raise ValueError("/project/config directory not found")

    sys.path.append(DEFAULT_CFGR_PATH)
    REST_CONFIG = __load_cfg_and_keys(CFGR_FILE)
    return REST_CONFIG
