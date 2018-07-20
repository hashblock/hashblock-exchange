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

import json
import random
import hashlib

from protobuf.stsetting_pb2 import SettingsPayload
from protobuf.stsetting_pb2 import SettingProposal

from modules.address import SimpleAddress
from modules.decode import (
    setting_addresser, asset_addresser, unit_addresser, utxq_addresser)
from shared.transactions import create_transaction, compose_builder
from modules.config import public_key

__SS_AUTH_KEYS = 'sawtooth.settings.vote.authorized_keys'
__SS_VOTE_PROP = 'sawtooth.settings.vote.proposals'
__SS_APRV_TRHSH = 'sawtooth.settings.vote.approval_threshold'
__SS_AUTH_TPS = 'sawtooth.validator.transaction_families'
SETTINGS_NAMESPACE = '000000'

_MIN_PRINT_WIDTH = 15
_MAX_KEY_PARTS = 4
_ADDRESS_PART_SIZE = 16


_sawset_addy = SimpleAddress('sawtooth_settings', ["1.0"])


def _short_hash(in_str):
    return hashlib.sha256(in_str.encode()).hexdigest()[:_ADDRESS_PART_SIZE]


def _key_to_address(key):
    """Creates the state address for a given setting key."""
    key_parts = key.split('.', maxsplit=_MAX_KEY_PARTS - 1)
    key_parts.extend([''] * (_MAX_KEY_PARTS - len(key_parts)))
    return SETTINGS_NAMESPACE + ''.join(_short_hash(x) for x in key_parts)


def _config_inputs(key):
    """Creates the list of inputs for a sawtooth_settings transaction, for a
    given setting key.
    """
    return [
        _key_to_address(__SS_VOTE_PROP),
        _key_to_address(__SS_AUTH_KEYS),
        _key_to_address(__SS_APRV_TRHSH),
        _key_to_address(key)
    ]


def _config_outputs(key):
    """Creates the list of outputs for a sawtooth_settings transaction, for a
    given setting key.
    """
    return [
        _key_to_address(__SS_VOTE_PROP),
        _key_to_address(key)
    ]


def _create_auth_inputs_outputs(ingest):
    signatore, setting, payload = ingest
    inputs = _config_inputs(setting)
    outputs = _config_outputs(setting)
    return (
        signatore,
        _sawset_addy,
        {"inputs": inputs, "outputs": outputs},
        payload)


def _create_sawset_authkey(ingest):
    signatore, keys = ingest
    nonce = hex(random.randint(0, 2**64))
    proposal = SettingProposal(
        setting=__SS_AUTH_KEYS,
        value=''.join(keys),
        nonce=nonce)
    return (
        signatore,
        __SS_AUTH_KEYS,
        SettingsPayload(
            data=proposal.SerializeToString(),
            action=SettingsPayload.PROPOSE))


def _create_sawset_authtps(ingest):
    signatore, families = ingest
    nonce = hex(random.randint(0, 2**64))
    proposal = SettingProposal(
        setting=__SS_AUTH_TPS,
        value=json.dumps(families),
        nonce=nonce)
    return (
        signatore,
        __SS_AUTH_TPS,
        SettingsPayload(
            data=proposal.SerializeToString(),
            action=SettingsPayload.PROPOSE))


def gensawset(signer):
    """Generates array of sawtooth setting transactions.

    Given a signer key, generate the setting for authorizing
    the signer for proposing settings changes. As there is only
    one signer, all changes to proposals will automatically
    be accepted.

    Finally, generate the TP authorization list for the
    current set of TPs with their versions
    """

    # Generate the auth key transaction
    authkey = compose_builder(
        create_transaction,
        _create_auth_inputs_outputs,
        _create_sawset_authkey)
    pkey = public_key(signer)
    authkey_txn = authkey((signer, [pkey]))[1]

    # Generate the allowed TP transaction
    flist = [
        setting_addresser,
        asset_addresser,
        unit_addresser,
        utxq_addresser]
    families = [
        {"family": a.family_ns_name, "version": a.family_current_version}
        for a in flist]
    authtps = compose_builder(
        create_transaction,
        _create_auth_inputs_outputs,
        _create_sawset_authtps)
    authtps_txn = authtps((signer, families))[1]
    return [authkey_txn, authtps_txn]


if __name__ == '__main__':
    from modules.config import load_hashblock_config
    load_hashblock_config()
    x = gensawset('turing')
    print("{}".format(x))
