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

import os
import logging
import functools

from sawtooth_sdk.processor.handler import TransactionHandler
from sawtooth_sdk.messaging.future import FutureTimeoutError
from sawtooth_sdk.processor.exceptions import InvalidTransaction
from sawtooth_sdk.processor.exceptions import InternalError

from modules.address import Address
from modules.config import load_hashblock_config, valid_key

from processor.services import Service

from protobuf.match_pb2 import MatchEvent
from protobuf.match_pb2 import UTXQ
from protobuf.match_pb2 import MTXQ

LOGGER = logging.getLogger(__name__)
load_hashblock_config()

# Number of seconds to wait for key operations to succeed
STATE_TIMEOUT_SEC = 10

initiateActionSet = frozenset([
    MatchEvent.UTXQ_ASK,
    MatchEvent.UTXQ_OFFER,
    MatchEvent.UTXQ_COMMITMENT,
    MatchEvent.UTXQ_GIVE])

reciprocateActionSet = frozenset([
    MatchEvent.MTXQ_TELL,
    MatchEvent.MTXQ_ACCEPT,
    MatchEvent.MTXQ_OBLIGATION,
    MatchEvent.MTXQ_TAKE])


class MatchTransactionHandler(TransactionHandler):

    def __init__(self):
        self._addresser = Address(Address.FAMILY_MATCH, ['0.1.0', '0.2.0'])

    @property
    def addresser(self):
        return self._addresser

    @property
    def family_name(self):
        return self.addresser.namespace

    @property
    def family_versions(self):
        return self.addresser.version

    @property
    def namespaces(self):
        return [self.addresser.ns_family]

    def apply(self, transaction, context):
        """match-tp transaction handling entry point"""
        Service.factory(
            transaction,
            context,
            self.addresser).apply()
        exchange_payload = MatchEvent()
        exchange_payload.ParseFromString(transaction.payload)
        if exchange_payload.action in initiateActionSet:
            pass
        elif exchange_payload.action in reciprocateActionSet:
            apply_reciprocate(exchange_payload, context)
        else:
            return throw_invalid(
                "'action' must be one of {} or {}".
                format([initiateActionSet, reciprocateActionSet]))
        generateTxnSuccessFor(exchange_payload, context)


# Version 0.1.0 Module functions


matchEventKeyMap = {
    MatchEvent.UTXQ_ASK: "hashblock.match.ask",
    MatchEvent.MTXQ_TELL: "hashblock.match.tell",
    MatchEvent.UTXQ_OFFER: "hashblock.match.offer",
    MatchEvent.MTXQ_ACCEPT: "hashblock.match.accept",
    MatchEvent.UTXQ_COMMITMENT: "hashblock.match.commitment",
    MatchEvent.MTXQ_OBLIGATION: "hashblock.match.obligation",
    MatchEvent.UTXQ_GIVE: "hashblock.match.give",
    MatchEvent.MTXQ_TAKE: "hashblock.match.take"
}


def __post_exchange(context, exchange_type, attributes):
    context.add_event(
        event_type=exchange_type,
        attributes=attributes,
        timeout=STATE_TIMEOUT_SEC)


def generateTxnSuccessFor(payload, context):
    attributes = [
        ("status", "completed"), ("unbalanced_address", payload.ukey)]
    if payload.action in reciprocateActionSet:
        attributes.append(tuple(["balanced_address", payload.mkey]))
    __post_exchange(
        context,
        matchEventKeyMap[payload.action],
        attributes)


def generateTxnFailEvent(context, payload, msg):
    pass


def compose(*functions):
    """Fancy construction of a composition
    """
    return functools.reduce(
        lambda f, g: lambda x: f(g(x)),
        functions,
        lambda x: x)


def throw_invalid(msg):
    """Generic invalid transaction
    """
    raise InvalidTransaction(msg)


def _timeout_error(basemsg, data):
    """Generic timeout error for state get/set/delete
    """
    LOGGER.warning('Timeout occured on %s ([%s])', basemsg, data)
    raise InternalError('Unable to get {}'.format(data))


RECIPROCATE_VSET = {'plus', 'minus', 'quantity', 'ratio'}


def __check_existence(exchange, exchangeset):
    ep = valid_key(exchange.plus.decode())
    em = valid_key(exchange.minus.decode())
    # LOGGER.debug('P: {} => {}, M: {} => {}'.format(
    #     exchange.plus,
    #     ep,
    #     exchange.minus,
    #     em))
    if not ep or not em:
        throw_invalid("Unknown exchange partner keys")
    zset = set([f[0].name for f in exchange.ListFields()])
    return exchangeset == zset


def apply_reciprocate(payload, context):
    LOGGER.debug("Executing balancing exchange")
    exchange_reciprocate = MTXQ()
    exchange_reciprocate.ParseFromString(payload.mdata)
    exchange_initiate = UTXQ()
    __get_exchange(context, exchange_initiate, payload.ukey)
    if exchange_initiate.matched:
        throw_invalid(
            "Attempt to balance with reciprocated Initiate")
    if __check_existence(exchange_reciprocate, RECIPROCATE_VSET):
        try:
            __check_reciprocate(exchange_reciprocate, exchange_initiate)
        except InvalidTransaction:
            LOGGER.error("UTXQ and MTXQ DO NOT BALANCE")
            raise
    else:
        throw_invalid('Balancing exchange not well formed')

    LOGGER.info("UTXQ and MTXQ Balance!")
    exchange_initiate.matched = True
    exchange_reciprocate.unmatched.CopyFrom(exchange_initiate)
    __set_exchange(context, exchange_initiate, payload.ukey)
    __complete_reciprocate_exchange(
        context, payload.mkey,
        exchange_reciprocate, payload.ukey)


def __check_reciprocate(reciprocate, initiate):
    if initiate.plus.decode() != reciprocate.minus.decode() \
            or initiate.minus.decode() != reciprocate.plus.decode():
        throw_invalid(
            "Reciprocate partner out of synch with initiate partners")
    __check_balance(reciprocate, initiate, 'value')
    __check_balance(reciprocate, initiate, 'valueUnit')
    __check_balance(reciprocate, initiate, 'resourceUnit')


def __check_balance(reciprocate, initiate, key):
    """
    Check rqv == (iqv*rrnqv)/rrdqv
    """
    iqv = int.from_bytes(
        getattr(initiate.quantity, key), byteorder='little')
    rqv = int.from_bytes(
        getattr(reciprocate.quantity, key), byteorder='little')
    rrnqv = int.from_bytes(
        getattr(reciprocate.ratio.numerator, key), byteorder='little')
    rrdqv = int.from_bytes(
        getattr(reciprocate.ratio.denominator, key), byteorder='little')
    if rqv != (iqv * rrnqv) / rrdqv:
        throw_invalid("".join([key, ' is not in balance']))
    return True


def __get_exchange(context, exchange, exchangeFQNAddress):
    try:
        exchange_list = context.get_state(
            [exchangeFQNAddress], timeout=STATE_TIMEOUT_SEC)
    except FutureTimeoutError:
        _timeout_error('context._get_exchange', exchangeFQNAddress)
    if len(exchange_list) != 1:
        raise InternalError(
            'Event does not exists for {}'.format(exchangeFQNAddress))
    exchange.ParseFromString(exchange_list[0].data)


def __set_exchange(context, exchange, exchangeFQNAddress):
    """
    Sets an exchange state
    """
    exchange_data = exchange.SerializeToString()
    state_dict = {exchangeFQNAddress: exchange_data}
    try:
        addresses = context.set_state(
            state_dict,
            timeout=STATE_TIMEOUT_SEC)
    except FutureTimeoutError:
        raise InternalError('Unable to set {}'.format(exchangeFQNAddress))
    if len(addresses) != 1:
        raise InternalError(
            'Unable to save exchange for address {}'.
            format(exchangeFQNAddress))


def __complete_reciprocate_exchange(
    context, reciprocateFQNAddress,
        exchange_reciprocate, initiateFQNAddress):
    """
    Completes reciprocation by removing the initiate address
    from merkle trie posts the reciprocate data to trie
    """
    __set_exchange(context, exchange_reciprocate, reciprocateFQNAddress)
    LOGGER.debug("Added reciprocate %s to state", reciprocateFQNAddress)
