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
from protobuf.events_pb2 import InitiateList

# eventsset event initiate -k /root/.sawtooth/keys/your_key.priv --url http://rest-api:8008 5:2:3
# eventsset event initiate -k /root/.sawtooth/keys/your_key.priv --url http://rest-api:8008 10:7:13
# eventsset event reciprocate -k /root/.sawtooth/keys/your_key.priv --url http://rest-api:8008 <event_id> 10:7:13 2:7:13 1:2:3



LOGGER = logging.getLogger(__name__)

ADDRESS_PREFIX = 'events'
FAMILY_NAME = 'hashblock_events'

EVENTS_ADDRESS_PREFIX = hashlib.sha512(
    ADDRESS_PREFIX.encode('utf-8')).hexdigest()[0:6]

INITIATE_EVENT_KEY = 'hashblock.events.initiate.'
RECIPROCATE_EVENT_KEY = 'hashblock.events.reciprocate.'
INITIATE_EVENT_LIST_KEY = 'hashblock.events.list'

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
        signer_key = transaction.header.signer_public_key
        event_transaction = EventPayload()
        event_transaction.ParseFromString(transaction.payload)
        keyUUID = event_transaction.key

        try:
            return verbs[event_transaction.action](
                keyUUID, event_transaction.data,
                context, signer_key)
        except KeyError:
            return _apply_invalid()


def _apply_invalid():
    raise InvalidTransaction(
        "'type' must be one of {INITIATE_EVENT, RECIPROCATE_EVENT}")


def _timeout_error(basemsg, data):
    LOGGER.warning('Timeout occured on %s ([%s])', basemsg, data)
    raise InternalError('Unable to get {}'.format(data))


def _apply_initiate(initiateUUID, payload_data, context, signer_key):
    LOGGER.debug("Executing initiate event")
    event_initiate = InitiateEvent()
    event_initiate.ParseFromString(payload_data)
    initiateFQNAddress = _ensure_initiate_not_exist(context, initiateUUID)
    _check_initiate(event_initiate)
    return _set_initiate_event(context, event_initiate, initiateFQNAddress)


def _apply_reciprocate(reciprocateUUID, payload_data, context, signer_key):
    LOGGER.debug("Executing reciprocate event")
    event_reciprocate = ReciprocateEvent()
    event_reciprocate.ParseFromString(payload_data)
    initiateFQNAddress = event_reciprocate.initiate_event_id
    reciprocateFQNAddress = make_fqnaddress(RECIPROCATE_EVENT_KEY, reciprocateUUID)
    _get_initiate_event(context, initiateFQNAddress)
    _check_reciprocate(event_reciprocate)
    return _complete_reciprocate_event(
        context, reciprocateFQNAddress,
        event_reciprocate, initiateFQNAddress)


def _ensure_initiate_not_exist(context, initiateUUID):
    """
    Ensure that a hashblock.events.initiate.UUID does
    not exist stadalone in state or in our hashblock.events.initiate
    collection
    """
    initiateFQNAddress = make_fqnaddress(INITIATE_EVENT_KEY, initiateUUID)

    # Get initiate event standalone
    try:
        entries_list = context.get_state(
            [initiateFQNAddress], timeout=STATE_TIMEOUT_SEC)
    except FutureTimeoutError:
        _timeout_error('context.get_state', initiateUUID)
    if len(entries_list) != 0:
        raise InternalError(
            'Initiate event exists for {}'.format(initiateUUID))

    # Try the collection
    try:
        entries_list = context.get_state(
            [INITIATE_EVENT_LIST_ADDRESS], timeout=STATE_TIMEOUT_SEC)
    except FutureTimeoutError:
        _timeout_error('context.get_state', initiateUUID)

    if len(entries_list) != 0:
        ilist = InitiateList()
        ilist.ParseFromString(entries_list[0].data)
        if initiateFQNAddress in ilist.entries:
            raise InternalError(
                'Initiate event exists for {}'.format(initiateUUID))

    return initiateFQNAddress


def _complete_reciprocate_event(
    context,
    reciprocateFQNAddress,
    event_reciprocate,
        initiateFQNAddress):
    """
    Completes reciprocation by removing the initiate address
    from our initiate address list and posts the reciprocate
    data to state
    """
    entries_list = _get_initiate_list(context)
    ilist = InitiateList()
    if len(entries_list) != 0:
        ilist.ParseFromString(entries_list[0].data)
        if initiateFQNAddress not in ilist.entries:
            raise InternalError(
                'Initiate event does not exist for {}'
                .format(initiateFQNAddress))
    else:
        raise InternalError('Empty initiation list')

    # Remove the intiate address from the list
    ilist.entries.remove(initiateFQNAddress)
    _set_initiate_list(context, ilist)
    LOGGER.debug("Removed initiate %s from list", initiateFQNAddress)

    # Add the reciprocate to the state
    _set_event(context, event_reciprocate, reciprocateFQNAddress)
    LOGGER.debug("Added reciprocate %s to state", reciprocateFQNAddress)

    context.add_event(
        event_type="events/reciprocated",
        attributes=[("reciprocated", reciprocateFQNAddress)])


def _get_initiate_event(context, initiateFQNAddress):
    """
    Gets an initiate event address from our
    hashblock.events.initiate list
    """

    # Get initiate event list
    entries_list = _get_initiate_list(context)

    ilist = InitiateList()
    ilist.ParseFromString(entries_list[0].data)
    if initiateFQNAddress not in ilist.entries:
        raise InternalError(
            'Event does not exist in list for {}'.format(initiateFQNAddress))

    return initiateFQNAddress


def _set_initiate_event(context, event_initiate, initiateFQNAddress):
    """
    Creates an iniitate event in state and stores
    its address in our initiate list
    """

    # Sets the event structure to state
    _set_event(context, event_initiate, initiateFQNAddress)
    LOGGER.debug("Added initiate %s to state", initiateFQNAddress)

    # Get initiate event list
    entries_list = _get_initiate_list(context)

    # Append my initiate address to list
    ilist = InitiateList()
    if len(entries_list) != 0:
        ilist.ParseFromString(entries_list[0].data)
    ilist.entries.append(initiateFQNAddress)
    _set_initiate_list(context, ilist)
    LOGGER.debug("Added initiate %s to list", initiateFQNAddress)

    context.add_event(
        event_type="events/initiated",
        attributes=[("initiated", initiateFQNAddress)])


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
            'Unable to save initiate value {}'.format(eventFQNAddress))

    return eventFQNAddress


def _set_initiate_list(context, ilist):
    """
    Sets the initiation list in state
    """
    try:
        context.set_state(
            {INITIATE_EVENT_LIST_ADDRESS: ilist.SerializeToString()},
            timeout=STATE_TIMEOUT_SEC)
    except FutureTimeoutError:
        raise InternalError('Unable to set initiatelist')


def _get_initiate_list(context):
    """
    Get the main unrecpiprocated list of initiate events
    """
    try:
        entries_list = context.get_state(
            [INITIATE_EVENT_LIST_ADDRESS], timeout=STATE_TIMEOUT_SEC)
    except FutureTimeoutError:
        _timeout_error('context.get_state', INITIATE_EVENT_LIST_KEY)
    return entries_list


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


INITIATE_EVENT_LIST_ADDRESS = _make_events_key(INITIATE_EVENT_LIST_KEY)
