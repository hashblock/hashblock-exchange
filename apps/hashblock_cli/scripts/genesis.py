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

from sawtooth_sdk.protobuf.genesis_pb2 import GenesisData

from scripts.hbsawset import gensawset
from scripts.ucum_to_assets import genucum
from scripts.iso4217_to_assets import geniso4217
from modules.exceptions import CliException
from shared.setting import create_settings_genesis
from shared.asset import create_unit_genesis, create_asset_genesis
from shared.transactions import create_batch, create_batch_list


def add_genesis_parser(subparsers, parent_parser):
    parser = subparsers.add_parser(
        'genesis',
        help='Creates hashblock-exchange genesis block',
        description='Generates the file genesis.batch used '
        'in the genesis block with initial hashblock-settings '
        'and hashblock-assets.',
        epilog='The file will be saved in the configuration path '
        'as set in the HASHBLOCK_CONFIG environment variable or passed in '
        'by the -o argument. '
        'Defaults to /project/hashblock-exchange/localconfig/genesis.batch.',
        parents=[parent_parser])

    parser.add_argument(
        '-k',
        help='Signing key for genesis transactions',
        dest='signer',
        default='turing')

    parser.add_argument(
        '-rk',
        help='specify the keys for proposing/voting on resources',
        dest='resource_keys',
        default=['turing', 'church'],
        nargs='+')

    parser.add_argument(
        '-rt',
        dest='resource_threshold',
        help='specify the resource voting threshold',
        default="2")

    parser.add_argument(
        '-uk',
        help='specify the keys for proposing/voting on units-of-measure',
        dest='unit_keys',
        default=['turing', 'church'],
        nargs='+')

    parser.add_argument(
        '-ut',
        dest='unit_threshold',
        help='specify the units-of-measure voting threshold',
        default="2")

    parser.add_argument(
        '-o',
        dest='output',
        help="specify the directory for the genesis.batch file")

    parser.add_argument(
        '--force',
        help="overwrite file if it exists",
        action='store_true')

    parser.add_argument(
        '-q',
        '--quiet',
        help="do not display output",
        action='store_true')


def do_genesis(args, config):
    """Generate the genesis batch file"""
    if not args.output:
        raise CliException('genesis creation requires output file')

    std_units = genucum()
    iso4217_assets = geniso4217()

    txns = gensawset(args.signer)

    txns.extend(create_settings_genesis(
        args.signer, args.resource_keys, args.resource_threshold,
        args.unit_keys, args.unit_threshold))

    txns.extend(create_unit_genesis(args.signer, std_units))
    txns.extend(create_asset_genesis(args.signer, iso4217_assets))

    # # Combine setting txns with assets txns in batchlist

    output_data = GenesisData(batches=[create_batch((args.signer, txns))])
    # batch = create_batch_list([create_batch((args.signer, txns))])
    # output_data = GenesisData(batches=[batch])

    if args.output:
        try:
            with open(args.output, 'wb') as batch_file:
                batch_file.write(output_data.SerializeToString())
                # batch_file.write(batch.SerializeToString())
            print('Generated {}'.format(args.output))
        except IOError as e:
            raise CliException(
                'Unable to write to batch file: {}'.format(str(e)))
