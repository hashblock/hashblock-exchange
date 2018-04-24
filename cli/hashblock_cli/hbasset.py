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
    """Parses command line arguments into an asset object
    """
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

    type_map, asset = _do_create_asset(type_map)
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
        rest_client.send_batches(batch_list)
    else:
        raise AssertionError('No target for create set.')


# bin/hbasset proposal create \
# -k /root/.sawtooth/keys/my_key.priv \
# asset='unit' system='imperial' key='unity' value='1'

def _do_config_proposal_list(args):
    """Executes the 'proposal list' subcommand.

    Given a url, optional filters on prefix and public key, this command lists
    the current pending proposals for resource changes.
    """

    def _accept(candidate, public_key):
        # Check to see if the first public key matches the given public key
        # (if it is not None).  This public key belongs to the user that
        # created it.
        return (not public_key or
                candidate.votes[0].public_key == public_key)

    rclient = RestClient(args.url)

    if args.unit:
        candidates_payload = [_get_proposals(rclient, Address.DIMENSION_UNIT)]
    elif args.resource:
        candidates_payload = [
            _get_proposals(rclient, Address.DIMENSION_RESOURCE)]
    elif args.all:
        candidates_payload = _get_all_proposals(rclient)
    else:
        raise AssertionError(
            'Dimension must be one of {-a[ll] -u[nit], -r[esource]}')

    candidates = [
        item for sublist in candidates_payload
        for item in sublist.candidates
        if _accept(item, args.public_key)]

    if args.format == 'default':
        for candidate in candidates:
            if candidate.proposal.type == AssetProposal.UNIT:
                proposal_asset = Unit()
                proposal_asset.ParseFromString(candidate.proposal.asset)
                print("UNIT {}: system '{}' key '{}' => value '{}'".format(
                    candidate.proposal_id,
                    proposal_asset.system,
                    proposal_asset.key,
                    proposal_asset.value))
            else:
                proposal_asset = Resource()
                proposal_asset.ParseFromString(candidate.proposal.asset)
                print(
                    "RESOURCE {}: system '{}' key '{}' => value '{}' sku '{}'".
                    format(
                        candidate.proposal_id,
                        proposal_asset.system,
                        proposal_asset.key,
                        proposal_asset.value,
                        proposal_asset.sku))
            for vote in candidate.votes:
                print("     voter {} => {}".format(
                    vote.public_key,
                    "accept" if vote.vote is AssetVote.ACCEPT else "reject"))
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
    id and a vote value, generate a batch of hashblock_asset transactions
    in a BatchList instance.  The BatchList is saved to a file or
    submitted to a validator.
    """
    signer = _read_signer(args.key)
    rest_client = RestClient(args.url)

    if args.unit:
        dimension = Address.DIMENSION_UNIT
    elif args.resource:
        dimension = Address.DIMENSION_RESOURCE
    else:
        raise AssertionError('Dimension must be one of {-u[nit], -r[esource]}')

    proposals = _get_proposals(rest_client, dimension)

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

    print("Proposing to vote")

    txn = _create_vote_txn(
        signer,
        args.proposal_id,
        dimension,
        args.vote_value)
    batch = _create_batch(signer, [txn])

    batch_list = BatchList(batches=[batch])

    x = rest_client.send_batches(batch_list)


def _do_config_unset_vote(args):
    """Executes the 'unset vote' subcommand.  Given a key file, a proposal
    id and a vote value, generate a batch of hashblock_asset transactions
    in a BatchList instance.  The BatchList is saved to a file or
    submitted to a validator.
    """
    signer = _read_signer(args.key)
    rest_client = RestClient(args.url)

    if args.unit:
        dimension = Address.DIMENSION_UNIT
    elif args.resource:
        dimension = Address.DIMENSION_RESOURCE
    else:
        raise AssertionError('Dimension must be one of {-u[nit], -r[esource]}')

    proposals = _get_proposals(rest_client, dimension)

    proposal = None
    for candidate in proposals.candidates:
        if candidate.proposal_id == args.proposal_id:
            proposal = candidate
            break

    spubkey = signer.get_public_key().as_hex()
    if proposal is None:
        raise CliException('No proposal exists with the given id')

    voter = None
    for vote_record in proposal.votes:
        if vote_record.public_key == spubkey:
            voter = vote_record
            break

    if not voter:
        raise CliException(
            'There is no vote made by user key {}'.format(
                signer.get_public_key().as_hex()))

    print("Proposing to rescind vote")

    txn = _create_vote_txn(
        signer,
        args.proposal_id,
        dimension,
        'rescind')
    batch = _create_batch(signer, [txn])

    batch_list = BatchList(batches=[batch])

    x = rest_client.send_batches(batch_list)
    print("Transaction submitted")


def _get_all_proposals(rest_client):
    """Return a list of proposals for all dimensions {unit, resource}"""
    candidates_list = []
    state_leaf = rest_client.list_state(_addresser.candidates_base)
    if state_leaf:
        for x in state_leaf['data']:
            candidate_bytes = b64decode(x['data'])
            if candidate_bytes is not None:
                candidate = AssetCandidates()
                candidate.ParseFromString(candidate_bytes)
                candidates_list.append(candidate)
    return candidates_list


def _get_proposals(rest_client, dimension):
    """Returns proposals for a specific dimension {unit, resource}"""
    state_leaf = rest_client.get_leaf(_addresser.candidates(dimension))
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

    return _make_txn(signer, dimension, asset_addr, payload)


def _create_vote_txn(signer, proposal_id, dimension, vote_value):
    """Creates an individual hashblock_resource transaction for voting on a
    proposal for a particular asset. The proposal_id is the asset address
    """
    vote_action = AssetPayload.VOTE

    if vote_value == 'accept':
        vote_id = AssetVote.ACCEPT
    elif vote_value == 'reject':
        vote_id = AssetVote.REJECT
    elif vote_value == 'rescind':
        vote_id = AssetVote.VOTE_UNSET
        vote_action = AssetPayload.ACTION_UNSET

    vote = AssetVote(
        proposal_id=proposal_id,
        vote=vote_id)
    payload = AssetPayload(
        data=vote.SerializeToString(),
        dimension=dimension,
        action=vote_action)

    return _make_txn(signer, dimension, proposal_id, payload)


def _make_txn(signer, dimension, asset_addr, payload):
    """Creates and signs a hashblock_asset transaction with with a payload.
    """
    serialized_payload = payload.SerializeToString()
    header = TransactionHeader(
        nonce=str(datetime.datetime.utcnow().timestamp()),
        signer_public_key=signer.get_public_key().as_hex(),
        family_name=Address.NAMESPACE_ASSET,
        family_version='0.1.0',
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
        version=(DISTRIBUTION_NAME + ' (Hashblock Asset Utility) version {}')
        .format(version),
        help='display version information')

    return parent_parser


def create_parser(prog_name):
    parent_parser = create_parent_parser(prog_name)

    parser = argparse.ArgumentParser(
        description='Provides subcommands to '
        'view, create, and vote on asset proposals.',
        parents=[parent_parser])

    subparsers = parser.add_subparsers(title='subcommands', dest='subcommand')
    subparsers.required = True

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

    proposal_list_type_group = \
        proposal_list_parser.add_mutually_exclusive_group(required=True)

    proposal_list_type_group.add_argument(
        '-unit',
        action='store_true',
        help='list outstanding unit proposals')

    proposal_list_type_group.add_argument(
        '-resource',
        action='store_true',
        help='list outstanding resource proposals')

    proposal_list_type_group.add_argument(
        '-all',
        action='store_true',
        help='list all outstanding proposals')

    proposal_list_parser.add_argument(
        '-fk', '--filter-key',
        type=str,
        default='',
        help='filter assets by key')

    proposal_list_parser.add_argument(
        '-fs', '--filter-system',
        type=str,
        default='',
        help='filter assets by system')

    proposal_list_parser.add_argument(
        '--format',
        default='default',
        choices=['default', 'csv', 'json', 'yaml'],
        help='choose the output format')

    vote_parser = proposal_parsers.add_parser(
        'vote',
        help='Votes for specific unit change proposals',
        description='Votes for a specific resource change proposal. Use '
                    '"hbasset proposal list" to find the proposal id.')

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

    vote_type_group = \
        vote_parser.add_mutually_exclusive_group(required=True)

    vote_type_group.add_argument(
        '-unit',
        action='store_true',
        help='list outstanding unit proposals')

    vote_type_group.add_argument(
        '-resource',
        action='store_true',
        help='list outstanding resource proposals')

    vote_parser.add_argument(
        'vote_value',
        type=str,
        choices=['accept', 'reject', 'rescind'],
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
        if args.vote_value == 'rescind':
            _do_config_unset_vote(args)
        else:
            _do_config_proposal_vote(args)
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
