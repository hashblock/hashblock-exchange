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

from hashblock_cli.protobuf.asset_pb2 import AssetPayload
from hashblock_cli.protobuf.asset_pb2 import AssetProposal
from hashblock_cli.protobuf.asset_pb2 import AssetVote
from hashblock_cli.protobuf.asset_pb2 import AssetCandidates
from hashblock_cli.protobuf.asset_pb2 import Resource
from hashblock_cli.protobuf.asset_pb2 import Unit
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

DISTRIBUTION_NAME = 'hbasset'

_addresser = Address(Address.FAMILY_ASSET)

FAMILY_NAME = 'hashblock_asset'
RESOURCE_NAMESPACE = hashlib.sha512(
    FAMILY_NAME.encode("utf-8")).hexdigest()[0:6]

_MIN_PRINT_WIDTH = 15
_MAX_KEY_PARTS = 4
_ADDRESS_PART_SIZE = 16


def add_config_parser(subparsers, parent_parser):
    """Creates the arg parsers needed for the config command and
    its subcommands.
    """
    parser = subparsers.add_parser(
        'config',
        help='Changes genesis block resource and create, view, and '
        'vote on resource proposals',
        description='Provides subcommands to change genesis block settings '
                    'and to view, create, and vote on existing proposals.'
    )

    config_parsers = parser.add_subparsers(title="subcommands",
                                           dest="subcommand")
    config_parsers.required = True


def _do_create_asset(type_map):

    asset_type = type_map['asset']
    asset_list = ['unit', 'resource']
    if asset_type:
        if asset_type in asset_list:
            if asset_type == 'unit':
                type_map['proposal_type'] = AssetProposal.UNIT
                asset = Unit(
                    system=type_map['system'],
                    key=type_map['key'],
                    value=type_map['value'])
            elif asset_type == 'resource':
                type_map['proposal_type'] = AssetProposal.RESOURCE
                asset = Resource(
                    system=type_map['system'],
                    key=type_map['key'],
                    value=type_map['value'],
                    sku=type_map['sku'])
            else:
                raise AssertionError(
                    'Asset must be one of {}'.format(asset_list))
    else:
        raise AssertionError('Unknown format {}'.format(args.format))

    return(type_map, asset)


def _do_config_proposal_create(args):
    """Executes the 'proposal create' subcommand.  Given a key file, and a
    series of code/value pairs, it generates batches of hashblock_resource
    transactions in a BatchList instance.  The BatchList is either stored to a
    file or submitted to a validator, depending on the supplied CLI arguments.
    """

    type_map = dict()
    for s in args.asset:
        keypair = s.split('=', 1)
        type_map[keypair[0]] = keypair[1]
    # resources = [s.split('=', 1) for s in args.resource]
    type_map, asset = _do_create_asset(type_map)
    print("Asset = {} from {}".format(asset, type_map))
    signer = _read_signer(args.key)

    txn = [_create_propose_txn(
        signer,
        asset,
        type_map['asset'],
        _addresser.asset_item(
            type_map['asset'],
            type_map['system'],
            type_map['key']),
        type_map['proposal_type'])]
    # txns = [_create_propose_txn(signer, resource)
    #         for resource in resources]

    batch = _create_batch(signer, txn)

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
        x = rest_client.send_batches(batch_list)
        print("Rest returns {}".format(x))
    else:
        raise AssertionError('No target for create set.')


def _do_config_proposal_list(args):
    """Executes the 'proposal list' subcommand.

    Given a url, optional filters on prefix and public key, this command lists
    the current pending proposals for resource changes.
    """

    def _accept(candidate, public_key, prefix):
        # Check to see if the first public key matches the given public key
        # (if it is not None).  This public key belongs to the user that
        # created it.
        has_pub_key = (not public_key or
                    candidate.votes[0].public_key == public_key)
        return has_pub_key

    if args.filter == 'unit':
        dimension = Address.DIMENSION_UNIT
    elif args.filter == 'resource':
        dimension = Address.DIMENSION_RESOURCE
    else:
        raise AssertionError('Arg filter must be one of {unit, resource')

    candidates_payload = _get_proposals(RestClient(args.url), dimension)
    candidates = [
        c for c in candidates_payload.candidates
        if _accept(c, args.public_key, args.filter)
    ]

    if args.format == 'default':
        for candidate in candidates:
            if candidate.proposal.type == AssetProposal.UNIT:
                proposal_asset = Unit()
                proposal_asset.ParseFromString(candidate.proposal.asset)
                print("{}: system '{}' key '{}' => value '{}'".format(
                    candidate.proposal_id,
                    proposal_asset.system,
                    proposal_asset.key,
                    proposal_asset.value))
            else:
                proposal_asset = Resource()
                proposal_asset.ParseFromString(candidate.proposal.asset)
                print("{}: system '{}' key '{}' => value '{}' sku '{}'".format(
                    candidate.proposal_id,
                    proposal_asset.system,
                    proposal_asset.key,
                    proposal_asset.value,
                    proposal_asset.sku))

            # candidate.proposal.asset.sku))
    elif args.format == 'csv':
        writer = csv.writer(sys.stdout, quoting=csv.QUOTE_ALL)
        writer.writerow(['PROPOSAL_ID', 'SYSTEM', 'KEY', 'VALUE', 'SKU'])
        for candidate in candidates:
            writer.writerow([
                candidate.proposal.asset.system,
                candidate.proposal.asset.key,
                candidate.proposal.asset.value,
                candidate.proposal.asset.sku])
    elif args.format == 'json' or args.format == 'yaml':
        candidates_snapshot = \
            {c.proposal_id: {c.proposal.asset.key: c.proposal.asset.value}
             for c in candidates}

        if args.format == 'json':
            print(json.dumps(candidates_snapshot, indent=2, sort_keys=True))
        else:
            print(yaml.dump(candidates_snapshot,
                            default_flow_style=False)[0:-1])
    else:
        raise AssertionError('Unknown format {}'.format(args.format))


def _do_config_proposal_vote(args):
    """Executes the 'proposal vote' subcommand.  Given a key file, a proposal
    id and a vote value, it generates a batch of hashblock_resource transactions
    in a BatchList instance.  The BatchList is file or submitted to a
    validator.
    """
    signer = _read_signer(args.key)
    rest_client = RestClient(args.url)

    proposals = _get_proposals(rest_client, Address.DIMENSION_RESOURCE)

    proposal = None
    for candidate in proposals.candidates:
        if candidate.proposal_id == args.proposal_id:
            proposal = candidate
            break

    if proposal is None:
        raise CliException('No proposal exists with the given id')

    for vote_record in proposal.votes:
        if vote_record.public_key == signer.get_public_key().as_hex():
            raise CliException(
                'A vote has already been recorded with this signing key')

    txn = _create_vote_txn(
        signer,
        args.proposal_id,
        proposal.proposal.code,
        args.vote_value)
    batch = _create_batch(signer, [txn])

    batch_list = BatchList(batches=[batch])

    rest_client.send_batches(batch_list)


def _do_config_genesis(args):
    signer = _read_signer(args.key)
    public_key = signer.get_public_key().as_hex()

    authorized_keys = args.authorized_key if args.authorized_key else \
        [public_key]
    if public_key not in authorized_keys:
        authorized_keys.append(public_key)

    txns = []

    txns.append(_create_propose_txn(
        signer,
        ('hashblock.setting.resource.authorized_keys',
         ','.join(authorized_keys))))

    if args.approval_threshold is not None:
        if args.approval_threshold < 1:
            raise CliException('approval threshold must not be less than 1')

        if args.approval_threshold > len(authorized_keys):
            raise CliException(
                'approval threshold must not be greater than the number of '
                'authorized keys')

        txns.append(_create_propose_txn(
            signer,
            ('hashblock.setting.resource.approval_threshold',
             str(args.approval_threshold))))

    batch = _create_batch(signer, txns)
    batch_list = BatchList(batches=[batch])

    try:
        with open(args.output, 'wb') as batch_file:
            batch_file.write(batch_list.SerializeToString())
        print('Generated {}'.format(args.output))
    except IOError as e:
        raise CliException(
            'Unable to write to batch file: {}'.format(str(e)))


def _get_proposals(rest_client, asset_str):

    state_leaf = rest_client.get_leaf(_addresser.candidates(asset_str))
    config_candidates = AssetCandidates()
    if state_leaf:
        candidates_bytes = b64decode(state_leaf['data'])
        if candidates_bytes is not None:
            config_candidates.ParseFromString(candidates_bytes)

    return config_candidates


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


def _create_propose_txn(signer, asset, dimension, asset_addr, proposal_type):
    """Creates an individual hashblock_asset transaction for the given key and
    value.
    """

    nonce = str(datetime.datetime.utcnow().timestamp())
    proposal = AssetProposal(
        type=proposal_type,
        asset=asset.SerializeToString(),
        nonce=nonce)

    payload = AssetPayload(
        data=proposal.SerializeToString(),
        dimension=dimension,
        action=AssetPayload.PROPOSE)

    print("Payload = {}".format(payload))
    return _make_txn(signer, dimension, asset_addr, payload)


def _create_vote_txn(signer, proposal_id, resource_key, vote_value):
    """Creates an individual hashblock_resource transaction for voting on a
    proposal for a particular unit key.
    """
    if vote_value == 'accept':
        vote_id = ResourceVote.ACCEPT
    else:
        vote_id = ResourceVote.REJECT

    vote = ResourceVote(proposal_id=proposal_id, vote=vote_id)
    payload = ResourcePayload(data=vote.SerializeToString(),
                              action=ResourcePayload.VOTE)

    return _make_txn(signer, resource_key, payload)


def _make_txn(signer, dimension, asset_addr, payload):
    """Creates and signs a hashblock_asset transaction with with a payload.
    """
    serialized_payload = payload.SerializeToString()
    header = TransactionHeader(
        signer_public_key=signer.get_public_key().as_hex(),
        family_name=Address.NAMESPACE_ASSET,
        family_version='1.0.0',
        inputs=_config_inputs(asset_addr, dimension),
        outputs=_config_outputs(asset_addr, dimension),
        dependencies=[],
        payload_sha512=hashlib.sha512(serialized_payload).hexdigest(),
        batcher_public_key=signer.get_public_key().as_hex()
    ).SerializeToString()

    return Transaction(
        header=header,
        header_signature=signer.sign(header),
        payload=serialized_payload)


def _config_inputs(asset_addr, dimension):
    """Creates the list of inputs for a hashblock_asset transaction, for a
    given unit key.
    """
    return [
        asset_addr,
        _addresser.candidates(dimension),
        Address(Address.FAMILY_SETTING).settings(dimension)
    ]


def _config_outputs(asset_addr, dimension):
    """Creates the list of outputs for a hashblock_resource transaction, for a
    given unit key.
    """
    return [
        asset_addr,
        _addresser.candidates(dimension),
    ]


def _short_hash(in_str):
    return hashlib.sha256(in_str.encode()).hexdigest()[:_ADDRESS_PART_SIZE]


def _key_to_address(key):
    """Creates the state address for a given unit key.
    """
    key_parts = key.split('.', maxsplit=_MAX_KEY_PARTS - 1)
    key_parts.extend([''] * (_MAX_KEY_PARTS - len(key_parts)))

    return RESOURCE_NAMESPACE + ''.join(_short_hash(x) for x in key_parts)


def resource_key_to_address(key):
    return _key_to_address(key)


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
        version=(DISTRIBUTION_NAME + ' (Hashblock Exchange) version {}')
        .format(version),
        help='display version information')

    return parent_parser


def create_parser(prog_name):
    parent_parser = create_parent_parser(prog_name)

    parser = argparse.ArgumentParser(
        description='Provides subcommands to change genesis block resource '
        'and to view, create, and vote on resource proposals.',
        parents=[parent_parser])

    subparsers = parser.add_subparsers(title='subcommands', dest='subcommand')
    subparsers.required = True

    # The following parser is for the `genesis` subcommand.
    # This command creates a batch that contains all of the initial
    # transactions for resource settings
    genesis_parser = subparsers.add_parser(
        'genesis',
        help='Creates a genesis batch file of resource transactions',
        description='Creates a Batch of resource proposals that can be '
                    'consumed by "resourceadm genesis" and used '
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
        default='config-resource.batch',
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

    # The following parser is for the `proposal` subcommand group. These
    # commands allow the user to create proposals which may be applied
    # immediately or placed in ballot mode, depending on the current on-chain
    # resource.

    proposal_parser = subparsers.add_parser(
        'proposal',
        help='Views, creates, or votes on resource change proposals',
        description='Provides subcommands to view, create, or vote on '
                    'proposed asset')
    proposal_parsers = proposal_parser.add_subparsers(
        title='subcommands',
        dest='proposal_cmd')
    proposal_parsers.required = True

    prop_parser = proposal_parsers.add_parser(
        'create',
        help='Creates proposals for asset changes',
        description='Create proposals for resource changes. The change '
                    'may be applied immediately or after a series of votes, '
                    'depending on the vote threshold unit.'
    )

    prop_parser.add_argument(
        '-k', '--key',
        type=str,
        help='specify a signing key for the resulting batches')

    prop_target_group = prop_parser.add_mutually_exclusive_group()
    prop_target_group.add_argument(
        '-o', '--output',
        type=str,
        help='specify the output file for the resulting batches')

    prop_target_group.add_argument(
        '--url',
        type=str,
        help="identify the URL of a validator's REST API",
        default='http://rest-api:8008')

    prop_parser.add_argument(
        'asset',
        type=str,
        nargs='+',
        help="""Asset unit defined as name/value pairs
        Unit Asset pairs: asset=unit system='' key='' value=''
        Resource Asset pairs: asset=resource system='' key='' value='' sku=''""")

    proposal_list_parser = proposal_parsers.add_parser(
        'list',
        help='Lists the currently proposed (not active) assets',
        description='Lists the currently proposed (not active) assets. '
                    'Use this list of proposals to find proposals to '
                    'vote on.')

    proposal_list_parser.add_argument(
        '--url',
        type=str,
        help="identify the URL of a validator's REST API",
        default='http://rest-api:8008')

    proposal_list_parser.add_argument(
        '--public-key',
        type=str,
        default='',
        help='filter proposals from a particular public key')

    proposal_list_parser.add_argument(
        '--filter',
        type=str,
        default='',
        help='filter codes that begin with this value')

    proposal_list_parser.add_argument(
        '--format',
        default='default',
        choices=['default', 'csv', 'json', 'yaml'],
        help='choose the output format')

    vote_parser = proposal_parsers.add_parser(
        'vote',
        help='Votes for specific unit change proposals',
        description='Votes for a specific resource change proposal. Use '
                    '"resourceset proposal list" to find the proposal id.')

    vote_parser.add_argument(
        '--url',
        type=str,
        help="identify the URL of a validator's REST API",
        default='http://rest-api:8008')

    vote_parser.add_argument(
        '-k', '--key',
        type=str,
        help='specify a signing key for the resulting transaction batch')

    vote_parser.add_argument(
        'proposal_id',
        type=str,
        help='identify the proposal to vote on')

    vote_parser.add_argument(
        'vote_value',
        type=str,
        choices=['accept', 'reject'],
        help='specify the value of the vote')

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

    if args.subcommand == 'proposal' and args.proposal_cmd == 'create':
        _do_config_proposal_create(args)
    elif args.subcommand == 'proposal' and args.proposal_cmd == 'list':
        _do_config_proposal_list(args)
    elif args.subcommand == 'proposal' and args.proposal_cmd == 'vote':
        _do_config_proposal_vote(args)
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

