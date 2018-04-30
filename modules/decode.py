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
from base64 import b64decode

from config.hb_rest_config import REST_CONFIG
from shared.rest_client import RestClient
from modules.address import Address
from google.protobuf.json_format import MessageToDict
from protobuf.match_pb2 import UTXQ
from protobuf.match_pb2 import MTXQ
from protobuf.setting_pb2 import Settings
from protobuf.asset_pb2 import Unit
from protobuf.asset_pb2 import Resource
from protobuf.asset_pb2 import AssetCandidates


def __get_leaf_data(address):
    node = REST_CONFIG['rest']['hosts']['local']
    return RestClient(node).get_leaf(address)


def __get_list_data(address):
    node = REST_CONFIG['rest']['hosts']['local']
    return RestClient(node).list_state(address)


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
    data['authList'] = data['authList'].split(",")
    return {
        'family': 'asset',
        'type': 'setting',
        'dimension': subfam,
        'data': data
    }


def decode_settings(address, data=None):
    if not data:
        data = __get_leaf_data(address)
    return __decode_settings(
        address,
        b64decode(__get_leaf_data(address)['data']))


def __decode_proposals(address, data):
    """Decode a proposals address
    """
    print("__DP {} = {}".format(address, data))
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
        data.append(msg)
    return {
        'family': 'asset',
        'type': 'proposal',
        'dimension': subfam,
        'data': data
    }


def decode_proposals(address, data=None):
    if not data:
        data = __get_leaf_data(address)
    return __decode_proposals(
        address,
        b64decode(__get_leaf_data(address)['data']))


def __decode_asset(address, data):
    """Decode a unit or resource asset address
    """
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

match_prime_lookup = {
    "bag": 2,
    "bags": 2,
    "{peanuts}": 3,
    "$": 5,
    "{usd}": 7,
    "bale": 11,
    "bales": 11,
    "{hay}": 13
}


def __match_reverse_lookup(lookup_value):
    """Reverse hash lookup
    """
    return [key for key,
            value in match_prime_lookup.items() if value == lookup_value]


def __format_quantity(quantity):
    value_magnitude = int.from_bytes(quantity.value, byteorder='little')
    value_units = __match_reverse_lookup(
        int.from_bytes(quantity.valueUnit, byteorder='little'))
    value_unit = value_units[0]
    if value_magnitude > 1 and value_unit.endswith('s') is True:
        value_unit = value_units[1]
    resource_unit = __match_reverse_lookup(
        int.from_bytes(quantity.resourceUnit, byteorder='little'))[0]
    return '{} {} of {}'.format(
        value_magnitude,
        value_unit,
        resource_unit)


def __decode_match(address, data):
    """Decode a unmatched or matched address
    """
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
    return {
        'family': 'match',
        'dimension': dim,
        'operation': operation,
        'data': match
    }


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
    results = __get_list_data(address)['data']
    ops = __revmachadd[address[18:24]]

    data = []
    for element in results:
        ladd = element['address']
        utxq = UTXQ()
        utxq.ParseFromString(b64decode(__get_leaf_data(ladd)['data']))
        data.append((
            {
                "plus": utxq.plus.decode("utf-8"),
                "minus": utxq.minus.decode("utf-8"),
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
    results = __get_list_data(address)['data']
    ops = __revmachadd[address[18:24]]

    data = []
    for element in results:
        ladd = element['address']
        mtxq = MTXQ()
        mtxq.ParseFromString(b64decode(__get_leaf_data(ladd)['data']))
        data.append(({
            "plus": mtxq.plus.decode("utf-8"),
            "minus": mtxq.minus.decode("utf-8"),
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
            Address._candidates_hash: decode_proposals,
            Address._unit_hash: __decode_asset,
            Address._resource_hash: __decode_asset
        },
        Address._match_hash: {
            Address._utxq_hash: __decode_match,
            Address._mtxq_hash: __decode_match
        },
        Address._setting_hash: {
            Address._unit_hash: decode_settings,
            Address._resource_hash: decode_settings
        }
    }
}


def decode_from_leaf(address):
    leaf = __get_leaf_data(address)
    y = _hash_map[address[:6]][address[6:12]][address[12:18]]
    return y(address, b64decode(leaf['data']))
