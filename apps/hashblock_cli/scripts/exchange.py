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

import shared.langparse as parse
from shared.transactions import initialize_txn_vc


def add_exchange_menu(subparsers, parent_parser):
    parser = subparsers.add_parser(
        'exchange',
        help='Generates exchange transactions from expression',
        description='UTXQ/MTXQ expression transaction submission '
        'with parsing validation.',
        parents=[parent_parser])

    parser.add_argument(
        '-n', '--namespace',
        help='specify the namespace for exchange if using -e')

    parser.add_argument(
        '-e', '--expression',
        help='specify the exchange expression')

    parser.add_argument(
        '-f', '--file',
        help='specify the file containing expression')

    parser.add_argument(
        '-q',
        '--quiet',
        help="do not display output",
        action='store_true')


def do_exchange(args, logger):
    print("Args = {}".format(args))
    if args.namespace and args.expression:
        parse.initialize_parse()
        parse.parse_with_ns(args.namespace, args.expression)
        initialize_txn_vc()
    else:
        print("Not loading")
