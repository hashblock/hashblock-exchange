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

import binascii

from shared.transactions import (
    create_transaction,
    submit_single_txn)
from protobuf.ledger_pb2 import (
    Value,
    LedgerPayload,
    Token,
    LedgerMerkleTrie)
from modules.exceptions import (
    DataException,
    AssetNotExistException, UnitNotExistException)
from modules.hashblock_zksnark import zkproc_quantity_cm
from modules.config import (
    HB_OPERATOR,
    public_key,
    agreement_secret,
    public_key_values_list)
from modules.secure import Secure
from modules.decode import ledger_addresser as _addresser
from modules.decode import asset_addresser as _asset_addy
from modules.decode import unit_addresser as _unit_addy
from modules.decode import decode_unit_list, decode_asset_list

_default_merkletrie = '0' * 64


def _validate_quantity(value, unit, asset):
    """Validate and return addresses that are reachable"""
    unit_result = None
    asset_result = None
    int(value)

    print("Validating references for asset {} and unit {}".format(asset, unit))

    unit_add = _unit_addy.address_syskey(unit['system'], unit['key'])
    asset_add = _asset_addy.address_syskey(asset['system'], asset['key'])

    def in_list(ent, elist):
        result = None
        for el in elist['data']:
            if el['system'] == ent['system'] and el['name'] == ent['key']:
                el['value'] = str(int(el['value'], 16))
                result = el
                break
        return result

    unit_result = in_list(unit, decode_unit_list(unit_add))
    if not unit_result:
        raise DataException(
            "Unit for {}.{} does not exist".format(
                unit['system'], unit['key']))
    asset_result = in_list(asset, decode_asset_list(asset_add))
    if not asset_result:
        raise DataException(
            "Asset for {}.{} does not exist".format(
                asset['system'], asset['key']))
    return (unit_result['value'], asset_result['value'])


def _validate_mint(request):
    """Validate the mint intent"""
    pubkey = public_key(request['owner'])
    secret = agreement_secret('wallet_' + request['owner'])
    unit_res, asset_res = _validate_quantity(
        request['quantity']['value'],
        request['quantity']['unit'],
        request['quantity']['asset'])
    return (secret, pubkey, request['quantity']['value'], unit_res, asset_res)


def _mint_token(ingest):
    """Encrypts value and generates commitments """
    ekey, pubkey, value, unit, asset = ingest
    # print("hex ekey {}".format(ekey.hex()))
    vcm, ucm, acm = zkproc_quantity_cm(ekey.hex(), value, unit, asset)
    ser_value = Value(
        value=bytes(value, 'utf8'),
        unit=bytes(unit, 'utf8'),
        asset=bytes(asset, 'utf8')).SerializeToString()
    evalue = binascii.hexlify(
        Secure.encrypt_object_with(ser_value, ekey))
    return (
        pubkey,
        Token(
            v_commitment=vcm,
            u_commitment=ucm,
            a_commitment=acm,
            quantity=evalue))


def _mint_payload(ingest):
    """Create the ledger payload for minting tokens"""
    pubkey, token = ingest
    return (
        _addresser.wallet(pubkey),
        LedgerPayload(
            action=LedgerPayload.WALLET_MINT_TOKEN,
            data=token.SerializeToString()))


def _mint_inputs_outputs(ingest):
    """Set the merkle trie and wallet addresses"""
    wallet_addr, payload = ingest
    addresses = [wallet_addr, _addresser.merkle]
    return (
        HB_OPERATOR,
        _addresser,
        {"inputs": addresses, "outputs": addresses},
        payload)


def mint_token(data):
    """Mint a token and submit transaction to ledger-TP"""
    intake = _mint_inputs_outputs(
        _mint_payload(
            _mint_token(_validate_mint(data))))
    return submit_single_txn(create_transaction(intake))


# Genesis operation
# //  Create LedgerMerkleTrie txn.outputs[0] has address, data has trie
# //  Create User Wallets txn.outputs[1-n] have addresses
# //  data is starting Merkle Trie string (default is 64 '0's)

def create_ledger_genesis(merkletrie=None):
    mtree = LedgerMerkleTrie(trie=bytes(
        _default_merkletrie, 'utf8')
        if not merkletrie else bytes(merkletrie, 'utf8'))
    payload = LedgerPayload(
        action=LedgerPayload.WALLET_GENESIS,
        data=mtree.SerializeToString())

    addresses = [_addresser.wallet(y) for y in public_key_values_list()]
    addresses.insert(0, _addresser.merkle)
    perms = {
        'inputs': addresses,
        'outputs': addresses
    }
    _, txn = create_transaction((HB_OPERATOR, _addresser, perms, payload))
    return [txn]
