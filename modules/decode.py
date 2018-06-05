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
from functools import lru_cache
from base64 import b64decode

from google.protobuf.json_format import MessageToDict

from modules.config import sawtooth_rest_host
from modules.config import key_owner
from modules.state import State

from shared.rest_client import RestClient
from modules.address import Address
from protobuf.match_pb2 import UTXQ
from protobuf.match_pb2 import MTXQ
from protobuf.setting_pb2 import Settings
from protobuf.asset_pb2 import Unit
from protobuf.asset_pb2 import Resource
from protobuf.asset_pb2 import AssetCandidates

asset_addresser = Address(Address.FAMILY_ASSET, "0.1.0")
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


def __get_leaf_data(address):
    """Fetch leaf data from chain"""
    return RestClient(sawtooth_rest_host()).get_leaf(address)


def __get_encrypted_leaf(address):
    """Fetch leaf data from chain"""
    ddict = RestClient(sawtooth_rest_host()).get_leaf(address)
    print("")
    ddict['data'] = STATE_CRYPTO.decrypt(b64decode(ddict['data']))
    return ddict


def __get_list_data(address):
    """Fetch list data from chain"""
    return RestClient(sawtooth_rest_host()).list_state(address)


@lru_cache(maxsize=128)
def __resource_asset_cache(prime):
    """Prime (value) lookup for resource asset"""
    res = __get_list_data(
        asset_addresser.asset_prefix(Address.DIMENSION_RESOURCE))
    resource = None
    for entry in res['data']:
        er = Resource()
        er.ParseFromString(b64decode(entry['data']))
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
        eu.ParseFromString(b64decode(entry['data']))
        if prime == eu.value:
            unit = eu
            break
    return unit


def __resource_key_lookup(prime_value):
    """Get key string of asset for type resource"""
    return __resource_asset_cache(
        str(int.from_bytes(prime_value, byteorder='little'))).key


def __unit_key_lookup(prime_value):
    """Get key string of asset for type unit-of-measure"""
    return __unit_asset_cache(
        str(int.from_bytes(prime_value, byteorder='little'))).key


def __format_quantity(quantity):
    """Replaces primes with asset information"""
    value_magnitude = int.from_bytes(quantity.value, byteorder='little')
    value_unit = __unit_key_lookup(quantity.valueUnit)
    resource_unit = __resource_key_lookup(quantity.resourceUnit)
    return '{} {} of {}'.format(
        value_magnitude,
        value_unit,
        resource_unit)


def __decode_settings(address, data):
    """Decode a settings address
    """
    settings = Settings()
    settings.ParseFromString(data)
    if address[12:18] == Address._unit_hash:
        subfam = 'unit'
    else:
        subfam = 'resource'
    data = MessageToDict(settings)
    data['authList'] = [key_owner(x) for x in data['authList'].split(",")]
    return {
        'family': 'asset',
        'type': 'setting',
        'dimension': subfam,
        'data': data
    }


def decode_settings(address, data=None):
    """Prepare settings json"""
    if not data:
        data = __get_leaf_data(address)
    return __decode_settings(
        address,
        b64decode(__get_leaf_data(address)['data']))


def __decode_proposals(address, data):
    """Decode a proposals address"""
    proposals = AssetCandidates()
    proposals.ParseFromString(data)
    if address[18:24] == Address._unit_hash:
        asset = Unit()
        subfam = 'unit'
    else:
        asset = Resource()
        subfam = 'resource'
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
        'dimension': subfam,
        'data': data
    }


def decode_proposals(address, data=None):
    if not data:
        data = b64decode(__get_leaf_data(address)['data'])
    return __decode_proposals(address, data)


def __decode_asset(address, data):
    """Decode a unit or resource asset address"""
    if address[12:18] == Address._unit_hash:
        asset = Unit()
        dim = Address.DIMENSION_UNIT
    else:
        asset = Resource()
        dim = Address.DIMENSION_RESOURCE
    asset.ParseFromString(data)
    return {
        'family': 'asset',
        'dimension': dim,
        'data': MessageToDict(asset)
    }


def __decode_match(address, data):
    """Detail decode a unmatched or matched address"""
    def quantity_to_prime(quantity, rquant):
        quantity['value'] = \
            int.from_bytes(rquant.value, byteorder='little')
        quantity['valueUnit'] = int.from_bytes(
            rquant.valueUnit, byteorder='little')
        quantity['resourceUnit'] = int.from_bytes(
            rquant.resourceUnit, byteorder='little')
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
        quantity_to_prime(
            match['ratio']['numerator'],
            item.ratio.numerator)
        quantity_to_prime(
            match['ratio']['denominator'],
            item.ratio.denominator)
        quantity_to_prime(
            match['unmatched']['quantity'],
            item.unmatched.quantity)
        match['unmatched']["plus"] = key_owner(item.unmatched.plus.decode())
        match['unmatched']["minus"] = key_owner(item.unmatched.minus.decode())
    return {
        'family': 'match',
        'dimension': dim,
        'operation': operation,
        'data': match
    }


def get_utxq_obj_json(address):
    utxq_obj = __get_encrypted_leaf(address)['data']
    utxq = UTXQ()
    utxq.ParseFromString(utxq_obj)
    return (utxq, __decode_match(address, utxq_obj))


def decode_match_dimension(address):
    results = __get_list_data(address)['data']
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


def decode_match_initiate_list(address):
    """Decorate initiates with text conversions"""
    results = __get_list_data(address)['data']
    ops = __revmachadd[address[18:24]]

    data = []
    for element in results:
        ladd = element['address']
        utxq = UTXQ()
        utxq.ParseFromString(b64decode(
            __get_encrypted_leaf(ladd)['data']))
        data.append((
            {
                "plus": key_owner(utxq.plus.decode("utf-8")),
                "minus": key_owner(utxq.minus.decode("utf-8")),
                "text": __format_quantity(utxq.quantity)
            },
            ladd))
    return {
        'family': 'match',
        'dimension': 'utxq',
        'operation': ops,
        'data': data
    }


def decode_match_reciprocate_list(address):
    """Decorate reciprocates with text conversions"""
    results = __get_list_data(address)['data']
    ops = __revmachadd[address[18:24]]

    data = []
    for element in results:
        ladd = element['address']
        mtxq = MTXQ()
        mtxq.ParseFromString(b64decode(
            __get_encrypted_leaf(ladd)['data']))
        data.append(({
            "plus": key_owner(mtxq.plus.decode("utf-8")),
            "minus": key_owner(mtxq.minus.decode("utf-8")),
            "text": '{} for {}'.format(
                __format_quantity(mtxq.quantity),
                __format_quantity(mtxq.unmatched.quantity))
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


def decode_asset_list(address):
    """List of assets not including proposals"""
    results = __decode_asset_listing(address)
    data = []
    for element in results:
        if element['address'][12:18] == Address._unit_hash:
            asset = Unit()
            atype = 'unit'
        else:
            asset = Resource()
            atype = 'resource'
        asset.ParseFromString(b64decode(element['data']))
        data.append({
            'link': element['address'],
            'type': atype,
            'system': asset.system,
            'name': asset.key,
            'value': asset.value
        })
    return {
        'family': 'asset',
        'data': data
    }


def decode_asset_unit_list(address):
    """List of assets not including proposals"""
    results = __decode_asset_listing(address)
    if address[12:18] == Address._unit_hash:
        asset = Unit()
        atype = 'unit'
    else:
        asset = Resource()
        atype = 'resource'
    data = []
    for element in results:
        asset.ParseFromString(b64decode(element['data']))
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
            Address._unit_hash:
                [__get_leaf_data, __decode_asset],
            Address._resource_hash:
                [__get_leaf_data, __decode_asset]
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


def decode_from_leaf(address):
    f, y = _hash_map[address[:6]][address[6:12]][address[12:18]]
    leaf = f(address)
    return y(address, b64decode(leaf['data']))
