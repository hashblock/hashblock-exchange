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

import logging

from sawtooth_sdk.processor.handler import TransactionHandler
from sawtooth_sdk.messaging.future import FutureTimeoutError
from sawtooth_sdk.processor.exceptions import InvalidTransaction
from sawtooth_sdk.processor.exceptions import InternalError

from modules.hashblock_zksnark import zkproc_insert_cm
from protobuf.ledger_pb2 import (
    LedgerPayload, LedgerMerkleTrie, Wallet, Token)

from modules.address import Address

LOGGER = logging.getLogger(__name__)

# Number of seconds to wait for state operations to succeed
STATE_TIMEOUT_SEC = 10


class LedgerTransactionHandler(TransactionHandler):

    def __init__(self):
        self._addresser = Address.ledger_addresser()
        self._action = None
        self._context = None

    @property
    def addresser(self):
        return self._addresser

    @property
    def family_name(self):
        return self.addresser.family_ns_name

    @property
    def family_versions(self):
        return self.addresser.family_versions

    @property
    def namespaces(self):
        return [self.addresser.family_ns_hash]

    # Context is stateful per apply call
    @property
    def context(self):
        return self._context

    @context.setter
    def context(self, ctx):
        self._context = ctx

    def apply(self, transaction, context):
        """Apply an inbound transaction"""
        self.context = context
        ledger_payload = LedgerPayload()
        ledger_payload.ParseFromString(transaction.payload)
        if ledger_payload.action == LedgerPayload.WALLET_GENESIS:
            self._genesis(ledger_payload.data, transaction.header.outputs)
        elif ledger_payload.action == LedgerPayload.WALLET_MINT_TOKEN:
            self._mint(ledger_payload.data, transaction.header.outputs)
        else:
            raise InvalidTransaction(
                "Not handling {}".format(ledger_payload.action))

    def _mint(self, edata, outputs):
        token = Token()
        token.ParseFromString(edata)
        LOGGER.debug("Servicing Mint Request")
        # Get the merkle trie and wallet and their current state
        wallet_res = _get_state(self.context, outputs[0])
        first_entry = False
        wallet = Wallet()
        if wallet_res:
            wallet.ParseFromString(wallet_res[0].data)
        else:
            first_entry = True
            LOGGER.debug("Wallet first use")
        mtree_res = _get_state(self.context, outputs[1])
        merkle = LedgerMerkleTrie()
        if not mtree_res:
            raise InvalidTransaction("No merkle trie found")
        else:
            merkle.ParseFromString(mtree_res[0].data)
        # LOGGER.debug("Wallet => {}".format(wallet))
        # LOGGER.debug("Merkle => {}".format(merkle))
        # Insert commitments to merkle trie
        try:
            results = zkproc_insert_cm(
                merkle.trie.decode('utf-8'),
                token.v_commitment,
                token.u_commitment,
                token.a_commitment,
                LOGGER)
        except InternalError as e:
            raise InvalidTransaction("From hbzkproc {}".format(e))

        # LOGGER.debug("After insert {}".format(results))
        # Get new trie and quantity commitment positions
        merkle.trie = bytes(results[0], 'utf8')
        if token.v_commitment == results[1][1]:
            token.v_pos = int(results[1][0])
        else:
            LOGGER.debug("No match on value")
        if token.u_commitment == results[2][1]:
            token.u_pos = int(results[2][0])
        else:
            LOGGER.debug("No match on unit")
        if token.a_commitment == results[3][1]:
            token.a_pos = int(results[3][0])
        else:
            LOGGER.debug("No match on asset")
        # Set updated merkle trie
        _set_state(self.context, outputs[1], merkle.SerializeToString())
        # Add token to wallet
        wlen = len(wallet.tokens) if not first_entry else 0
        wallet.tokens.add(id=wlen, state=1, token=token)
        _set_state(self.context, outputs[0], wallet.SerializeToString())

    def _genesis(self, edata, outputs):
        """Genesis operations

        Create the merkle trie (outputs[0] address) with data
        Create empty wallets for users (outputs[1:] addresses)
        """
        is_exist = []
        for y in outputs:
            s = _get_state(self.context, y)
            if s:
                is_exist.append(s[0])
        if is_exist:
            raise InvalidTransaction(
                "Invalid genesis, stuff exists {}".format(is_exist))
        else:
            LOGGER.debug("Setting merkle {} => {}".format(outputs[0], edata))
            _set_state(self.context, outputs[0], edata)
            [_set_state(
                self.context, y, Wallet().SerializeToString())
                for y in outputs[1:]]


def _get_state(context, address):
    try:
        results = context.get_state([address], timeout=STATE_TIMEOUT_SEC)
    except FutureTimeoutError:
        LOGGER.warning(
            'Timeout occured on context.get_state([%s])',
            address)
        raise InternalError('Unable to get {}'.format(address))
    return results


def _set_state(context, address, data):
    try:
        results = context.set_state(
            {address: data}, timeout=STATE_TIMEOUT_SEC)
    except FutureTimeoutError:
        LOGGER.warning(
            'Timeout occured on context.set_state([%s])',
            address)
        raise InternalError('Unable to set {}'.format(address))
    return results
