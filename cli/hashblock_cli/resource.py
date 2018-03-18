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

from hashblock_cli.exceptions import CliException
from hashblock_cli.rest_client import RestClient
from hashblock_cli import tty

from hashblock_cli.protobuf.resource_pb2 import Resource


RESOURCE_NAMESPACE = hashlib.sha512(
    'hashblock_resource'.encode("utf-8")).hexdigest()[0:6]

_MIN_PRINT_WIDTH = 15
_MAX_KEY_PARTS = 4
_ADDRESS_PART_SIZE = 16


def add_resource_parser(subparsers, parent_parser):
    """Creates the args parser needed for the resource command and its
    subcommands.
    """
    # The following parser is for the resource subsection of commands.  These
    # commands display information about the currently applied on-chain
    # resource.

    resource_parser = subparsers.add_parser(
        'resource',
        help='Displays on-chain resource',
        description='Displays the values of currently active on-chain '
                    'resource.')

    resource_parsers = resource_parser.add_subparsers(
        title='resource',
        dest='resource_cmd')
    resource_parsers.required = True

    list_parser = resource_parsers.add_parser(
        'list',
        help='Lists the current keys and values of on-chain resource',
        description='List the current keys and values of on-chain '
                    'resource. The content can be exported to various '
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


def do_resource(args):
    if args.resource_cmd == 'list':
        _do_resource_list(args)
    else:
        raise AssertionError('Invalid subcommand: ')


def _do_resource_list(args):
    """Lists the current on-chain resource values.
    """
    rest_client = RestClient(args.url)
    state = rest_client.list_state(subtree=RESOURCE_NAMESPACE)

    prefix = args.filter

    head = state['head']
    state_values = state['data']
    printable_resource = []
    proposals_address = _key_to_address('hashblock.resource.vote.proposals')
    for state_value in state_values:
        if state_value['address'] == proposals_address:
            # This is completely internal resource and we won't list it here
            continue

        decoded = b64decode(state_value['data'])
        resource = Resource()
        resource.ParseFromString(decoded)

        for entry in resource.entries:
            if entry.key.startswith(prefix):
                printable_resource.append(entry)

    printable_resource.sort(key=lambda s: s.key)

    if args.format == 'default':
        tty_width = tty.width()
        for resource in printable_resource:
            # Set value width to the available terminal space, or the min width
            width = tty_width - len(resource.key) - 3
            width = width if width > _MIN_PRINT_WIDTH else _MIN_PRINT_WIDTH
            value = (resource.value[:width] + '...'
                     if len(resource.value) > width
                     else resource.value)
            print('{}: {}'.format(resource.key, value))
    elif args.format == 'csv':
        try:
            writer = csv.writer(sys.stdout, quoting=csv.QUOTE_ALL)
            writer.writerow(['KEY', 'VALUE'])
            for resource in printable_resource:
                writer.writerow([resource.key, resource.value])
        except csv.Error:
            raise CliException('Error writing CSV')
    elif args.format == 'json' or args.format == 'yaml':
        resource_snapshot = {
            'head': head,
            'resource': {resource.key: resource.value
                         for resource in printable_resource}
        }
        if args.format == 'json':
            print(json.dumps(resource_snapshot, indent=2, sort_keys=True))
        else:
            print(yaml.dump(resource_snapshot, default_flow_style=False)[0:-1])
    else:
        raise AssertionError('Unknown format {}'.format(args.format))


def _key_to_address(key):
    """Creates the state address for a given resource of measure key.
    """
    key_parts = key.split('.', maxsplit=_MAX_KEY_PARTS - 1)
    key_parts.extend([''] * (_MAX_KEY_PARTS - len(key_parts)))

    return RESOURCE_NAMESPACE + ''.join(_short_hash(x) for x in key_parts)


def _short_hash(in_str):
    return hashlib.sha256(in_str.encode()).hexdigest()[:_ADDRESS_PART_SIZE]
