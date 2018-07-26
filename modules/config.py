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

from modules.state import State
from modules.dualities import Duality
from modules.exceptions import CliException, AuthException
from sawtooth_signing import create_context
from sawtooth_signing import CryptoFactory
from sawtooth_signing import ParseError
from sawtooth_signing.secp256k1 import Secp256k1PrivateKey


REST_CONFIG = None
KEYS_PATH = None
HB_OPERATOR = '__ZZZ_fff_hashblock_OPERATOR'
ENVIRONMENT_KEYS_PATH = 'HASHBLOCK_KEYS'
ENVIRONMENT_CFGR_PATH = 'HASHBLOCK_CONFIG'
DUALITIES_SPECIFICATIONS = "dualities.yaml"
DEFAULT_KEYS_PATH = '/project/keys'
DEFAULT_CFGR_PATH = '/project/configs'
CFGR_FILE = 'hashblock_config.yaml'
UNKNOWN_OWNER = '__unknown_key_owner_value__'
UNKNOWN_AGREEMENT = '__unknown_agreement__'


def keys_path():
    return KEYS_PATH


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


def public_key(name):
    """Attempts to resolve a public key by name"""
    result = None
    for key, value in REST_CONFIG['rest']['public_keys'].items():
        if key == name:
            result = value
            break
    if not result:
        raise AuthException
    return result


def private_key(name):
    """Attempts to resolve a private key by name"""
    result = None
    for key, value in REST_CONFIG['rest']['private_keys'].items():
        if key == name:
            result = value
            break
    if not result:
        raise AuthException
    return result


def valid_partnership(part1, part2):
    result = False
    for key, value in REST_CONFIG['rest']['partners'].items():
        if part1 in value and part2 in value:
            result = True
            break
    return result


def partnership_secret(part1, part2):
    result = None
    for key, value in REST_CONFIG['rest']['partners'].items():
        if part1 in value and part2 in value:
            result = value[2]
            break
    if not result:
        raise AuthException
    return result


def agreement_secret(agreement_name):
    result = None
    for key, value in REST_CONFIG['rest']['partners'].items():
        if key == agreement_name:
            result = value[2]
            break
    if not result:
        raise AuthException(
            '{} < {}'.format(UNKNOWN_AGREEMENT, agreement_name))
    return result


def key_owner(key_value):
    """Reverse lookup by key_value"""
    result = UNKNOWN_OWNER
    for key, value in REST_CONFIG['rest']['signer_keys'].items():
        if value == key_value:
            result = key
            break
    return result


def zksnark_prover_key():
    """Returns the registered prover key"""
    return REST_CONFIG['rest']['zksnark_keys']['prover']


def zksnark_verifier_key():
    """Returns the registered verifier key"""
    return REST_CONFIG['rest']['zksnark_keys']['verifier']


def valid_key(key_value):
    """Tests key against known keys"""
    return False if key_owner(key_value) == UNKNOWN_OWNER else True


def __read_keyfile(key_filename):
    try:
        with open(key_filename, 'r') as key_file:
            key_file_key = key_file.read().strip()
    except IOError as e:
        raise CliException('Unable to read key file: {}'.format(str(e)))
    return key_file_key


def __read_keys(key_file_prefix):
    """Reads in the public and private keys"""
    return (
        __read_keyfile(key_file_prefix + ".pub"),
        __read_keyfile(key_file_prefix + ".priv"))


def __read_signer(signing_key):
    """Reads the given file as a hex key.

    Args:
        private_key: The private key from file

    Returns:
        Signer: the signer

    Raises:
        CliException: If unable to create Secp256k1PrivateKey
    """

    try:
        private_key = Secp256k1PrivateKey.from_hex(signing_key)
    except ParseError as e:
        raise CliException(
            'Unable to create Secp256k1PrivateKey: {}'.format(str(e)))

    context = create_context('secp256k1')
    crypto_factory = CryptoFactory(context)
    return crypto_factory.new_signer(private_key)


def __fabricate_signer():
    """Fabricate private, public and signer keys"""
    context = create_context('secp256k1')
    private_key = context.new_random_private_key()
    public_key = context.get_public_key(private_key)
    crypto_factory = CryptoFactory(context)
    signer_key = crypto_factory.new_signer(private_key)
    return (public_key.as_hex(), private_key.as_hex(), signer_key)


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
    private_keys = {}
    public_keys = {}
    submitter_keys = {}
    # iterate through signers for keys
    for key, value in doc['rest']['signers'].items():
        public, private = __read_keys(os.path.join(DEFAULT_KEYS_PATH, value))
        public_keys[key] = public
        private_keys[key] = private
        signer_keys[key] = public
        submitter_keys[key] = __read_signer(private)

    public, private, signer = __fabricate_signer()
    public_keys[HB_OPERATOR] = public
    private_keys[HB_OPERATOR] = private
    signer_keys[HB_OPERATOR] = public
    submitter_keys[HB_OPERATOR] = signer

    doc['rest']['public_keys'] = public_keys
    doc['rest']['private_keys'] = private_keys
    doc['rest']['signer_keys'] = signer_keys
    doc['rest']['submitters'] = submitter_keys

    # iterate through zksnark keys
    zksnark_keys = {}
    for key, value in doc['rest']['zksnark'].items():
        zksnarkkey = __read_keyfile(os.path.join(DEFAULT_KEYS_PATH, value))
        zksnark_keys[key] = zksnarkkey
    doc['rest']['zksnark_keys'] = submitter_keys

    # iterate through agreements
    # for each agreement get the pair and append a secret
    agreements = {}
    for key, value in doc['rest']['agreements'].items():
        if len(value) == 2:
            value.append(
                State.get_secret(
                    doc['rest']['private_keys'][value[0]],
                    doc['rest']['public_keys'][value[1]]))
            agreements[key] = value
        else:
            raise AuthException
    doc['rest']['partners'] = agreements
    return doc


def load_hashblock_config():
    """Load the hashblock-rest configuration file

    Will also check environment var for key resolution
    """
    global REST_CONFIG
    global DEFAULT_KEYS_PATH
    global DEFAULT_CFGR_PATH
    global KEYS_PATH

    if REST_CONFIG:
        return REST_CONFIG

    if os.environ.get(ENVIRONMENT_KEYS_PATH):
        DEFAULT_KEYS_PATH = os.environ.get(ENVIRONMENT_KEYS_PATH)

    if os.environ.get(ENVIRONMENT_CFGR_PATH):
        DEFAULT_CFGR_PATH = os.environ.get(ENVIRONMENT_CFGR_PATH)

    if not os.path.exists(DEFAULT_KEYS_PATH):
        raise ValueError("/project/keys directory not found")
    if not os.path.exists(DEFAULT_CFGR_PATH):
        raise ValueError("/project/config directory not found")

    KEYS_PATH = DEFAULT_KEYS_PATH + '/'

    sys.path.append(DEFAULT_CFGR_PATH)
    Duality.load_dualities(ENVIRONMENT_CFGR_PATH, DUALITIES_SPECIFICATIONS)
    REST_CONFIG = __load_cfg_and_keys(CFGR_FILE)
    return REST_CONFIG
