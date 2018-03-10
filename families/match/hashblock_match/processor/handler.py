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
import functools

from sawtooth_sdk.processor.handler import TransactionHandler
from sawtooth_sdk.messaging.future import FutureTimeoutError
from sawtooth_sdk.processor.exceptions import InvalidTransaction
from sawtooth_sdk.processor.exceptions import InternalError
# from sawtooth_sdk.processor.exceptions import AuthorizationException

from protobuf.match_pb2 import MatchEvent
from protobuf.match_pb2 import UTXQ
from protobuf.match_pb2 import MTXQ

# initiate 5:2:3
# initiate 10:7:13
# reciprocate <exchange_id> 10:7:13 2:7:13 1:2:3


LOGGER = logging.getLogger(__name__)

ADDRESS_PREFIX = 'match'
FAMILY_NAME = 'hashblock-match'

MATCH_ADDRESS_PREFIX = hashlib.sha512(
    FAMILY_NAME.encode('utf-8')).hexdigest()[0:6]

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

    @property
    def family_name(self):
        return FAMILY_NAME

    @property
    def family_versions(self):
        return ['0.2.0']

    @property
    def namespaces(self):
        return [MATCH_ADDRESS_PREFIX]

    def apply(self, transaction, context):

        exchange_payload = MatchEvent()
        exchange_payload.ParseFromString(transaction.payload)
        if exchange_payload.action in initiateActionSet:
            apply_initiate(exchange_payload, context)
        elif exchange_payload.action in reciprocateActionSet:
            apply_reciprocate(exchange_payload, context)
        else:
            return throw_invalid(
                "'action' must be one of {} or {}".
                format([initiateActionSet, reciprocateActionSet]))

        (exchange_payload, context)
        generateTxnSuccessFor(exchange_payload, context)


# Module functions


matchEventKeyMap = {
    MatchEvent.UTXQ_ASK: "hashblock.match.ask",
    MatchEvent.MTXQ_TELL: "hashblock.matchtell",
    MatchEvent.UTXQ_OFFER: "hashblock.matchoffer",
    MatchEvent.MTXQ_ACCEPT: "hashblock.matchaccept",
    MatchEvent.UTXQ_COMMITMENT: "hashblock.matchcommitment",
    MatchEvent.MTXQ_OBLIGATION: "hashblock.matchobligation",
    MatchEvent.UTXQ_GIVE: "hashblock.matchgive",
    MatchEvent.MTXQ_TAKE: "hashblock.matchtake"
}


def __post_exchange(context, exchange_type, attributes):
    context.add_exchange(
        exchange_type=exchange_type,
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
    """
    Fancy construction of a composition
    """
    return functools.reduce(
        lambda f, g: lambda x: f(g(x)),
        functions,
        lambda x: x)


def throw_invalid(msg):
    """
    Generic invalid stringaction
    """
    raise InvalidTransaction(msg)


def _timeout_error(basemsg, data):
    LOGGER.warning('Timeout occured on %s ([%s])', basemsg, data)
    raise InternalError('Unable to get {}'.format(data))


INITIATE_VSET = {'plus', 'minus', 'quantity'}
RECIPROCATE_VSET = {'plus', 'minus', 'quantity', 'ratio'}


def __check_existence(exchange, exchangeset):
    return exchangeset == set([f[0].name for f in exchange.ListFields()])


def apply_initiate(payload, context):
    LOGGER.debug("Executing unbalanced exchange")
    exchange_initiate = UTXQ()
    exchange_initiate.ParseFromString(payload.data)
    if __check_existence(exchange_initiate, INITIATE_VSET):
        if exchange_initiate.matched:
            throw_invalid('Already reconcilled')
        else:
            __set_exchange(context, exchange_initiate, payload.ukey)
            LOGGER.debug("Added unbalanced %s to state", payload.ukey)
    else:
        throw_invalid('Unbalanced exchange not well formed')


def apply_reciprocate(payload, context):
    LOGGER.debug("Executing balancing exchange")
    exchange_reciprocate = MTXQ()
    exchange_reciprocate.ParseFromString(payload.data)
    exchange_initiate = UTXQ()
    __get_exchange(context, exchange_initiate, payload.ukey)
    if exchange_initiate.reciprocated:
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


def _to_hash(value):
    return hashlib.sha256(value.encode()).hexdigest()


_MAX_KEY_PARTS = 4
_ADDRESS_PART_SIZE = 16
_EMPTY_PART = _to_hash('')[:_ADDRESS_PART_SIZE]


def make_exchanges_address(data):
    return MATCH_ADDRESS_PREFIX + hashlib.sha512(
        data.encode('utf-8')).hexdigest()[-64:]


def make_fqnaddress(key, keyUUID):
    return _make_exchanges_key(''.join([key, keyUUID]))


@functools.lru_cache(maxsize=128)
def _make_exchanges_key(key):
    # split the key into 4 parts, maximum
    key_parts = key.split('.', maxsplit=_MAX_KEY_PARTS - 1)
    # compute the short hash of each part
    addr_parts = [_to_hash(x)[:_ADDRESS_PART_SIZE] for x in key_parts]
    # pad the parts with the empty hash, if needed
    addr_parts.extend([_EMPTY_PART] * (_MAX_KEY_PARTS - len(addr_parts)))
    return make_exchanges_address(''.join(addr_parts))
