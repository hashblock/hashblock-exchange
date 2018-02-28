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
# from sawtooth_sdk.processor.exceptions import AuthorizationException

from protobuf.events_pb2 import EventPayload
from protobuf.events_pb2 import InitiateEvent
from protobuf.events_pb2 import ReciprocateEvent

# eventsset event initiate -k /root/.sawtooth/keys/your_key.priv --url http://rest-api:8008 5:2:3
# eventsset event initiate -k /root/.sawtooth/keys/your_key.priv --url http://rest-api:8008 10:7:13
# eventsset event reciprocate -k /root/.sawtooth/keys/your_key.priv --url http://rest-api:8008 <event_id> 10:7:13 2:7:13 1:2:3


LOGGER = logging.getLogger(__name__)

ADDRESS_PREFIX = 'events'
FAMILY_NAME = 'hashblock_events'

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
            EventPayload.INITIATE_EVENT: _apply_initiate,
            EventPayload.RECIPROCATE_EVENT: _apply_reciprocate,
        }

        event_payload = EventPayload()
        event_payload.ParseFromString(transaction.payload)

        try:
            return verbs[event_payload.action](event_payload, context)
        except KeyError:
            return _apply_invalid()


def _apply_invalid():
    raise InvalidTransaction(
        "'type' must be one of {INITIATE_EVENT, RECIPROCATE_EVENT}")


def _timeout_error(basemsg, data):
    LOGGER.warning('Timeout occured on %s ([%s])', basemsg, data)
    raise InternalError('Unable to get {}'.format(data))


def _apply_initiate(payload, context):
    LOGGER.debug("Executing initiate event")
    event_initiate = InitiateEvent()
    event_initiate.ParseFromString(payload.data)
    _check_initiate(event_initiate)
    LOGGER.debug("Adding initiate %s to state", payload.ikey)
    return _set_event(context, event_initiate, payload.ikey)


def _apply_reciprocate(payload, context):
    LOGGER.debug("Executing reciprocate event")
    event_reciprocate = ReciprocateEvent()
    event_reciprocate.ParseFromString(payload.data)
    _check_reciprocate(event_reciprocate)
    event_initiate = _get_event(context, InitiateEvent(), payload.ikey)
    new_reciprocate = ReciprocateEvent(
        plus=event_reciprocate.plus,
        minus=event_reciprocate.minus,
        ratio=event_reciprocate.ratio,
        quantity=event_reciprocate.quantity,
        initiateEvent=event_initiate)
    LOGGER.debug("Reciprocate hydrated with Initiate")
    return _complete_reciprocate_event(
        context, payload.rkey,
        new_reciprocate, payload.ikey)


def _complete_reciprocate_event(
    context, reciprocateFQNAddress,
        event_reciprocate, initiateFQNAddress):
    """
    Completes reciprocation by removing the initiate address
    from merkle trie posts the reciprocate data to trie
    """

    # Remove the intiate address merkle trie
    try:
        event_list = context.delete_state(
            [initiateFQNAddress], timeout=STATE_TIMEOUT_SEC)
    except FutureTimeoutError:
        _timeout_error('context._delete_state', initiateFQNAddress)
    if len(event_list) != 1:
        raise InternalError(
            'Event not deleted for {}'.format(initiateFQNAddress))
    LOGGER.debug("Removed initiate %s from state", initiateFQNAddress)

    # Add the reciprocate to the state
    _set_event(context, event_reciprocate, reciprocateFQNAddress)
    LOGGER.debug("Added reciprocate %s to state", reciprocateFQNAddress)

    context.add_event(
        event_type="events/reciprocated",
        attributes=[("reciprocated", reciprocateFQNAddress)])


def _get_event(context, event, eventFQNAddress):
    try:
        event_list = context.get_state(
            [eventFQNAddress], timeout=STATE_TIMEOUT_SEC)
    except FutureTimeoutError:
        _timeout_error('context._get_event', eventFQNAddress)
    if len(event_list) != 1:
        raise InternalError(
            'Event does not exists for {}'.format(eventFQNAddress))
    event.ParseFromString(event_list[0].data)
    return event


def _set_event(context, event, eventFQNAddress):
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

    return eventFQNAddress


def _check_initiate(event_initiate):
    _check_plus(event_initiate)
    _check_minus(event_initiate)
    _check_quanity(event_initiate)


def _check_reciprocate(event_reciprocate):
    _check_plus(event_reciprocate)
    _check_minus(event_reciprocate)
    _check_quanity(event_reciprocate)
    _check_ratio(event_reciprocate)


def _check_plus(event_payload):
    try:
        plus = event_payload.plus
    except AttributeError:
        raise InvalidTransaction('Plus is required')
    return plus


def _check_minus(event_payload):
    try:
        minus = event_payload.minus
    except AttributeError:
        raise InvalidTransaction('Minus is required')
    return minus


def _check_quanity(event_payload):
    try:
        quantity = event_payload.quantity
    except AttributeError:
        raise InvalidTransaction('Quantity is required')
    _check_value(quantity)
    _check_valueUnit(quantity)
    _check_resourceUnit(quantity)


def _check_value(event_payload):
    try:
        value = event_payload.value
    except AttributeError:
        raise InvalidTransaction('Quantity.Value is required')
    return value


def _check_valueUnit(event_payload):
    try:
        valueUnit = event_payload.valueUnit
    except AttributeError:
        raise InvalidTransaction('Quanity.ValueUnit is required')
    return valueUnit


def _check_resourceUnit(event_payload):
    try:
        resourceUnit = event_payload.resourceUnit
    except AttributeError:
        raise InvalidTransaction('Quantity.ResourceUnit is required')
    return resourceUnit


def _check_ratio(event_payload):
    try:
        ratio = event_payload.ratio
    except AttributeError:
        raise InvalidTransaction('Ratio is required')
    _check_numerator(ratio)
    _check_numerator(ratio)


def _check_numerator(event_payload):
    try:
        numerator = event_payload.numerator
    except AttributeError:
        raise InvalidTransaction('Ratio.Numerator is required')
    return numerator


def _check_denominator(event_payload):
    try:
        denominator = event_payload.denominator
    except AttributeError:
        raise InvalidTransaction('Ratio.Denominator is required')
    return denominator


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


@lru_cache(maxsize=128)
def _make_events_key(key):
    # split the key into 4 parts, maximum
    key_parts = key.split('.', maxsplit=_MAX_KEY_PARTS - 1)
    # compute the short hash of each part
    addr_parts = [_to_hash(x)[:_ADDRESS_PART_SIZE] for x in key_parts]
    # pad the parts with the empty hash, if needed
    addr_parts.extend([_EMPTY_PART] * (_MAX_KEY_PARTS - len(addr_parts)))
    return make_events_address(''.join(addr_parts))
