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
        '-rk',
        help='specify the keys for proposing/voting on resources',
        nargs='?')

    parser.add_argument(
        '-rt',
        help='specify the resource voting threshold')

    parser.add_argument(
        '-uk',
        help='specify the keys for proposing/voting on units-of-measure',
        nargs='?')

    parser.add_argument(
        '-ut',
        help='specify the units-of-measure voting threshold')

    parser.add_argument(
        '-o',
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


def do_genesis(args):
    # signer = _read_signer(args.key)
    # public_key = signer.get_public_key().as_hex()

    # authorized_keys = args.authorized_key if args.authorized_key else \
    #     [public_key]
    # if public_key not in authorized_keys:
    #     authorized_keys.append(public_key)

    # txns = []

    # keys = ','.join(authorized_keys)
    # threshold = str(args.approval_threshold)

    # if args.approval_threshold is not None:
    #     if args.approval_threshold < 1:
    #         raise CliException('approval threshold must not be less than 1')

    #     if args.approval_threshold > len(authorized_keys):
    #         raise CliException(
    #             'approval threshold must not be greater than the number of '
    #             'authorized keys')

    # txns.append(_create_setting(
    #     signer,
    #     Address.DIMENSION_UNIT,
    #     SettingPayload.CREATE,
    #     keys, threshold))
    # txns.append(_create_setting(
    #     signer,
    #     Address.DIMENSION_RESOURCE,
    #     SettingPayload.CREATE,
    #     keys, threshold))

    # batch = _create_batch(signer, txns)
    # batch_list = BatchList(batches=[batch])

    # try:
    #     with open(args.output, 'wb') as batch_file:
    #         batch_file.write(batch_list.SerializeToString())
    #     print('Generated {}'.format(args.output))
    # except IOError as e:
    #     raise CliException(
    #         'Unable to write to batch file: {}'.format(str(e)))
    pass
