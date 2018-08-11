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
        if(ledger_payload.action == LedgerPayload.WALLET_GENESIS):
            self._genesis(ledger_payload.data, transaction.header.outputs)
            pass
        else:
            pass
        # address = self.addresser.ledger(ledger.id, ledger.property)
        # return self._set_ledger(context, ledger, address)

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
