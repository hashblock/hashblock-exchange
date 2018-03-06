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

from protobuf.events_pb2 import EventPayload
from protobuf.events_pb2 import InitiateEvent
from protobuf.events_pb2 import ReciprocateEvent

# initiate 5:2:3
# initiate 10:7:13
# reciprocate <event_id> 10:7:13 2:7:13 1:2:3


LOGGER = logging.getLogger(__name__)

ADDRESS_PREFIX = 'events'
FAMILY_NAME = 'hashblock_events'
DEAD_KEY = 'DEAD'

EVENTS_ADDRESS_PREFIX = hashlib.sha512(
    ADDRESS_PREFIX.encode('utf-8')).hexdigest()[0:6]

# Number of seconds to wait for key operations to succeed
STATE_TIMEOUT_SEC = 10


class EventTransactionHandler(TransactionHandler):

    @property
    def family_name(self):
        return FAMILY_NAME

    @property
    def family_versions(self):
        return ['0.1.0']

    @property
    def namespaces(self):
        return [EVENTS_ADDRESS_PREFIX]

    def apply(self, transaction, context):
        verbs = {
            EventPayload.INITIATE_EVENT: apply_initiate,
            EventPayload.RECIPROCATE_EVENT: apply_reciprocate,
        }
        event_payload = EventPayload()
        event_payload.ParseFromString(transaction.payload)
        try:
            verbs[event_payload.action](event_payload, context)
            generateTxnSuccessFor(event_payload, context)
        except KeyError:
            return throw_invalid(
                "'action' must be one of {INITIATE_EVENT, RECIPROCATE_EVENT}")

# Module functions


transactionKeyMap = {
    EventPayload.INITIATE_EVENT: "hashblock.transaction.initiate",
    EventPayload.RECIPROCATE_EVENT: "hashblock.transactio.reciprocate"
}


def __post_event(context, event_type, attributes):
    context.add_event(
        event_type=event_type,
        attributes=attributes,
        timeout=STATE_TIMEOUT_SEC)


def generateTxnSuccessFor(payload, context):
    attributes = [("status", "completed"), ("initiate_address", payload.ikey)]
    if payload.action == EventPayload.RECIPROCATE_EVENT:
        attributes.append(tuple(["reciprocate_address", payload.rkey]))
    __post_event(
        context,
        transactionKeyMap[payload.action],
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


def __check_existence(event, eventset):
    return eventset == set([f[0].name for f in event.ListFields()])


def apply_initiate(payload, context):
    LOGGER.debug("Executing initiate event")
    event_initiate = InitiateEvent()
    event_initiate.ParseFromString(payload.data)
    if __check_existence(event_initiate, INITIATE_VSET):
        if event_initiate.reciprocated:
            throw_invalid('Initiate already reconcilled')
        else:
            __set_event(context, event_initiate, payload.ikey)
            LOGGER.debug("Added Initiate %s to state", payload.ikey)
    else:
        throw_invalid('Initiate not well formed')


def apply_reciprocate(payload, context):
    LOGGER.debug("Executing reciprocate event")
    event_reciprocate = ReciprocateEvent()
    event_reciprocate.ParseFromString(payload.data)
    event_initiate = InitiateEvent()
    __get_event(context, event_initiate, payload.ikey)
    if event_initiate.reciprocated:
        throw_invalid(
            "Attempt to balance with reciprocated Initiate")
    if __check_existence(event_reciprocate, RECIPROCATE_VSET):
        try:
            __check_reciprocate(event_reciprocate, event_initiate)
        except InvalidTransaction:
            LOGGER.error("Initiate and Reciprocate DO NOT BALANCE")
            raise
    else:
        throw_invalid('Reciprocate not well formed')

    LOGGER.info("Initiate and Reciprocate Balance!")
    event_initiate.reciprocated = True
    event_reciprocate.initiateEvent.CopyFrom(event_initiate)
    __set_event(context, event_initiate, payload.ikey)
    __complete_reciprocate_event(
        context, payload.rkey,
        event_reciprocate, payload.ikey)


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


def __get_event(context, event, eventFQNAddress):
    try:
        event_list = context.get_state(
            [eventFQNAddress], timeout=STATE_TIMEOUT_SEC)
    except FutureTimeoutError:
        _timeout_error('context._get_event', eventFQNAddress)
    if len(event_list) != 1:
        raise InternalError(
            'Event does not exists for {}'.format(eventFQNAddress))
    event.ParseFromString(event_list[0].data)


def __set_event(context, event, eventFQNAddress):
    """
    Sets an event state
    """
    event_data = event.SerializeToString()
    state_dict = {eventFQNAddress: event_data}
    try:
        addresses = context.set_state(
            state_dict,
            timeout=STATE_TIMEOUT_SEC)
    except FutureTimeoutError:
        raise InternalError('Unable to set {}'.format(eventFQNAddress))
    if len(addresses) != 1:
        raise InternalError(
            'Unable to save event for address {}'.format(eventFQNAddress))


def __complete_reciprocate_event(
    context, reciprocateFQNAddress,
        event_reciprocate, initiateFQNAddress):
    """
    Completes reciprocation by removing the initiate address
    from merkle trie posts the reciprocate data to trie
    """
    __set_event(context, event_reciprocate, reciprocateFQNAddress)
    LOGGER.debug("Added reciprocate %s to state", reciprocateFQNAddress)


def _to_hash(value):
    return hashlib.sha256(value.encode()).hexdigest()


_MAX_KEY_PARTS = 4
_ADDRESS_PART_SIZE = 16
_EMPTY_PART = _to_hash('')[:_ADDRESS_PART_SIZE]


def make_events_address(data):
    return EVENTS_ADDRESS_PREFIX + hashlib.sha512(
        data.encode('utf-8')).hexdigest()[-64:]


def make_fqnaddress(key, keyUUID):
    return _make_events_key(''.join([key, keyUUID]))


@functools.lru_cache(maxsize=128)
def _make_events_key(key):
    # split the key into 4 parts, maximum
    key_parts = key.split('.', maxsplit=_MAX_KEY_PARTS - 1)
    # compute the short hash of each part
    addr_parts = [_to_hash(x)[:_ADDRESS_PART_SIZE] for x in key_parts]
    # pad the parts with the empty hash, if needed
    addr_parts.extend([_EMPTY_PART] * (_MAX_KEY_PARTS - len(addr_parts)))
    return make_events_address(''.join(addr_parts))
