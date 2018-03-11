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

import argparse

_listOptionList = [
    'all',
    'utxq',
    'mtxq',
    'ask',
    'tell',
    'offer',
    'accept',
    'commitment',
    'obligation',
    'give',
    'take']

_listCmdMap = {
    '-u': {
        'help': 'url of rest server, default is http://rest-api:8008',
        'default': 'http://rest-api:8008',
        'dest': 'url'},
    '-t': {
        'help': "filter listing to type, default is 'all'",
        'default': 'all',
        'choices': _listOptionList,
        'dest': 'listtype'},
    '-f': {
        'help': "format listing to type, default is 'default'",
        'default': 'default',
        'choices': ['default', 'json', 'yaml'],
        'dest': 'format'}}

_inititateCmdMap = {
    '-a': {
        'help': 'address of related/prior MTXQ item (optional)',
        'default': None,
        'dest': 'mtxq'},
    '-u': {
        'help': 'url of rest server for submissions',
        'default': 'http://rest-api:8008',
        'dest': 'url'},
    '-k': {
        'help': 'public signing key for batch',
        'default': '/root/.sawtooth/keys/your_key.priv',
        'dest': 'skey'},
    '-p': {
        'help': 'specifies the public key (TBD)',
        'default': None,
        'dest': 'pkey'},
    '-m': {
        'help': 'specifies the minus key (TBD)',
        'default': None,
        'dest': 'mkey'},
    '-x': {
        'help': 'initiating expression (required)',
        'default': None,
        'required': True,
        'dest': 'expr'}}

_reciprocateCmdMap = {
    '-a': {
        'help': 'address of UTXQ item (required)',
        'default': None,
        'type': str,
        'required': True,
        'dest': 'utxq'},
    '-u': {
        'help': 'url of rest server for submissions',
        'default': 'http://rest-api:8008',
        'dest': 'url'},
    '-k': {
        'help': 'private signing key for batch',
        'default': '/root/.sawtooth/keys/your_key.priv',
        'dest': 'skey'},
    '-p': {
        'help': 'specifies the plus key (TBD)',
        'default': None,
        'dest': 'pkey'},
    '-m': {
        'help': 'specifies the minus key (TBD)',
        'default': None,
        'dest': 'mkey'},
    '-x': {
        'help': 'reciprocating expression (required)',
        'default': None,
        'required': True,
        'nargs': 5,
        'dest': 'expr'}}

_v2map = {
    'list': {
        'help': 'lists TXQ type ledger entries',
        'child': _listCmdMap},
    'ask': {
        'help': 'ask transaction, initiates the block',
        'child': _inititateCmdMap},
    'tell': {
        'help': 'a reciprocating tell for an ask',
        'child': _reciprocateCmdMap},
    'offer': {
        'help': 'create an offer, optionaly on a tell response',
        'child': _inititateCmdMap},
    'accept': {
        'help': 'accept an offer',
        'child': _reciprocateCmdMap},
    'commitment': {
        'help': 'a commitment, optionally on accepted offer',
        'child': _inititateCmdMap},
    'obligation': {
        'help': 'obligation to commitment',
        'child': _reciprocateCmdMap},
    'give': {
        'help': 'give something',
        'child': _inititateCmdMap},
    'take': {
        'help': 'take what is given',
        'child': _reciprocateCmdMap}}


def __gensub(subprs, subcnd, nblock):
    """
    Private function to imbue the commands and associated
    options
    """
    child = nblock['child']
    del nblock['child']
    p = subprs.add_parser(subcnd, **nblock)
    for arg, kwds in child.items():
        p.add_argument(arg, **kwds)


def create_txq_cli_parser(parent_parser):
    """
    Creates the command line parser from the
    parent_parser and sets up all the options
    """

    # Initialize the parser
    parser = argparse.ArgumentParser(
        description='Provides commands to '
        'list addresses, to create initiating (unmatched) '
        'transactions, and to create reciprocating (matched) transactions.',
        usage='%(prog)s [-h] [list | #B TXQ] [subcommand arguments]',
        parents=[parent_parser])

    # Generate a subparser for the heavy lifing
    subparse = parser.add_subparsers(
        title='commands',
        dest='cmd',
        description='valid subcommands')

    # Setup the commands and their respective options
    [__gensub(subparse, k, v)
        for k, v in _v2map.items()]

    return parser
