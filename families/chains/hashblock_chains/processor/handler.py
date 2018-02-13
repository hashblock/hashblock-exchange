# ------------------------------------------------------------------------------
# Copyright 2018 Frank V. Castellucci
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

import logging
import hashlib
import base64
from functools import lru_cache


from sawtooth_sdk.processor.handler import TransactionHandler
from sawtooth_sdk.messaging.future import FutureTimeoutError
from sawtooth_sdk.processor.exceptions import InvalidTransaction
from sawtooth_sdk.processor.exceptions import InternalError

from protobuf.chains_pb2 import ChainTransaction

LOGGER = logging.getLogger(__name__)
ADDRESS = ''


# Number of seconds to wait for state operations to succeed
STATE_TIMEOUT_SEC = 10


class ChainTransactionHandler(TransactionHandler):
    def __init__(self, namespace_prefix):
        global ADDRESS
        ADDRESS = namespace_prefix
        self._namespace_prefix = namespace_prefix

    @property
    def family_name(self):
        return 'hashblock_chains'

    @property
    def family_versions(self):
        return ['0.1.0']

    @property
    def namespaces(self):
        return [self._namespace_prefix]

    def apply(self, transaction, context):
        txn_header = transaction.header
        public_key = txn_header.signer_public_key

        chain_transaction = ChainTransaction()
        chain_transaction.ParseFromString(transaction.payload)

        if chain_transaction.type == ChainTransaction.INITIATE:
            return self._apply_initiate(
                public_key, chain_transaction.data, context)
        elif chain_transaction.action == ChainTransaction.RECIPROCATE:
            return self._apply_reciprocate(
                public_key,
                chain_transaction.data,
                context)
        else:
            raise InvalidTransaction(
                "'type' must be one of {INITIATE, RECIPROCATE}")

    def _apply_initiate(self, public_key, chain_initiate_data, context):
        pass

    def _apply_reciprocate(self, public_key, chain_reciprocate_data, context):
        pass


def _to_hash(value):
    return hashlib.sha256(value.encode()).hexdigest()


_MAX_KEY_PARTS = 4
_ADDRESS_PART_SIZE = 16
_EMPTY_PART = _to_hash('')[:_ADDRESS_PART_SIZE]


@lru_cache(maxsize=128)
def _make_chain_key(key):
    # split the key into 4 parts, maximum
    key_parts = key.split('.', maxsplit=_MAX_KEY_PARTS - 1)
    # compute the short hash of each part
    addr_parts = [_to_hash(x)[:_ADDRESS_PART_SIZE] for x in key_parts]
    # pad the parts with the empty hash, if needed
    addr_parts.extend([_EMPTY_PART] * (_MAX_KEY_PARTS - len(addr_parts)))

    return ADDRESS + ''.join(addr_parts)
