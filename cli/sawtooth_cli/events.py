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


EVENTS_NAMESPACE = hashlib.sha512('events'.encode("utf-8")).hexdigest()[0:6]

_MIN_PRINT_WIDTH = 15
_MAX_KEY_PARTS = 4
_ADDRESS_PART_SIZE = 16


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
    state = rest_client.list_state(subtree=EVENTS_NAMESPACE)

    prefix = args.filter

    head = state['head']
    state_values = state['data']
    printable_events = []
    initiate_address = _key_to_address('hashblock.events.initiate')
    for state_value in state_values:
        if state_value['address'] == initiate_address:
            # This is an initiate event and we won't list it here
            continue

        decoded = b64decode(state_value['data'])
        events = ReciprocateEvent()
        events.ParseFromString(decoded)

        for entry in events.entries:
            if entry.key.startswith(prefix):
                printable_events.append(entry)

    printable_events.sort(key=lambda s: s.key)

    if args.format == 'default':
        tty_width = tty.width()
        for event in printable_events:
            # Set value width to the available terminal space, or the min width
            width = tty_width - len(event.key) - 3
            width = width if width > _MIN_PRINT_WIDTH else _MIN_PRINT_WIDTH
            value = (event.value[:width] + '...'
                     if len(event.value) > width
                     else event.value)
            print('{}: {}'.format(event.key, value))
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


def _key_to_address(key):
    """Creates the state address for a given event of measure key.
    """
    key_parts = key.split('.', maxsplit=_MAX_KEY_PARTS - 1)
    key_parts.extend([''] * (_MAX_KEY_PARTS - len(key_parts)))

    return EVENTS_NAMESPACE + ''.join(_short_hash(x) for x in key_parts)


def _short_hash(in_str):
    return hashlib.sha256(in_str.encode()).hexdigest()[:_ADDRESS_PART_SIZE]
