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

from sawtooth_cli.protobuf.units_pb2 import Unit


UNITS_NAMESPACE = hashlib.sha512('units'.encode("utf-8")).hexdigest()[0:6]

_MIN_PRINT_WIDTH = 15
_MAX_KEY_PARTS = 4
_ADDRESS_PART_SIZE = 16


def add_units_parser(subparsers, parent_parser):
    """Creates the args parser needed for the units command and its
    subcommands.
    """
    # The following parser is for the units subsection of commands.  These
    # commands display information about the currently applied on-chain
    # units.

    units_parser = subparsers.add_parser(
        'units',
        help='Displays on-chain units',
        description='Displays the values of currently active on-chain '
                    'units.')

    units_parsers = units_parser.add_subparsers(
        title='units',
        dest='units_cmd')
    units_parsers.required = True

    list_parser = units_parsers.add_parser(
        'list',
        help='Lists the current keys and values of on-chain units',
        description='List the current keys and values of on-chain '
                    'units. The content can be exported to various '
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


def do_units(args):
    if args.units_cmd == 'list':
        _do_units_list(args)
    else:
        raise AssertionError('Invalid subcommand: ')


def _do_units_list(args):
    """Lists the current on-chain unit values.
    """
    rest_client = RestClient(args.url)
    state = rest_client.list_state(subtree=UNITS_NAMESPACE)

    prefix = args.filter

    head = state['head']
    state_values = state['data']
    printable_units = []
    proposals_address = _key_to_address('sawtooth.units.vote.proposals')
    for state_value in state_values:
        if state_value['address'] == proposals_address:
            # This is completely internal unit and we won't list it here
            continue

        decoded = b64decode(state_value['data'])
        units = Unit()
        units.ParseFromString(decoded)

        for entry in units.entries:
            if entry.key.startswith(prefix):
                printable_units.append(entry)

    printable_units.sort(key=lambda s: s.key)

    if args.format == 'default':
        tty_width = tty.width()
        for unit in printable_units:
            # Set value width to the available terminal space, or the min width
            width = tty_width - len(unit.key) - 3
            width = width if width > _MIN_PRINT_WIDTH else _MIN_PRINT_WIDTH
            value = (unit.value[:width] + '...'
                     if len(unit.value) > width
                     else unit.value)
            print('{}: {}'.format(unit.key, value))
    elif args.format == 'csv':
        try:
            writer = csv.writer(sys.stdout, quoting=csv.QUOTE_ALL)
            writer.writerow(['KEY', 'VALUE'])
            for unit in printable_units:
                writer.writerow([unit.key, unit.value])
        except csv.Error:
            raise CliException('Error writing CSV')
    elif args.format == 'json' or args.format == 'yaml':
        units_snapshot = {
            'head': head,
            'units': {unit.key: unit.value
                         for unit in printable_units}
        }
        if args.format == 'json':
            print(json.dumps(units_snapshot, indent=2, sort_keys=True))
        else:
            print(yaml.dump(units_snapshot, default_flow_style=False)[0:-1])
    else:
        raise AssertionError('Unknown format {}'.format(args.format))


def _key_to_address(key):
    """Creates the state address for a given unit of measure key.
    """
    key_parts = key.split('.', maxsplit=_MAX_KEY_PARTS - 1)
    key_parts.extend([''] * (_MAX_KEY_PARTS - len(key_parts)))

    return UNITS_NAMESPACE + ''.join(_short_hash(x) for x in key_parts)


def _short_hash(in_str):
    return hashlib.sha256(in_str.encode()).hexdigest()[:_ADDRESS_PART_SIZE]
