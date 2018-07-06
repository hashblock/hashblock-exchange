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

"""Decode - Support hashblock module

This module is referenced when fetching an address to
decode into it's type data structure
"""
import binascii
from functools import lru_cache
from base64 import b64decode

from google.protobuf.json_format import MessageToDict
from shared.rest_client import RestClient

from modules.config import sawtooth_rest_host
from modules.config import key_owner, agreement_secret
from modules.state import State
from modules.exceptions import AuthException
from modules.address import Address

from protobuf.match_pb2 import UTXQ
from protobuf.match_pb2 import MTXQ
from protobuf.setting_pb2 import Settings
from protobuf.unit_pb2 import Unit
from protobuf.unit_pb2 import UnitCandidates
from protobuf.asset_pb2 import Asset
from protobuf.asset_pb2 import AssetCandidates

asset_addresser = Address.asset_addresser()
unit_addresser = Address.unit_addresser()
setting_addresser = Address.setting_addresser()

STATE_CRYPTO = State()

__revmachadd = {
    Address._ask_hash: 'ask',
    Address._tell_hash: 'tell',
    Address._offer_hash: 'offer',
    Address._accept_hash: 'accept',
    Address._commitment_hash: 'commitment',
    Address._obligation_hash: 'obligation',
    Address._give_hash: 'give',
    Address._take_hash: 'take'
}


def __get_leaf_data(address, partner_secret=None):
    """Fetch leaf data from chain"""
    ddict = RestClient(sawtooth_rest_host()).get_leaf(address)
    ddict['data'] = b64decode(ddict['data'])
    return ddict


def __get_encrypted_leaf(address, partner_secret=None):
    """Fetch encrypted leaf data from chain"""
    if partner_secret is None:
        raise AuthException
    ddict = RestClient(sawtooth_rest_host()).get_leaf(address)
    data = binascii.unhexlify(b64decode(ddict['data']).decode())
    ddict['data'] = STATE_CRYPTO.decrypt_object_with(data, partner_secret)
    return ddict


def __get_list_data(address, partner_secret=None):
    """Fetch list data from chain"""
    ddict = RestClient(sawtooth_rest_host()).list_state(address)
    for entry in ddict['data']:
        entry['data'] = b64decode(entry['data'])
    return ddict


def __get_encrypted_list_data(address, partner_secret=None):
    """Fetch encrypted list data from chain"""
    if partner_secret is None:
        raise AuthException
    ddict = RestClient(sawtooth_rest_host()).list_state(address)
    for entry in ddict['data']:
        s1 = binascii.unhexlify(b64decode(entry['data']).decode())
        entry['data'] = STATE_CRYPTO.decrypt_object_with(s1, partner_secret)
    return ddict


@lru_cache(maxsize=128)
def __resource_asset_cache(prime):
    """Prime (value) lookup for resource asset"""
    res = __get_list_data(
        asset_addresser.asset_prefix(Address.DIMENSION_RESOURCE))
    resource = None
    for entry in res['data']:
        er = Asset()
        er.ParseFromString(entry['data'])
        if prime == er.value:
            resource = er
            break
    return resource


@lru_cache(maxsize=128)
def __unit_asset_cache(prime):
    """Prime (value) lookup for unit asset"""
    res = __get_list_data(
        asset_addresser.asset_prefix(Address.DIMENSION_UNIT))
    unit = None
    for entry in res['data']:
        eu = Unit()
        eu.ParseFromString(entry['data'])
        if prime == eu.value:
            unit = eu
            break
    return unit


def __resource_key_lookup(prime_value):
    """Get key string of asset for type resource"""
    return __resource_asset_cache(
        '0' + '{:x}'.
        format(int.from_bytes(prime_value, byteorder='little'))).key


def __unit_key_lookup(prime_value):
    """Get key string of asset for type unit-of-measure"""
    return __unit_asset_cache(
        '0' + '{:x}'.
        format(int.from_bytes(prime_value, byteorder='little'))).key


def __format_quantity(quantity):
    """Replaces primes with asset information"""
    magnitude = int.from_bytes(quantity.value, byteorder='little')
    unit = __unit_key_lookup(quantity.unit)
    resource = __resource_key_lookup(quantity.resource)
    return '{} {} of {}'.format(
        magnitude,
        unit,
        resource)


def __decode_settings(address, data):
    """Decode a settings address
    """
    settings = Settings()
    settings.ParseFromString(data)
    if address == setting_addresser.settings("unit"):
        stype = 'unit'
    else:
        stype = 'asset'
    data = MessageToDict(settings)
    data['authList'] = [key_owner(x) for x in data['authList'].split(",")]
    return {
        'family': stype,
        'type': 'settings',
        'data': data
    }


def decode_settings(address, data=None):
    """Prepare settings json"""
    if not data:
        data = __get_leaf_data(address)
    return __decode_settings(
        address,
        __get_leaf_data(address)['data'])


def __decode_asset_proposals(address, data):
    """Decode a proposals address"""
    proposals = AssetCandidates()
    proposals.ParseFromString(data)
    asset = Asset()
    data = []
    for candidate in proposals.candidates:
        msg = MessageToDict(candidate)
        asset.ParseFromString(candidate.proposal.asset)
        msg['proposal']['asset'] = MessageToDict(asset)
        for voter in msg['votes']:
            voter['publicKey'] = key_owner(voter['publicKey'])
        data.append(msg)
    return {
        'family': 'asset',
        'type': 'proposal',
        'data': data
    }


def __decode_unit_proposals(address, data):
    """Decode a proposals address"""
    proposals = UnitCandidates()
    proposals.ParseFromString(data)
    unit = Unit()
    data = []
    for candidate in proposals.candidates:
        msg = MessageToDict(candidate)
        unit.ParseFromString(candidate.proposal.unit)
        msg['proposal']['asset'] = MessageToDict(unit)
        for voter in msg['votes']:
            voter['publicKey'] = key_owner(voter['publicKey'])
        data.append(msg)
    return {
        'family': 'unit',
        'type': 'proposal',
        'data': data
    }


def decode_proposals(address, data=None):
    if not data:
        data = __get_leaf_data(address)['data']
    return __decode_unit_proposals(address, data) \
        if address == unit_addresser.candidate_address \
        else __decode_asset_proposals(address, data)


def decode_asset(address):
    """Decode a asset address"""
    data = __get_leaf_data(address)['data']
    asset = Asset()
    asset.ParseFromString(data)
    return {
        'family': 'asset',
        'data': MessageToDict(asset)
    }


def decode_unit(address):
    """Decode a unit or resource asset address"""
    data = __get_leaf_data(address)['data']
    unit = Unit()
    unit.ParseFromString(data)
    return {
        'family': 'unit',
        'data': MessageToDict(unit)
    }


def __decode_match(address, data):
    """Detail decode a unmatched or matched address"""
    def quantity_to_prime(quantity, rquant):
        quantity['value'] = \
            int.from_bytes(rquant.value, byteorder='little')
        quantity['unit'] = int.from_bytes(
            rquant.unit, byteorder='little')
        quantity['resource'] = int.from_bytes(
            rquant.resource, byteorder='little')
    operation = __revmachadd[address[18:24]]
    if address[12:18] == Address._utxq_hash:
        item = UTXQ()
        dim = 'utxq'
        deep = False
    else:
        item = MTXQ()
        dim = 'mtxq'
        deep = True
    item.ParseFromString(data)
    match = MessageToDict(item)
    match["plus"] = key_owner(item.plus.decode())
    match["minus"] = key_owner(item.minus.decode())
    quantity_to_prime(match['quantity'], item.quantity)
    if deep:
        # Get address of utxq
        match["utxqAddr"] = item.utxq_addr.decode()
        match["matched"] = asset_addresser.is_utxq_matched(match["utxqAddr"])
        quantity_to_prime(
            match['ratio']['numerator'],
            item.ratio.numerator)
        quantity_to_prime(
            match['ratio']['denominator'],
            item.ratio.denominator)
    return {
        'family': 'match',
        'dimension': dim,
        'operation': operation,
        'data': match
    }


def get_utxq_obj_json(address, secret):
    utxq_obj = __get_encrypted_leaf(address, secret)['data']
    utxq = UTXQ()
    utxq.ParseFromString(utxq_obj)
    return (utxq, __decode_match(address, utxq_obj))


def decode_match_dimension(address, agreement):
    sec = agreement_secret(agreement)
    results = __get_encrypted_list_data(address, sec)['data']
    dim = 'utxq' if address[12:18] == Address._utxq_hash else 'mtxq'
    data = []
    for element in results:
        data.append(
            (
                __revmachadd[element['address'][18:24]],
                element['address']))
    return {
        'family': 'match',
        'dimension': dim,
        'data': data
    }


def decode_match_initiate_list(address, agreement):
    """Decorate initiates with text conversions"""
    sec = agreement_secret(agreement)
    results = __get_encrypted_list_data(address, sec)['data']
    ops = __revmachadd[address[18:24]]

    data = []
    for element in results:
        ladd = element['address']
        utxq = UTXQ()
        utxq.ParseFromString(__get_encrypted_leaf(ladd, sec)['data'])
        data.append((
            {
                "plus": key_owner(utxq.plus.decode("utf-8")),
                "minus": key_owner(utxq.minus.decode("utf-8")),
                "text": __format_quantity(utxq.quantity),
                "matched": asset_addresser.is_utxq_matched(ladd)
            },
            ladd))
    return {
        'family': 'match',
        'dimension': 'utxq',
        'operation': ops,
        'data': data
    }


def decode_match_reciprocate_list(address, agreement):
    """Decorate reciprocates with text conversions"""
    sec = agreement_secret(agreement)
    results = __get_encrypted_list_data(address, sec)['data']
    ops = __revmachadd[address[18:24]]

    data = []
    for element in results:
        ladd = element['address']
        mtxq = MTXQ()
        mtxq.ParseFromString(__get_encrypted_leaf(ladd, sec)['data'])
        data.append(({
            "plus": key_owner(mtxq.plus.decode("utf-8")),
            "minus": key_owner(mtxq.minus.decode("utf-8")),
            # "text": '{} for {}'.format(
            #     __format_quantity(mtxq.quantity))
            #  __format_quantity(mtxq.unmatched.quantity))
        }, ladd))
    return {
        'family': 'match',
        'dimension': 'mtxq',
        'operation': ops,
        'data': data
    }


def __decode_asset_listing(address):
    return [
        x for x in __get_list_data(address)['data']
        if x['address'][12:18] != Address._candidates_hash]


def decode_asset_list():
    """List of assets not including proposals"""
    results = __decode_asset_listing(asset_addresser.family_ns_hash)
    data = []
    for element in results:
        asset = Asset()
        asset.ParseFromString(element['data'])
        data.append({
            'link': element['address'],
            'type': 'asset',
            'system': asset.system,
            'name': asset.key,
            'value': asset.value
        })
    return {
        'family': 'asset',
        'data': data
    }


def decode_unit_list():
    """List of assets not including proposals"""
    results = __decode_asset_listing(unit_addresser.family_ns_hash)
    data = []
    for element in results:
        unit = Unit()
        unit.ParseFromString(element['data'])
        data.append({
            'link': element['address'],
            'type': 'unit',
            'system': unit.system,
            'name': unit.key,
            'value': unit.value
        })
    return {
        'family': 'unit',
        'data': data
    }


def decode_asset_unit_list(address):
    """List of assets not including proposals"""
    results = __decode_asset_listing(address)
    if address[12:14] == Address._unit_asset_hash:
        asset = Unit()
        atype = 'unit'
    else:
        asset = Asset()
        atype = 'resource'
    data = []
    for element in results:
        asset.ParseFromString(element['data'])
        data.append({
            'link': element['address'],
            'system': asset.system,
            'name': asset.key,
            'value': asset.value
        })
    return {
        'family': 'asset',
        'dimension': atype,
        'data': data
    }


_hash_map = {
    Address._namespace_hash: {
        Address._asset_hash: {
            Address._candidates_hash:
                [__get_leaf_data, decode_proposals],
        },
        Address._match_hash: {
            Address._utxq_hash:
                [__get_encrypted_leaf, __decode_match],
            Address._mtxq_hash:
                [__get_encrypted_leaf, __decode_match]
        },
        Address._setting_hash: {
            Address._unit_hash:
                [__get_leaf_data, decode_settings],
            Address._resource_hash:
                [__get_leaf_data, decode_settings]
        }
    }
}


def decode_from_leaf(address, partner_secret=None):
    if address[6:12] == Address._asset_hash and \
            address[12:18] != Address._candidates_hash:
                f = __get_leaf_data
                y = decode_asset
    else:
        f, y = _hash_map[address[:6]][address[6:12]][address[12:18]]
    return y(address, f(address, partner_secret)['data'])
