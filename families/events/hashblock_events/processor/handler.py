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
from sawtooth_sdk.processor.exceptions import AuthorizationException

from protobuf.events_pb2 import EventPayload
from protobuf.events_pb2 import InitiateEvent
from protobuf.events_pb2 import ReciprocateEvent

LOGGER = logging.getLogger(__name__)

ADDRESS_PREFIX = 'events'
FAMILY_NAME = 'hashblock_events'

EVENTS_ADDRESS_PREFIX = hashlib.sha512(
    ADDRESS_PREFIX.encode('utf-8')).hexdigest()[0:6]

_MAX_KEY_PARTS = 4


def make_events_address(data):
    return EVENTS_ADDRESS_PREFIX + hashlib.sha512(
        data.encode('utf-8')).hexdigest()[-64:]


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
        keyUUID = event_transaction.key.split(
            '.', maxsplit=_MAX_KEY_PARTS - 1)[-1]

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


def _apply_initiate(keyUUID, payload_data, context, signer_key):
    event_initiate = InitiateEvent()
    event_initiate.ParseFromString(payload_data)
    LOGGER.debug(event_initiate)
    myevent = _get_initiate_event(context, keyUUID)
    if myevent:
        raise InvalidTransaction(
            'Initiate already set for UUID {} .'.keyUUID)
    _check_initiate(event_initiate)
    return _set_initiate_event(context, event_initiate, keyUUID)


def _apply_reciprocate(keyUUID, payload_data, context, signer_key):
    event_reciprocate = ReciprocateEvent()
    event_reciprocate.ParseFromString(payload_data)
    myevent = _get_initiate_event(context, keyUUID)
    if not myevent:
        raise InvalidTransaction(
            'Reciprocate: no matching key for UUID {} .'.keyUUID)
    _check_reciprocate(event_reciprocate)
    return _complete_reciprocate_event(context, keyUUID)


def _complete_reciprocate_event(context, address_key):
    mykey = _make_events_key(address_key)
    myevent = _get_initiate_event(context, address_key)
    if not myevent:
        raise InvalidTransaction(
            'Initiate does not exist {} .'.format(myevent))
    try:
        entries_list = context.delete_state([mykey])
    except FutureTimeoutError:
        _timeout_error('context.delete_state', address_key)
    if len(entries_list) != 1:
        LOGGER.warning(
            'Failed to remove value on address %s', address_key)
        raise InternalError(
            'Unable to save config value {}'.format(address_key))
    context.add_event(
        event_type="events/reciprocated",
        attributes=[("reciprocated", address_key)])


def _get_initiate_event(context, uuid_key):
    initiate_event = InitiateEvent()
    mykey = _make_events_key(uuid_key)
    LOGGER.debug(uuid_key)
    LOGGER.debug(mykey)

    try:
        entries_list = context.get_state([mykey], timeout=STATE_TIMEOUT_SEC)
    except FutureTimeoutError:
        _timeout_error('context.get_state', uuid_key)
    except AuthorizationException:
        entries_list = None
        LOGGER.error("State not found")

    LOGGER.debug(entries_list)
    if entries_list:
        initiate_event.ParseFromString(entries_list[0].data)
    else:
        initiate_event = None

    LOGGER.debug(initiate_event)

    return initiate_event


def _set_initiate_event(context, event_initiate, uuid_key):
    mykey = _make_events_key(uuid_key)
    # base64.b64encode()
    LOGGER.debug(mykey)
    LOGGER.debug(event_initiate)
    LOGGER.debug(event_initiate.SerializeToString())
    try:
        addresses = list(context.set_state(
            {mykey: event_initiate.SerializeToString()},
            timeout=STATE_TIMEOUT_SEC))
    except FutureTimeoutError:
        LOGGER.warning(
            'Timeout occured on context.set_staten for %s', uuid_key)
        raise InternalError('Unable to set {}'.format(mykey))

    if len(addresses) != 1:
        LOGGER.warning(
            'Failed to save value on address %s', uuid_key)
        raise InternalError(
            'Unable to save config value {}'.format(uuid_key))
        LOGGER.info('Event setting %s changed from NIL to %s',
                    uuid_key, event_initiate)
    context.add_event(
        event_type="events/initiated",
        attributes=[("initiated", uuid_key)])


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


_ADDRESS_PART_SIZE = 16
_EMPTY_PART = _to_hash('')[:_ADDRESS_PART_SIZE]


@lru_cache(maxsize=128)
def _make_events_key(key):
    key_parts = key.split('.', maxsplit=_MAX_KEY_PARTS - 1)
    key_parts.extend([''] * (_MAX_KEY_PARTS - len(key_parts)))

    return EVENTS_ADDRESS_PREFIX + ''.join(_to_hash(x) for x in key_parts)

    # split the key into 4 parts, maximum
    # key_parts = key.split('.', maxsplit=_MAX_KEY_PARTS - 1)
    # compute the short hash of each part
    # addr_parts = [_to_hash(x)[:_ADDRESS_PART_SIZE] for x in key_parts]
    # pad the parts with the empty hash, if needed
    # addr_parts.extend([_EMPTY_PART] * (_MAX_KEY_PARTS - len(addr_parts)))
    # return make_events_address(''.join(addr_parts))
