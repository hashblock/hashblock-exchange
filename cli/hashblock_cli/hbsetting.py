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

import argparse
from base64 import b64decode
import csv
import datetime
import getpass
import hashlib
import json
import logging
import os
import sys
import traceback
import yaml

import pkg_resources
from colorlog import ColoredFormatter

from hashblock_cli.exceptions import CliException
from hashblock_cli.rest_client import RestClient

from hashblock_cli.protobuf.setting_pb2 import SettingPayload
from hashblock_cli.protobuf.setting_pb2 import Settings
from hashblock_cli.protobuf.transaction_pb2 import TransactionHeader
from hashblock_cli.protobuf.transaction_pb2 import Transaction
from hashblock_cli.protobuf.batch_pb2 import BatchHeader
from hashblock_cli.protobuf.batch_pb2 import Batch
from hashblock_cli.protobuf.batch_pb2 import BatchList

from sawtooth_signing import create_context
from sawtooth_signing import CryptoFactory
from sawtooth_signing import ParseError
from sawtooth_signing.secp256k1 import Secp256k1PrivateKey
from sdk.python.address import Address

_addresser = Address(Address.FAMILY_SETTING)

DISTRIBUTION_NAME = 'setset'


def add_config_parser(subparsers, parent_parser):
    """Creates the arg parsers needed for the config command and
    its subcommands.
    """
    parser = subparsers.add_parser(
        'config',
        help='Changes genesis block units and create, view, and '
        'vote on units proposals',
        description='Provides subcommands to change genesis block settings '
                    'and to view, create, and vote on existing proposals.'
    )

    config_parsers = parser.add_subparsers(title="subcommands",
                                           dest="subcommand")
    config_parsers.required = True


def _do_config_setting_create(args):
    """Executes the 'settings create' subcommand.  Given a key file, and a
    series of code/value pairs, it generates batches of hashblock_units
    transactions in a BatchList instance.  The BatchList is either stored to a
    file or submitted to a validator, depending on the supplied CLI arguments.
    """
    units = [s.split('=', 1) for s in args.unit]

    signer = _read_signer(args.key)

    txns = [_create_propose_txn(signer, unit)
            for unit in units]

    batch = _create_batch(signer, txns)

    batch_list = BatchList(batches=[batch])

    if args.output is not None:
        try:
            with open(args.output, 'wb') as batch_file:
                batch_file.write(batch_list.SerializeToString())
        except IOError as e:
            raise CliException(
                'Unable to write to batch file: {}'.format(str(e)))
    elif args.url is not None:
        rest_client = RestClient(args.url)
        rest_client.send_batches(batch_list)
    else:
        raise AssertionError('No target for create set.')


def _do_config_setting_list(args):
    """Executes the 'setting list' subcommand.

    Given a url, optional filters on prefix and public key, this command lists
    the current pending proposals for units changes.
    """
    pass


def _do_config_genesis(args):
    signer = _read_signer(args.key)
    public_key = signer.get_public_key().as_hex()

    authorized_keys = args.authorized_key if args.authorized_key else \
        [public_key]
    if public_key not in authorized_keys:
        authorized_keys.append(public_key)

    txns = []

    keys = ','.join(authorized_keys)
    threshold = str(args.approval_threshold)

    if args.approval_threshold is not None:
        if args.approval_threshold < 1:
            raise CliException('approval threshold must not be less than 1')

        if args.approval_threshold > len(authorized_keys):
            raise CliException(
                'approval threshold must not be greater than the number of '
                'authorized keys')

    txns.append(_create_setting(
        signer,
        Address.DIMENSION_UNIT,
        SettingPayload.CREATE,
        keys, threshold))
    txns.append(_create_setting(
        signer,
        Address.DIMENSION_RESOURCE,
        SettingPayload.CREATE,
        keys, threshold))

    batch = _create_batch(signer, txns)
    batch_list = BatchList(batches=[batch])

    try:
        with open(args.output, 'wb') as batch_file:
            batch_file.write(batch_list.SerializeToString())
        print('Generated {}'.format(args.output))
    except IOError as e:
        raise CliException(
            'Unable to write to batch file: {}'.format(str(e)))


def _create_setting(signer, dimension, action, auth_keys, threshold):
    # nonce = str(datetime.datetime.utcnow().timestamp())
    settings = Settings(
        auth_list=auth_keys,
        threshold=threshold)
    payload = SettingPayload(
        action=action,
        dimension=dimension,
        data=settings.SerializeToString())

    return _make_setting_txn(signer, dimension, payload)


def _make_setting_txn(signer, dimension, payload):
    """Creates and signs a hashblock_units transaction with with a payload.
    """
    props = Address(Address.FAMILY_ASSET)
    serialized_payload = payload.SerializeToString()
    header = TransactionHeader(
        nonce=str(datetime.datetime.utcnow().timestamp()),
        signer_public_key=signer.get_public_key().as_hex(),
        family_name=Address.NAMESPACE_SETTING,
        family_version='1.0.0',
        inputs=[
            _addresser.settings(dimension),
            props.candidates(dimension)],
        outputs=[
            _addresser.settings(dimension),
            props.candidates(dimension)],
        dependencies=[],
        payload_sha512=hashlib.sha512(serialized_payload).hexdigest(),
        batcher_public_key=signer.get_public_key().as_hex()
    ).SerializeToString()

    return Transaction(
        header=header,
        header_signature=signer.sign(header),
        payload=serialized_payload)


def _get_proposals(rest_client):
    pass


def _read_signer(key_filename):
    """Reads the given file as a hex key.

    Args:
        key_filename: The filename where the key is stored. If None,
            defaults to the default key for the current user.

    Returns:
        Signer: the signer

    Raises:
        CliException: If unable to read the file.
    """
    filename = key_filename
    if filename is None:
        filename = os.path.join(os.path.expanduser('~'),
                                '.sawtooth',
                                'keys',
                                getpass.getuser() + '.priv')

    try:
        with open(filename, 'r') as key_file:
            signing_key = key_file.read().strip()
    except IOError as e:
        raise CliException('Unable to read key file: {}'.format(str(e)))

    try:
        private_key = Secp256k1PrivateKey.from_hex(signing_key)
    except ParseError as e:
        raise CliException('Unable to read key in file: {}'.format(str(e)))

    context = create_context('secp256k1')
    crypto_factory = CryptoFactory(context)
    return crypto_factory.new_signer(private_key)


def _create_batch(signer, transactions):
    """Creates a batch from a list of transactions and a public key, and signs
    the resulting batch with the given signing key.

    Args:
        signer (:obj:`Signer`): The cryptographic signer
        transactions (list of `Transaction`): The transactions to add to the
            batch.

    Returns:
        `Batch`: The constructed and signed batch.
    """
    txn_ids = [txn.header_signature for txn in transactions]
    batch_header = BatchHeader(
        signer_public_key=signer.get_public_key().as_hex(),
        transaction_ids=txn_ids).SerializeToString()

    return Batch(
        header=batch_header,
        header_signature=signer.sign(batch_header),
        transactions=transactions)


def _create_propose_txn(signer, unit_key_value):
    """Creates an individual hashblock_units transaction for the given key and
    value.
    """
    pass


def _create_vote_txn(signer, proposal_id, unit_key, vote_value):
    """Creates an individual hashblock_units transaction for voting on a
    proposal for a particular unit key.
    """
    pass


def _make_txn(signer, unit_key, payload):
    """Creates and signs a hashblock_units transaction with with a payload.
    """
    serialized_payload = payload.SerializeToString()
    header = TransactionHeader(
        nonce=str(datetime.datetime.utcnow().timestamp()),
        signer_public_key=signer.get_public_key().as_hex(),
        family_name=Address.NAMESPACE_SETTING,
        family_version='1.0.0',
        inputs=_config_inputs(unit_key),
        outputs=_config_outputs(unit_key),
        dependencies=[],
        payload_sha512=hashlib.sha512(serialized_payload).hexdigest(),
        batcher_public_key=signer.get_public_key().as_hex()
    ).SerializeToString()

    return Transaction(
        header=header,
        header_signature=signer.sign(header),
        payload=serialized_payload)


def _config_inputs(key):
    """Creates the list of inputs for a hashblock_units transaction, for a
    given unit key.
    """
    return []


def _config_outputs(key):
    """Creates the list of outputs for a hashblock_units transaction, for a
    given unit key.
    """
    return []


def create_console_handler(verbose_level):
    clog = logging.StreamHandler()
    formatter = ColoredFormatter(
        "%(log_color)s[%(asctime)s %(levelname)-8s%(module)s]%(reset)s "
        "%(white)s%(message)s",
        datefmt="%H:%M:%S",
        reset=True,
        log_colors={
            'DEBUG': 'cyan',
            'INFO': 'green',
            'WARNING': 'yellow',
            'ERROR': 'red',
            'CRITICAL': 'red',
        })

    clog.setFormatter(formatter)

    if verbose_level == 0:
        clog.setLevel(logging.WARN)
    elif verbose_level == 1:
        clog.setLevel(logging.INFO)
    else:
        clog.setLevel(logging.DEBUG)

    return clog


def setup_loggers(verbose_level):
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    logger.addHandler(create_console_handler(verbose_level))


def create_parent_parser(prog_name):
    parent_parser = argparse.ArgumentParser(prog=prog_name, add_help=False)
    parent_parser.add_argument(
        '-v', '--verbose',
        action='count',
        help='enable more verbose output')

    try:
        version = pkg_resources.get_distribution(DISTRIBUTION_NAME).version
    except pkg_resources.DistributionNotFound:
        version = 'UNKNOWN'

    parent_parser.add_argument(
        '-V', '--version',
        action='version',
        version=(DISTRIBUTION_NAME + ' (Hashblock Sawtooth) version {}')
        .format(version),
        help='display version information')

    return parent_parser


def create_parser(prog_name):
    parent_parser = create_parent_parser(prog_name)

    parser = argparse.ArgumentParser(
        description='Provides subcommands to create genesis block '
        'and to view, create, and update hashblock asset settings.',
        parents=[parent_parser])

    subparsers = parser.add_subparsers(title='subcommands', dest='subcommand')
    subparsers.required = True

    # The following parser is for the `genesis` subcommand.
    # This command creates a batch that contains all of the initial
    # transactions for settings
    genesis_parser = subparsers.add_parser(
        'genesis',
        help='Creates a genesis batch file of settings transactions',
        description='Creates a Batch of asset settings that can be '
                    'consumed by "sawadm genesis" and used '
                    'during genesis hashblock construction.'
    )
    genesis_parser.add_argument(
        '-k', '--key',
        type=str,
        help='specify signing key for resulting batches '
             'and initial authorized key')

    genesis_parser.add_argument(
        '-o', '--output',
        type=str,
        default='config-units.batch',
        help='specify the output file for the resulting batches')

    genesis_parser.add_argument(
        '-T', '--approval-threshold',
        type=int,
        help='set the number of votes required to enable a setting change')

    genesis_parser.add_argument(
        '-A', '--authorized-key',
        type=str,
        action='append',
        help='specify a public key for the user authorized to submit '
             'config transactions')

    # The following parser is for listing settings

    setting_list_parser = subparsers.add_parser(
        'list',
        help='Lists the assets setting',
        description='Lists the asset (all, unit or resource) settings. ')

    setting_list_parser.add_argument(
        '--url',
        type=str,
        help="identify the URL of a validator's REST API",
        default='http://rest-api:8008')

    setting_list_parser.add_argument(
        '--format',
        default='default',
        choices=['default', 'csv', 'json', 'yaml'],
        help='choose the output format')

    # The following parser is for the `proposal` subcommand group. These
    # commands allow the user to create proposals which may be applied
    # immediately or placed in ballot mode, depending on the current on-chain
    # units.

    setting_parser = subparsers.add_parser(
        'setting',
        help='Views, creates, or modifies settings for assets',
        description='Provides subcommands to view, create, '
        'or modify settings ')
    setting_parsers = setting_parser.add_subparsers(
        title='subcommands',
        dest='setting_cmd')
    setting_parsers.required = True

    create_parser = setting_parsers.add_parser(
        'create',
        help='Creates setting',
        description='Create settings key value for asset management. '
                    'The change is applied immediately.'
    )

    create_parser.add_argument(
        '-k', '--key',
        type=str,
        help='specify a signing key for the resulting batches')

    create_target_group = create_parser.add_mutually_exclusive_group()
    create_target_group.add_argument(
        '-o', '--output',
        type=str,
        help='specify the output file for the resulting batches')

    create_target_group.add_argument(
        '--url',
        type=str,
        help="identify the URL of a validator's REST API",
        default='http://rest-api:8008')

    create_parser.add_argument(
        'unit',
        type=str,
        nargs='+',
        help='configuration unit as key/value pair with the '
        'format <code>=<value>')

    return parser


def main(prog_name=os.path.basename(sys.argv[0]), args=None,
         with_loggers=True):
    parser = create_parser(prog_name)
    if args is None:
        args = sys.argv[1:]
    args = parser.parse_args(args)

    if with_loggers is True:
        if args.verbose is None:
            verbose_level = 0
        else:
            verbose_level = args.verbose
        setup_loggers(verbose_level=verbose_level)

    if args.subcommand == 'setting' and args.setting_cmd == 'create':
        _do_config_setting_create(args)
    elif args.subcommand == 'list':
        _do_config_setting_list(args)
    elif args.subcommand == 'genesis':
        _do_config_genesis(args)
    else:
        raise CliException(
            '"{}" is not a valid subcommand of "config"'.format(
                args.subcommand))


def main_wrapper():
    # pylint: disable=bare-except
    try:
        main()
    except CliException as e:
        print("Error: {}".format(e), file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        pass
    except BrokenPipeError:
        sys.stderr.close()
    except SystemExit as e:
        raise e
    except:
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)

