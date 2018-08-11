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


from shared.transactions import (create_transaction)
from protobuf.ledger_pb2 import (LedgerPayload, Token)
from modules.config import (HB_OPERATOR, public_key_values_list)
from modules.decode import ledger_addresser as _addresser

_default_merkletrie = '0' * 64


def _validate_quantity(data):
    pass


def _create_mint(ingest):
    pass


def _create_commit_wrapper(ingest):
    pass


def _create_inputs_outputs(ingest):
    pass


def mint_token(data):
    return
    # direct = compose_builder(
    #     submit_single_txn, create_transaction, _create_inputs_outputs,
    #     _create_commit_wrapper, _create_mint)
    # direct((
    #     data['signer'],
    #     commit_addresser,
    #     data))


# Genesis operation
# //  Create LedgerMerkleTrie txn.outputs[0] has address, data has trie
# //  Create User Wallets txn.outputs[1-n] have addresses
# //  data is starting Merkle Trie string (default is 64 '0's)

def create_ledger_genesis(merkletrie=None):
    payload = LedgerPayload(
        action=LedgerPayload.WALLET_GENESIS,
        data=bytes(_default_merkletrie, 'utf8')
        if not merkletrie else bytes(merkletrie, 'utf8'))

    addresses = [_addresser.wallet(y) for y in public_key_values_list()]
    addresses.insert(0, _addresser.merkle)
    perms = {
        'inputs': addresses,
        'outputs': addresses
    }
    _, txn = create_transaction((HB_OPERATOR, _addresser, perms, payload))
    return [txn]
