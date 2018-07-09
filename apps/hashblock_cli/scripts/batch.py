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

from __future__ import print_function

from modules.exceptions import CliException
from shared.asset import create_asset_unit_batch


def add_batch_parser(subparsers, parent_parser):
    parser = subparsers.add_parser(
        'batch',
        help='Generates transactions and batch from json file',
        description='Batch import of json files that optimizes'
        'data population. Support for all hashblock TP types.',
        parents=[parent_parser])

    parser.add_argument('target', choices=['asset', 'match', 'setting'])

    parser.add_argument(
        '-f', '--file',
        help='specify the input file')

    parser.add_argument(
        '--url',
        default="http://rest-api:8008",
        help='The sawtooth rest url. Default is http://localhost:8008')

    parser.add_argument(
        '-q',
        '--quiet',
        help="do not display output",
        action='store_true')


def do_batch(args, config):
    print("Args = {}".format(args))

    if args.target == 'asset':
        create_asset_unit_batch(args.file)
