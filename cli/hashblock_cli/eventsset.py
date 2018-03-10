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
import urllib.request
import uuid
import yaml

import pkg_resources
from colorlog import ColoredFormatter

from sawtooth_cli.exceptions import CliException
from sawtooth_cli.rest_client import RestClient
from sawtooth_cli.parser import parser

from hashblock_cli.protobuf.exchange_pb2 import TransactionPayload
from hashblock_cli.protobuf.exchange_pb2 import UTXQ
from hashblock_cli.protobuf.exchange_pb2 import MTXQ
from hashblock_cli.protobuf.exchange_pb2 import Quantity
from hashblock_cli.protobuf.exchange_pb2 import Ratio
from hashblock_cli.protobuf.exchange_pb2 import UnmatchedEvent
from hashblock_cli.protobuf.transaction_pb2 import TransactionHeader
from hashblock_cli.protobuf.transaction_pb2 import Transaction
from hashblock_cli.protobuf.batch_pb2 import BatchHeader
from hashblock_cli.protobuf.batch_pb2 import Batch
from hashblock_cli.protobuf.batch_pb2 import BatchList

from sawtooth_signing import create_context
from sawtooth_signing import CryptoFactory
from sawtooth_signing import ParseError
from sawtooth_signing.secp256k1 import Secp256k1PrivateKey

DISTRIBUTION_NAME = 'eventsset'
INITIATE_EVENT_KEY = 'utxq.'
RECIPROCATE_EVENT_KEY = 'mtxq.'

EVENTS_NAMESPACE = hashlib.sha512('exchanges'.encode("utf-8")).hexdigest()[0:6]
INITIATE_LIST_ADDRESS = EVENTS_NAMESPACE + \
    hashlib.sha512(INITIATE_EVENT_KEY.encode("utf-8")).hexdigest()[0:6]

_MIN_PRINT_WIDTH = 15
_MAX_KEY_PARTS = 4
_ADDRESS_PART_SIZE = 16

ADDRESS_PREFIX = 'exchanges'

LOGGER = logging.getLogger(__name__)

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


def _do_event_initiate(args):
    """Executes the 'event initiate' subcommand.  Given a signing private key file, an
    assignment public key file, and a quantity, it generates batches of hashblock_events
    transactions in a BatchList instance.  The BatchList is either stored to a
    file or submitted to a validator, depending on the supplied CLI arguments.
    """
    raw_quantity = []
    ast = parser.parse(args.quantity)
    if ast[0].lower() != 'event_quantity':
        raise AssertionError('Invalid quantity specification.')
    else:
        quantity = ast[1]
        if quantity[0].lower() != 'quantity':
            raise AssertionError('Invalid quantity specification.')
        else:
            term_binary = quantity[1]
            if term_binary[0].lower() != 'term_binary' and term_binary[1].lower() != '.':
                raise AssertionError('Invalid quantity specification.')
            else:
                term = term_binary[2]
                if term[0].lower() != 'term':
                    raise AssertionError('Invalid quantity specification.')
                else:
                    component_unary = term[1]
                    if component_unary[0].lower() != 'component_unary':
                        raise AssertionError('Invalid quantity specification.')
                    else:
                        factor = component_unary[1]
                        if factor[0].lower() != 'factor':
                            raise AssertionError('Invalid quantity specification.')
                        else:
                            raw_quantity.append(factor[1])

                component_binary = term_binary[3]
                if component_binary[0].lower() != 'component_binary':
                    raise AssertionError('Invalid quantity specification.')
                else:
                    annotatable = component_binary[1]
                    resource_unit = component_binary[2]
                    if annotatable[0].lower() != 'annotatable':
                        raise AssertionError('Invalid quantity specification.')
                    else:
                        simple_unit = annotatable[1]
                        if simple_unit[0].lower() != 'simple_unit':
                            raise AssertionError('Invalid quantity specification.')
                        else:
                            value_unit = simple_unit[1]
                            raw_quantity.append(hash_lookup[value_unit])
                            raw_quantity.append(hash_lookup[resource_unit])             

    signer = _read_signer(args.key)
    txns = [_create_initiate_txn(signer, raw_quantity)]

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


def _do_event_list(args):
    """Executes the 'events list' subcommand.

    Given a url, optional filters on prefix, this command lists
    the current unmatched initate events.
    """
    unmatched_event_list = _get_unmatched_event_list(RestClient(args.url))

    if args.format == 'default':
        for unmatched_event in unmatched_event_list:
            value_magnitude = int.from_bytes(unmatched_event.value, byteorder='little')
            value_units = _hash_reverse_lookup(int.from_bytes(unmatched_event.valueUnit, byteorder='little'))
            value_unit = value_units[0]
            if value_magnitude > 1 and value_unit.endswith('s') == False:
                value_unit = value_units[1]
            resource_units = _hash_reverse_lookup(int.from_bytes(unmatched_event.resourceUnit, byteorder='little'))
            resource_unit = resource_units[0]
            print('{} => {}.{}{}'.format(
                unmatched_event.event_id,
                value_magnitude,
                value_unit,
                resource_unit))
    elif args.format == 'csv':
        writer = csv.writer(sys.stdout, quoting=csv.QUOTE_ALL)
        writer.writerow(['ADDESS', 'VALUE', 'VALUEUNIT', 'RESOURCEUNIT'])
        for unmatched_event in unmatched_event_list:
            writer.writerow([
                unmatched_event.event_id,
                int.from_bytes(unmatched_event.value, byteorder='little'),
               int.from_bytes(unmatched_event.valueUnit, byteorder='little'),
                int.from_bytes(unmatched_event.resourceUnit, byteorder='little')])
    elif args.format == 'json' or args.format == 'yaml':
        unmatched_event_snapshot = \
            {e.event_id: {int.from_bytes(e.value, byteorder='little'),
                    int.from_bytes(e.valueUnit, byteorder='little'), 
                    int.from_bytes(e.resourceUnit, byteorder='little') }
             for e in unmatched_event_list}

        if args.format == 'json':
            print(json.dumps(unmatched_event_snapshot, indent=2, sort_keys=True))
        else:
            print(yaml.dump(unmatched_event_snapshot,
                            default_flow_style=False)[0:-1])
    else:
        raise AssertionError('Unknown format {}'.format(args.format))


def _hash_reverse_lookup(lookup_value):
    """Reverse hash lookup
    """
    return [key for key, value in hash_lookup.items() if value == lookup_value]

def _do_event_reciprocate(args):
    """Executes the 'event reciprocate' subcommand.  Given a key file, an event
    id, a quantity, and a ratop, it generates a batch of hashblock_events transactions
    in a BatchList instance.  The BatchList is file or submitted to a
    validator.
    """
    signer = _read_signer(args.key)
    rest_client = RestClient(args.url)

    unmatched_events = _get_unmatched_event_list(rest_client)

    initiate_event_id = None
    for unmatched_event in unmatched_events:
        if unmatched_event.event_id == args.event_id:
            initiate_event_id = unmatched_event
            break

    if initiate_event_id is None:
        raise CliException('No unmatched initiating event exists with the given id:{}'.format(args.event_id))

    quantities = args.quantities

    if quantities[1] != '@' and quantities[3].lower() != 'for':
        raise AssertionError('Invalid specification.')

    r_quantity = Quantity()
    event_quantity = parser.parse(quantities[0])
    if event_quantity[0].lower() != 'event_quantity':
        raise AssertionError('Invalid quantity specification.')
    else:
        quantity_prefix = event_quantity[1]
        if quantity_prefix[0].lower() != 'quantity_prefix':
            raise AssertionError('Invalid quantity specification.')
        else:
            value_unit = quantity_prefix[1]
            term = quantity_prefix[2]
            if term[0].lower() != 'term':
                raise AssertionError('Invalid quantity specification.')
            else:
                component_unary = term[1]
                if component_unary[0].lower() != 'component_unary':
                    raise AssertionError('Invalid quantity specification.')
                else:
                    factor_annotation = component_unary[1]
                    if factor_annotation[0].lower() != 'factor_annotation':
                        raise AssertionError('Invalid quantity specification.')
                    else:
                        r_quantity.value=(int(factor_annotation[1])).to_bytes(2, byteorder='little')
                        r_quantity.valueUnit=(int(hash_lookup[value_unit])).to_bytes(2, byteorder='little')
                        r_quantity.resourceUnit=(int(hash_lookup[factor_annotation[2]])).to_bytes(2, byteorder='little')

    numerator = Quantity()
    event_quantity = parser.parse(quantities[2])
    if event_quantity[0].lower() != 'event_quantity':
        raise AssertionError('Invalid quantity specification.')
    else:
        quantity_prefix = event_quantity[1]
        if quantity_prefix[0].lower() != 'quantity_prefix':
            raise AssertionError('Invalid quantity specification.')
        else:
            value_unit = quantity_prefix[1]
            term = quantity_prefix[2]
            if term[0].lower() != 'term':
                raise AssertionError('Invalid quantity specification.')
            else:
                component_unary = term[1]
                if component_unary[0].lower() != 'component_unary':
                    raise AssertionError('Invalid quantity specification.')
                else:
                    factor_annotation = component_unary[1]
                    if factor_annotation[0].lower() != 'factor_annotation':
                        raise AssertionError('Invalid quantity specification.')
                    else:
                        numerator.value=(int(factor_annotation[1])).to_bytes(2, byteorder='little')
                        numerator.valueUnit=(int(hash_lookup[value_unit])).to_bytes(2, byteorder='little')
                        numerator.resourceUnit=(int(hash_lookup[factor_annotation[2]])).to_bytes(2, byteorder='little')

    denominator = Quantity()
    event_quantity = parser.parse(quantities[4])
    if event_quantity[0].lower() != 'event_quantity':
        raise AssertionError('Invalid quantity specification.')
    else:
        quantity = event_quantity[1]
        if quantity[0].lower() != 'quantity':
            raise AssertionError('Invalid quantity specification.')
        else:
            term_binary = quantity[1]
            if term_binary[0].lower() != 'term_binary' and term_binary[1].lower() != '.':
                raise AssertionError('Invalid quantity specification.')
            else:
                term = term_binary[2]
                if term[0].lower() != 'term':
                    raise AssertionError('Invalid quantity specification.')
                else:
                    component_unary = term[1]
                    if component_unary[0].lower() != 'component_unary':
                        raise AssertionError('Invalid quantity specification.')
                    else:
                        factor = component_unary[1]
                        if factor[0].lower() != 'factor':
                            raise AssertionError('Invalid quantity specification.')
                        else:
                            denominator.value=(int(factor[1])).to_bytes(2, byteorder='little')

                component_binary = term_binary[3]
                if component_binary[0].lower() != 'component_binary':
                    raise AssertionError('Invalid quantity specification.')
                else:
                    annotatable = component_binary[1]
                    resource_unit = component_binary[2]
                    if annotatable[0].lower() != 'annotatable':
                        raise AssertionError('Invalid quantity specification.')
                    else:
                        simple_unit = annotatable[1]
                        if simple_unit[0].lower() != 'simple_unit':
                            raise AssertionError('Invalid quantity specification.')
                        else:
                            value_unit = simple_unit[1]
                            denominator.valueUnit=(int(hash_lookup[value_unit])).to_bytes(2, byteorder='little')
                            denominator.resourceUnit=(int(hash_lookup[resource_unit])).to_bytes(2, byteorder='little')

    ratio=Ratio(numerator=numerator, denominator=denominator)

    txn = _create_reciprocate_txn(
        signer,
        args.event_id,
        r_quantity,
        ratio)
    batch = _create_batch(signer, [txn])

    batch_list = BatchList(batches=[batch])

    rest_client.send_batches(batch_list)


def _create_reciprocate_txn(signer, event_id, quantity, ratio):
    """Creates an individual hashblock_units transaction for creating
    a reciprocate event that matches with an initate event.
    """
    reciprocate_event = MTXQ(
        plus=b'public key',
        minus=b'minus',
        ratio=ratio,
        quantity=quantity)
    # initiate_event_id=event_id)
    event_key = make_events_address(RECIPROCATE_EVENT_KEY, str(uuid.uuid4()))
    input_keys = [event_id]
    output_keys = [event_key, event_id]
    payload = TransactionPayload(data=reciprocate_event.SerializeToString(),
                           ukey=event_id,
                           mkey=event_key,
                           action=TransactionPayload.RECIPROCATE_EVENT)

    return _make_txn(signer, input_keys, output_keys, payload)


def _get_unmatched_event_list(rest_client):
    state_leaf = rest_client.list_state(INITIATE_LIST_ADDRESS)
    unmatched_events = []

    if state_leaf is not None:
        initiate_event_bytes = None
        for event_state_leaf in state_leaf['data']:
            if event_state_leaf is not None:
                initiate_event_bytes = b64decode(event_state_leaf['data'])
                if initiate_event_bytes is not None:
                    initiate_event = UTXQ()
                    initiate_event.ParseFromString(initiate_event_bytes)
                    if initiate_event.matched == False:
                        unmatched_event = UnmatchedEvent()
                        unmatched_event.event_id = event_state_leaf['address']
                        unmatched_event.value = initiate_event.quantity.value
                        unmatched_event.valueUnit = initiate_event.quantity.valueUnit
                        unmatched_event.resourceUnit = initiate_event.quantity.resourceUnit
                        unmatched_events.append(unmatched_event)

    return unmatched_events


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


def _read_key(key_filename):
    """Reads the given file as a hex key.

    Args:
        key_filename: The filename where the key is stored. If None,
            defaults to the default key for the current user.

    Returns:
        Key: the public key

    Raises:
        CliException: If unable to read the file.
    """
    filename = key_filename
    if filename is None:
        filename = os.path.join(os.path.expanduser('~'),
                                '.sawtooth',
                                'keys',
                                getpass.getuser() + '.pub')

    try:
        with open(filename, 'r') as key_file:
            public_key = key_file.read().strip()
    except IOError as e:
        raise CliException('Unable to read key file: {}'.format(str(e)))

    return public_key


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


def _create_initiate_txn(signer, quantity_value_unit_resource):
    """Creates an individual hashblock_events transaction for the given key and
    value.quantity_value_unit_resource
    """
    value, unit, resource = quantity_value_unit_resource
    quantity = Quantity(
        value=(int(value)).to_bytes(2, byteorder='little'),
        valueUnit=(int(unit)).to_bytes(2, byteorder='little'),
        resourceUnit=(int(resource)).to_bytes(2, byteorder='little'))
    initiateEvent = UTXQ(
        reciprocated=False,
        plus=b'public key',
        minus=b'minus_public_key',
        quantity=quantity)
    event_key = make_events_address(INITIATE_EVENT_KEY, str(uuid.uuid4()))
    output_keys = [event_key]
    payload = TransactionPayload(data=initiateEvent.SerializeToString(),
                           ikey=event_key,
                           action=TransactionPayload.INITIATE_EVENT)
    return _make_txn(signer, [], output_keys, payload)


def _make_txn(signer, input_keys, output_keys, payload):
    """Creates and signs a hashblock_events transaction with with a payload.
    """
    serialized_payload = payload.SerializeToString()
    header = TransactionHeader(
        signer_public_key=signer.get_public_key().as_hex(),
        family_name='hashblock_events',
        family_version='0.1.0',
        inputs=input_keys,
        outputs=output_keys,
        dependencies=[],
        payload_sha512=hashlib.sha512(serialized_payload).hexdigest(),
        batcher_public_key=signer.get_public_key().as_hex()
    ).SerializeToString()

    return Transaction(
        header=header,
        header_signature=signer.sign(header),
        payload=serialized_payload)


def _to_hash(value):
    return hashlib.sha256(value.encode()).hexdigest()


_EMPTY_PART = _to_hash('')[:_ADDRESS_PART_SIZE]
EVENTS_ADDRESS_PREFIX = hashlib.sha512(
    ADDRESS_PREFIX.encode('utf-8')).hexdigest()[0:6]


def make_events_address(sublist, data):
    return EVENTS_ADDRESS_PREFIX + \
        hashlib.sha512(sublist.encode('utf-8')).hexdigest()[0:6] + \
        hashlib.sha512(data.encode('utf-8')).hexdigest()[-58:]


def _make_events_key(key):
    print("Making events key from {}".format(key))
    # split the key into 4 parts, maximum
    key_parts = key.split('.', maxsplit=_MAX_KEY_PARTS - 1)
    # compute the short hash of each part
    addr_parts = [_to_hash(x)[:_ADDRESS_PART_SIZE] for x in key_parts]
    # pad the parts with the empty hash, if needed
    addr_parts.extend([_EMPTY_PART] * (_MAX_KEY_PARTS - len(addr_parts)))
    return make_events_address(addr_parts[0], ''.join(addr_parts[0:3]))


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
        description='Provides subcommands to '
        'to list unmatched initating events, to create initiating '
        'events, and to create reciprocating events.',
        parents=[parent_parser])

    subparsers = parser.add_subparsers(title='subcommands', dest='subcommand')
    subparsers.required = True

    # The following parser is for the `event` subcommand group. These
    # commands allow the user to create initiating events.

    event_parser = subparsers.add_parser(
        'event',
        help='Lists unmatched initiating events, creates initating events, '
        'or creates reciprocating events',
        description='Provides subcommands to ist unmatched initiating events, '
        ' to creates initating events, and to create reciprocating events')
    event_parsers = event_parser.add_subparsers(
        title='subcommands',
        dest='event_cmd')
    event_parsers.required = True

    initiate_parser = event_parsers.add_parser(
        'initiate',
        help='Creates initiating event',
        description='Create initiating event.'
    )

    initiate_parser.add_argument(
        '-k', '--key',
        type=str,
        help='specify a private signing key for the resulting batches, '
        'and the plus public key assignment.')

    initiate_parser.add_argument(
        '-m', '--minus',
        type=str,
        help='specify the minus public key assignment.')

    prop_target_group = initiate_parser.add_mutually_exclusive_group()
    prop_target_group.add_argument(
        '-o', '--output',
        type=str,
        help='specify the output file for the resulting batches')

    prop_target_group.add_argument(
        '--url',
        type=str,
        help="identify the URL of a validator's REST API",
        default='http://rest-api:8008')

    initiate_parser.add_argument(
        'quantity',
        type=str,
        help='Quantity with the '
        'format <value>.<value_unit> {resource_unit}.')

    event_list_parser = event_parsers.add_parser(
        'list',
        help='Lists the unmatched initiating events',
        description='Lists the initiating events. '
                    'Use this list of initiating events to '
                    'match with reciprocating events.')

    event_list_parser.add_argument(
        '--url',
        type=str,
        help="identify the URL of a validator's REST API",
        default='http://rest-api:8008')

    event_list_parser.add_argument(
        '--public-key',
        type=str,
        default='',
        help='filter proposals from a particular public key')

    event_list_parser.add_argument(
        '--filter',
        type=str,
        default='',
        help='filter codes that begin with this value')

    event_list_parser.add_argument(
        '--format',
        default='default',
        choices=['default', 'csv', 'json', 'yaml'],
        help='choose the output format')

    reciprocate_parser = event_parsers.add_parser(
        'reciprocate',
        help='Create reciprocating events',
        description='Create reciprocating events that  that match '
        'with initiating events. Use "eventsset event list" to '
        'find the initiating event id.')

    reciprocate_parser.add_argument(
        '--url',
        type=str,
        help="identify the URL of a validator's REST API",
        default='http://rest-api:8008')

    reciprocate_parser.add_argument(
        '-k', '--key',
        type=str,
        help='specify a signing private key for the resulting transaction batch, '
        'and the resource increment assignment\'s public key')

    reciprocate_parser.add_argument(
        'event_id',
        type=str,
        help='identify the initiating event to match')

    reciprocate_parser.add_argument(
        'quantities',
        type=str,
        nargs='+',
        help='Reciprocating event as quantity and quantity ratio with the '
        'format <value_symbol><value>{<resource_unit>} @ '
        '<value_symbol><value>{<resource_unit>} for '
        '<value>.<value_unit>{<resource_unit>}.')

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

    if args.subcommand == 'event' and args.event_cmd == 'initiate':
        _do_event_initiate(args)
    elif args.subcommand == 'event' and args.event_cmd == 'list':
        _do_event_list(args)
    elif args.subcommand == 'event' and args.event_cmd == 'reciprocate':
        _do_event_reciprocate(args)
    else:
        raise CliException(
            '"{}" is not a valid subcommand of "event"'.format(
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

