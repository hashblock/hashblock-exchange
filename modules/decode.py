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
import hashlib
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
from protobuf.asset_pb2 import AssetCandidate


# Well known hashes

ASSET_HASH = hashlib.sha512(
    Address.FAMILY_ASSET.encode("utf-8")).hexdigest()[0:6]
MATCH_HASH = hashlib.sha512(
    Address.FAMILY_MATCH.encode("utf-8")).hexdigest()[0:6]
SETTING_HASH = hashlib.sha512(
    Address.FAMILY_SETTING.encode("utf-8")).hexdigest()[0:6]
CANDIDATES_HASH = Address._candidates_hash
UNIT_HASH = hashlib.sha512(
    Address.DIMENSION_UNIT.encode("utf-8")).hexdigest()[0:6]
RESOURCE_HASH = hashlib.sha512(
    Address.DIMENSION_RESOURCE.encode("utf-8")).hexdigest()[0:6]
UTXQ_HASH = hashlib.sha512(
    Address.DIMENSION_UTXQ.encode("utf-8")).hexdigest()[0:6]
MTXQ_HASH = hashlib.sha512(
    Address.DIMENSION_MTXQ.encode("utf-8")).hexdigest()[0:6]


def _decode_settings(data, address):
    settings = Settings()
    settings.ParseFromString(data)
    return {
        'family': 'setting',
        'address': address,
        'data': MessageToDict(settings)
    }


def _decode_proposals(data, address):
    candidates = AssetCandidate()
    candidates.ParseFromString(data)
    return {
        'family': 'asset',
        'address': address,
        'data': MessageToDict(candidates)
    }


def _decode_asset(data, address):
    asset = Unit() if address[18:24] == UNIT_HASH else Resource()
    asset.ParseFromString(data)
    return {
        'family': 'asset',
        'address': address,
        'data': MessageToDict(asset)
    }


def _decode_match(data, address):
    match = UTXQ() if address[12:18] == UTXQ_HASH else MTXQ()
    match.ParseFromString(data)
    return {
        'family': 'match',
        'address': address,
        'data': MessageToDict(match)
    }


_hash_map = {
    Address._namespace_hash: {
        ASSET_HASH: {
            Address._candidates_hash: _decode_proposals,
            UNIT_HASH: _decode_asset,
            RESOURCE_HASH: _decode_asset
        },
        MATCH_HASH: {
            UTXQ_HASH: _decode_match,
            MTXQ_HASH: _decode_match
        },
        SETTING_HASH: {
            UNIT_HASH: _decode_settings,
            RESOURCE_HASH: _decode_settings
        }
    }
}


def decode_from_leaf(address):
    node = REST_CONFIG['rest']['hosts']['local']
    leaf = RestClient(node).get_leaf(address)
    y = _hash_map[address[:6]][address[6:12]][address[12:18]]
    return y(b64decode(leaf['data']), address)
