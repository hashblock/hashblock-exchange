# ------------------------------------------------------------------------------
# Copyright 2018 Frank V. Castellucci and Arthur R. Greef
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

import hashlib
from base64 import b64decode
from hashblock_cli.protobuf.match_pb2 import UTXQ
from hashblock_cli.protobuf.match_pb2 import MTXQ
from hashblock_cli.protobuf.match_pb2 import Quantity
from hashblock_cli.protobuf.match_pb2 import Ratio


_ADDRESS_PREFIX = 'hashblock_match'
_MATCH_NAMESPACE = hashlib.sha512(
    _ADDRESS_PREFIX.encode("utf-8")).hexdigest()[0:6]
_INITIATE_LIST_ADDRESS = _MATCH_NAMESPACE + \
    hashlib.sha512('utxq'.encode("utf-8")).hexdigest()[0:6]
_RECIPROCATE_LIST_ADDRESS = _MATCH_NAMESPACE + \
    hashlib.sha512('mtxq'.encode("utf-8")).hexdigest()[0:6]

_QUERY_KEY_MAP = {
    'ask': _INITIATE_LIST_ADDRESS +
    hashlib.sha512('ask'.encode("utf-8")).hexdigest()[0:6],
    'tell': _RECIPROCATE_LIST_ADDRESS +
    hashlib.sha512('tell'.encode("utf-8")).hexdigest()[0:6],
    'offer': _INITIATE_LIST_ADDRESS +
    hashlib.sha512('offer'.encode("utf-8")).hexdigest()[0:6],
    'accept': _RECIPROCATE_LIST_ADDRESS +
    hashlib.sha512('accept'.encode("utf-8")).hexdigest()[0:6],
    'commitment': _RECIPROCATE_LIST_ADDRESS +
    hashlib.sha512('commitment'.encode("utf-8")).hexdigest()[0:6],
    'obligation': _INITIATE_LIST_ADDRESS +
    hashlib.sha512('obligation'.encode("utf-8")).hexdigest()[0:6],
    'give': _INITIATE_LIST_ADDRESS +
    hashlib.sha512('give'.encode("utf-8")).hexdigest()[0:6],
    'take': _RECIPROCATE_LIST_ADDRESS +
    hashlib.sha512('take'.encode("utf-8")).hexdigest()[0:6]}


# Addresses are string length 70 where:
# Chars 0-5 are family (e.g. hashblock_match vs. hashblock_units, etc.)
# Chars 6-11 are class (e.g. UTXQ vs. MTXQ)
# Chars 12-17 are subtypes (e.g. ask vs. tell, etc.)

_META_FAMILY = {
    _MATCH_NAMESPACE: _ADDRESS_PREFIX
}

_META_CLASS = {
    _INITIATE_LIST_ADDRESS: 'UTXQ',
    _RECIPROCATE_LIST_ADDRESS: 'MTXQ'
}

_META_SUBTYPE = {
    _QUERY_KEY_MAP['ask']: 'ask',
    _QUERY_KEY_MAP['tell']: 'tell',
    _QUERY_KEY_MAP['offer']: 'offer',
    _QUERY_KEY_MAP['accept']: 'accept',
    _QUERY_KEY_MAP['commitment']: 'commitment',
    _QUERY_KEY_MAP['obligation']: 'obligation',
    _QUERY_KEY_MAP['give']: 'give',
    _QUERY_KEY_MAP['take']: 'take'
}


def __meta_dictionary(address):
    meta_dict = {'family': None, 'class': 'all', 'subtype': 'all'}
    meta_dict['family'] = _META_FAMILY[address[0:6]]
    if len(address) >= 12:
        meta_dict['class'] = _META_CLASS[address[0:12]]
    if len(address) >= 18:
        meta_dict['subtype'] = _META_SUBTYPE[address[0:18]]
    return meta_dict


def __get_query_address(listing_type):
    if listing_type == 'all':
            qadd = _MATCH_NAMESPACE
    elif listing_type == 'utxq':
        qadd = _INITIATE_LIST_ADDRESS
    elif listing_type == 'mtxq':
        qadd = _RECIPROCATE_LIST_ADDRESS
    else:
        qadd = _QUERY_KEY_MAP[listing_type] + \
            hashlib.sha512(listing_type.encode("utf-8")).hexdigest()[0:6]
    return qadd


def __instance_for(address, edata):
    if address[:12] == _INITIATE_LIST_ADDRESS:
        data = UTXQ()
        data.ParseFromString(b64decode(edata))
    elif address[:12] == _RECIPROCATE_LIST_ADDRESS:
        data = MTXQ()
        data.ParseFromString(b64decode(edata))
    else:
        print("Unknown data type in state")
        data = None
    return dict([
        ('instance', data),
        ('event_id', address),
        ('meta_data', __meta_dictionary(address))])


def exchange_list_for(listing_type, format_type, rest_client):
    match_events = []
    results = rest_client.list_state(
        __get_query_address(listing_type))['data']

    for exchange in results:
        match_events.append(
            __instance_for(exchange['address'], exchange['data']))
    return match_events
