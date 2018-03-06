# Copyright 2017 Intel Corporation
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

from base64 import b64decode
import csv
import hashlib
import json
import sys

import yaml

from sawtooth_cli.exceptions import CliException
from sawtooth_cli.rest_client import RestClient
from sawtooth_cli import tty

from sawtooth_cli.protobuf.events_pb2 import ReciprocateEvent

ADDRESS_PREFIX = 'events'
FAMILY_NAME = 'hashblock_events'

RECIPROCATE_EVENT_KEY = 'reciprocate.' 
INITIATE_EVENT_KEY = 'initiate.'
EVENTS_NAMESPACE = hashlib.sha512('events'.encode("utf-8")).hexdigest()[0:6]
RECIPROCATE_LIST_ADDRESS = EVENTS_NAMESPACE + \
    hashlib.sha512(RECIPROCATE_EVENT_KEY.encode("utf-8")).hexdigest()[0:6]

_MIN_PRINT_WIDTH = 15
_MAX_KEY_PARTS = 4
_ADDRESS_PART_SIZE = 16

hash_lookup = {
    "bag": 2,
    "bags": 2,
    "{peanuts}":3,
    "$":5,
    "{usd}":7,
    "bale":11,
    "bales":11,
    "{hay}":13
}


def add_events_parser(subparsers, parent_parser):
    """Creates the args parser needed for the events command and its
    subcommands.
    """
    # The following parser is for the events subsection of commands.  These
    # commands display information about the currently applied on-chain
    # events.

    events_parser = subparsers.add_parser(
        'events',
        help='Displays on-chain events',
        description='Displays the values of currently active on-chain '
                    'events.')

    events_parsers = events_parser.add_subparsers(
        title='events',
        dest='events_cmd')
    events_parsers.required = True

    list_parser = events_parsers.add_parser(
        'list',
        help='Lists the current keys and values of on-chain events',
        description='List the current keys and values of on-chain '
                    'events. The content can be exported to various '
                    'formats for external consumption.'
    )

    list_parser.add_argument(
        '--url',
        type=str,
        help="identify the URL of a validator's REST API",
        default='http://rest-api:8008')

    list_parser.add_argument(
        '--filter',
        type=str,
        default='',
        help='filters keys that begin with this value')

    list_parser.add_argument(
        '--format',
        default='default',
        choices=['default', 'csv', 'json', 'yaml'],
        help='choose the output format')


def do_events(args):
    if args.events_cmd == 'list':
        _do_events_list(args)
    else:
        raise AssertionError('Invalid subcommand: ')


def _do_events_list(args):
    """Lists the current on-chain event values.
    """
    rest_client = RestClient(args.url)
    state_leaf = rest_client.list_state(RECIPROCATE_LIST_ADDRESS)

    printable_events = []
    for event_state_leaf in state_leaf['data']:
        if event_state_leaf is not None:
            decoded = b64decode(event_state_leaf['data'])
            event = ReciprocateEvent()
            event.ParseFromString(decoded)
            printable_events.append([event_state_leaf['address'],event])

    if args.format == 'default':
        for event in printable_events:
            i_value = int.from_bytes(event[1].initiateEvent.quantity.value, byteorder='little') 
            i_value_units = _hash_reverse_lookup(int.from_bytes(event[1].initiateEvent.quantity.valueUnit, byteorder='little'))
            i_value_unit = i_value_units[0]
            if i_value > 1 and i_value_unit.endswith('s') == False:
                i_value_unit = i_value_units[1]
            i_resource_unit = _hash_reverse_lookup(int.from_bytes(event[1].initiateEvent.quantity.resourceUnit, byteorder='little'))[0]

            n_value = int.from_bytes(event[1].ratio.numerator.value, byteorder='little')
            n_value_units = _hash_reverse_lookup(int.from_bytes(event[1].ratio.numerator.valueUnit, byteorder='little'))
            n_value_unit = n_value_units[0]
            n_resource_unit = _hash_reverse_lookup(int.from_bytes(event[1].ratio.numerator.resourceUnit, byteorder='little'))[0]

            d_value = int.from_bytes(event[1].ratio.denominator.value, byteorder='little')
            d_value_units = _hash_reverse_lookup(int.from_bytes(event[1].ratio.denominator.valueUnit, byteorder='little'))
            d_value_unit = d_value_units[0]
            if d_value > 1 and d_value_unit.endswith('s') == False:
                d_value_unit = d_value_units[1]
            d_resource_unit = _hash_reverse_lookup(int.from_bytes(event[1].ratio.denominator.resourceUnit, byteorder='little'))[0]

            r_value = int.from_bytes(event[1].quantity.value, byteorder='little')
            r_value_units = _hash_reverse_lookup(int.from_bytes(event[1].quantity.valueUnit, byteorder='little'))
            r_value_unit = r_value_units[0]
            r_resource_unit = _hash_reverse_lookup(int.from_bytes(event[1].quantity.resourceUnit, byteorder='little'))[0]

            print('{}\n\r\t({}.{}{} * {}{}{}) / {}.{}{} = {}{}{}'.format(
                event[0],
                i_value, i_value_unit, i_resource_unit,
                n_value_unit, n_value, n_resource_unit,
                d_value, d_value_unit, d_resource_unit,
                r_value_unit, r_value, r_resource_unit))
    elif args.format == 'csv':
        try:
            writer = csv.writer(sys.stdout, quoting=csv.QUOTE_ALL)
            writer.writerow(['KEY', 'VALUE'])
            for event in printable_events:
                writer.writerow([event.key, event.value])
        except csv.Error:
            raise CliException('Error writing CSV')
    elif args.format == 'json' or args.format == 'yaml':
        events_snapshot = {
            'head': head,
            'events': {event.key: event.value
                         for event in printable_events}
        }
        if args.format == 'json':
            print(json.dumps(events_snapshot, indent=2, sort_keys=True))
        else:
            print(yaml.dump(events_snapshot, default_flow_style=False)[0:-1])
    else:
        raise AssertionError('Unknown format {}'.format(args.format))


def _hash_reverse_lookup(lookup_value):
    """Reverse hash lookup
    """
    return [key for key, value in hash_lookup.items() if value == lookup_value]


def _key_to_address(key):
    """Creates the state address for a given event of measure key.
    """
    key_parts = key.split('.', maxsplit=_MAX_KEY_PARTS - 1)
    key_parts.extend([''] * (_MAX_KEY_PARTS - len(key_parts)))

    return EVENTS_NAMESPACE + ''.join(_short_hash(x) for x in key_parts)


def _short_hash(in_str):
    return hashlib.sha256(in_str.encode()).hexdigest()[:_ADDRESS_PART_SIZE]




