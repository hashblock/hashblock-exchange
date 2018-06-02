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
from shared.setting import create_settings_batch, create_settings_submit


def add_genesis_parser(subparsers, parent_parser):
    parser = subparsers.add_parser(
        'genesis',
        help='Creates hashblock-exchange genesis block',
        description='Generates the file genesis.batch used '
        'in the genesis block with initial hashblock-settings transactions.',
        epilog='The file will be saved in the configuration path '
        'as set in the HASHBLOCK_CONFIG environment variable or passed in '
        'by the -o argument. '
        'Defaults to /project/hashblock-exchange/localconfig/genesis.batch.',
        parents=[parent_parser])

    parser.add_argument(
        '-k',
        help='Signing key for genesis transactions',
        dest='signer',
        required=True)

    parser.add_argument(
        '-rk',
        help='specify the keys for proposing/voting on resources',
        dest='resource_keys',
        nargs='+')

    parser.add_argument(
        '-rt',
        dest='resource_threshold',
        help='specify the resource voting threshold')

    parser.add_argument(
        '-uk',
        help='specify the keys for proposing/voting on units-of-measure',
        dest='unit_keys',
        nargs='+')

    parser.add_argument(
        '-ut',
        dest='unit_threshold',
        help='specify the units-of-measure voting threshold')

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

    results = create_settings_batch(
        args.signer, args.resource_keys, args.resource_threshold,
        args.unit_keys, args.unit_threshold)

    if args.output:
        try:
            with open(args.output, 'wb') as batch_file:
                batch_file.write(results.SerializeToString())
            print('Generated {}'.format(args.output))
        except IOError as e:
            raise CliException(
                'Unable to write to batch file: {}'.format(str(e)))
    else:
        print('Submitted {}'.format(results))
