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
import csv
import sys
from base64 import b64decode
from hashblock_cli.protobuf.match_pb2 import UTXQ
from hashblock_cli.protobuf.match_pb2 import MTXQ

from hashblock_cli.txqcommon import hash_lookup
from hashblock_cli.txqcommon import ADDRESS_PREFIX
from hashblock_cli.txqcommon import MATCH_NAMESPACE
from hashblock_cli.txqcommon import INITIATE_LIST_ADDRESS
from hashblock_cli.txqcommon import RECIPROCATE_LIST_ADDRESS


_QUERY_KEY_MAP = {
    'ask': INITIATE_LIST_ADDRESS +
    hashlib.sha512('ask'.encode("utf-8")).hexdigest()[0:6],
    'tell': RECIPROCATE_LIST_ADDRESS +
    hashlib.sha512('tell'.encode("utf-8")).hexdigest()[0:6],
    'offer': INITIATE_LIST_ADDRESS +
    hashlib.sha512('offer'.encode("utf-8")).hexdigest()[0:6],
    'accept': RECIPROCATE_LIST_ADDRESS +
    hashlib.sha512('accept'.encode("utf-8")).hexdigest()[0:6],
    'commitment': RECIPROCATE_LIST_ADDRESS +
    hashlib.sha512('commitment'.encode("utf-8")).hexdigest()[0:6],
    'obligation': INITIATE_LIST_ADDRESS +
    hashlib.sha512('obligation'.encode("utf-8")).hexdigest()[0:6],
    'give': INITIATE_LIST_ADDRESS +
    hashlib.sha512('give'.encode("utf-8")).hexdigest()[0:6],
    'take': RECIPROCATE_LIST_ADDRESS +
    hashlib.sha512('take'.encode("utf-8")).hexdigest()[0:6]}


# Addresses are string length 70 where:
# Chars 0-5 are family (e.g. hashblock_match vs. hashblock_units, etc.)
# Chars 6-11 are class (e.g. UTXQ vs. MTXQ)
# Chars 12-17 are subtypes (e.g. ask vs. tell, etc.)

_META_FAMILY = {
    MATCH_NAMESPACE: ADDRESS_PREFIX
}

_META_CLASS = {
    INITIATE_LIST_ADDRESS: 'UTXQ',
    RECIPROCATE_LIST_ADDRESS: 'MTXQ'
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


def __hash_reverse_lookup(lookup_value):
    """Reverse hash lookup
    """
    return [key for key, value in hash_lookup.items() if value == lookup_value]


def __meta_dictionary(address):
    """Address classifier
    """
    meta_dict = {'family': None, 'class': 'all', 'subtype': 'all'}
    meta_dict['family'] = _META_FAMILY[address[0:6]]
    if len(address) >= 12:
        meta_dict['class'] = _META_CLASS[address[0:12]]
    if len(address) >= 18:
        meta_dict['subtype'] = _META_SUBTYPE[address[0:18]]
    return meta_dict


def __print_default(instance=None, event_id=None, meta_data=None):
    value_magnitude = int.from_bytes(
        instance.quantity.value, byteorder='little')
    value_units = __hash_reverse_lookup(
        int.from_bytes(instance.quantity.valueUnit, byteorder='little'))
    value_unit = value_units[0]
    if value_magnitude > 1 and value_unit.endswith('s') is False:
        value_unit = value_units[1]
    resource_unit = __hash_reverse_lookup(
        int.from_bytes(instance.quantity.resourceUnit, byteorder='little'))[0]
    print('{} => [{}:{}] {}.{}{}'.format(
        event_id,
        meta_data['class'],
        meta_data['subtype'],
        value_magnitude,
        value_unit,
        resource_unit))


def __print_csv(instance=None, event_id=None, meta_data=None):
    writer = csv.writer(sys.stdout, quoting=csv.QUOTE_ALL)
    writer.writerow(['ADDESS', 'VALUE', 'VALUEUNIT', 'RESOURCEUNIT'])
    writer.writerow([
        event_id,
        int.from_bytes(instance.quantity.value, byteorder='little'),
        int.from_bytes(instance.quantity.valueUnit, byteorder='little'),
        int.from_bytes(instance.quantity.resourceUnit, byteorder='little')])


OUTPUT_MAP = {
    'default': __print_default
}


def __get_query_address(listing_type):
    if listing_type == 'all':
            qadd = MATCH_NAMESPACE
    elif listing_type == 'utxq':
        qadd = INITIATE_LIST_ADDRESS
    elif listing_type == 'mtxq':
        qadd = RECIPROCATE_LIST_ADDRESS
    else:
        qadd = _QUERY_KEY_MAP[listing_type]

    print(listing_type, "=> ", qadd)
    return qadd


def __instance_for(address, edata):
    if address[:12] == INITIATE_LIST_ADDRESS:
        data = UTXQ()
        data.ParseFromString(b64decode(edata))
    elif address[:12] == RECIPROCATE_LIST_ADDRESS:
        data = MTXQ()
        data.ParseFromString(b64decode(edata))
    else:
        print("Unknown data type in state")
        data = None
    return dict([
        ('instance', data),
        ('event_id', address),
        ('meta_data', __meta_dictionary(address))])


def listing_of(listing_type, format_type, rest_client):
    results = rest_client.list_state(
        __get_query_address(listing_type))['data']
    for exchange in results:
        # argdict =
        OUTPUT_MAP[format_type](
            **__instance_for(exchange['address'], exchange['data']))


def exchange_list_for(listing_type, format_type, rest_client):
    match_events = []
    results = rest_client.list_state(
        __get_query_address(listing_type))['data']

    for exchange in results:
        argdict = __instance_for(exchange['address'], exchange['data'])
        match_events.append(argdict)
    return match_events
