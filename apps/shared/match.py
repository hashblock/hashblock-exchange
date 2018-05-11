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

"""match - Match business logic

This module is referenced when posting utxq and mtxq exchanges
"""
import uuid

from shared.transactions import (
    submit_single_txn, create_transaction, compose_builder)

from modules.address import Address
from modules.config import valid_signer
from modules.decode import decode_from_leaf
from modules.exceptions import RestException, DataException
from modules.exceptions import AssetNotExistException
from protobuf.match_pb2 import (
    MatchEvent, UTXQ, MTXQ, Quantity, Ratio)


_asset_addrs = Address(Address.FAMILY_ASSET, "0.1.0")
_utxq_addrs = Address(Address.FAMILY_MATCH, "0.1.0", Address.DIMENSION_UTXQ)
_mtxq_addrs = Address(Address.FAMILY_MATCH, "0.1.0", Address.DIMENSION_MTXQ)

_ACTION_MAP = {
    'ask': MatchEvent.UTXQ_ASK,
    'tell': MatchEvent.MTXQ_TELL,
    'offer': MatchEvent.UTXQ_OFFER,
    'accept': MatchEvent.MTXQ_ACCEPT,
    'commitment': MatchEvent.UTXQ_COMMITMENT,
    'obligation': MatchEvent.MTXQ_OBLIGATION,
    'give': MatchEvent.UTXQ_GIVE,
    'take': MatchEvent.MTXQ_TAKE}


def __validate_partners(plus, minus):
    """Validate the plus and minus are reachable keys"""
    valid_signer(plus)
    valid_signer(minus)
    print("Validated partners")


def __validate_assets(value, unit, resource):
    """Validate and return asset addresses that are reachable"""
    int(value)
    unit_add = _asset_addrs.asset_item(
        Address.DIMENSION_UNIT,
        unit['system'], unit['key'])
    resource_add = _asset_addrs.asset_item(
        Address.DIMENSION_RESOURCE,
        resource['system'], resource['key'])

    unit_res = decode_from_leaf(unit_add)
    resource_res = decode_from_leaf(resource_add)
    if not unit_res['data'] or not resource_res['data']:
        raise AssetNotExistException
    return (unit_res['data'], resource_res['data'])


def __validate_utxq_exists(address):
    """Check that the utxq exists to recipricate on"""
    try:
        decode_from_leaf(address)
    except RestException:
        raise DataException('Invalid initiate (utxq) address')


def __validate_utxq(request):
    """Validate the content for utxq"""
    __validate_partners(request["plus"], request["minus"])
    quantity_assets = __validate_assets(
        request['quantity']['value'],
        request['quantity']['unit'], request['quantity']['resource'])
    print("Validated utxq")
    return (quantity_assets)


def __validate_mtxq(request):
    """Validate the content for mtxq"""
    __validate_utxq_exists(request["utxq_address"])
    quantity_assets = __validate_assets(
        request['quantity']['value'],
        request['quantity']['unit'],
        request['quantity']['resource'])

    numerator_assets = __validate_assets(
        request['ratio']['numerator']['value'],
        request['ratio']['numerator']['unit'],
        request['ratio']['numerator']['resource'])

    demoninator_assets = __validate_assets(
        request['ratio']['denominator']['value'],
        request['ratio']['denominator']['unit'],
        request['ratio']['denominator']['resource'])
    return (quantity_assets, numerator_assets, demoninator_assets)


def __create_quantity(value, quantity):
    """Converts a quantity type into byte string from prime number"""
    unit_data, resource_data = quantity
    return Quantity(
        value=int(value).to_bytes(2, byteorder='little'),
        valueUnit=int(unit_data['value']).to_bytes(
            2, byteorder='little'),
        resourceUnit=int(resource_data['value']).to_bytes(
            2, byteorder='little'))


def __create_utxq(ingest):
    """Create a utxq object"""
    operation, addresser, quantity, data = ingest
    return (operation, addresser, data['plus'], UTXQ(
        matched=False,
        plus=valid_signer(data['plus']).encode(),
        minus=valid_signer(data['minus']).encode(),
        quantity=__create_quantity(data['quantity']['value'], quantity)))


def __create_initiate_payload(ingest):
    """Create the utxq payload"""
    operation, addresser, signer, data = ingest
    return (operation, addresser, signer, MatchEvent(
        data=data.SerializeToString(),
        ukey=addresser.txq_item(
            addresser.dimension, operation, str(uuid.uuid4)),
        action=_ACTION_MAP[operation]))


def __create_initiate_inputs_outputs(ingest):
    """Create utxq address (state) authorizations"""
    operation, addresser, signer, payload = ingest
    inputs = []
    outputs = [payload.ukey]
    return (
        signer, addresser, {"inputs": inputs, "outputs": outputs}, payload)


def __create_mtxq(ingest):
    """Create the mtxq object"""
    operation, addresser, qassets, data = ingest
    quantity, numerator, denominator = qassets
    # mtxq = MTXQ()
    return (operation, addresser, data, MTXQ(
        plus=valid_signer(data['plus']).encode(),
        minus=valid_signer(data['minus']).encode(),
        quantity=__create_quantity(data['quantity']['value'], quantity),
        ratio=Ratio(
            numerator=__create_quantity(
                data['ratio']['numerator']['value'], numerator),
            denominator=__create_quantity(
                data['ratio']['denominator']['value'], denominator))))


def __create_reciprocate_payload(ingest):
    """Create the mtxq payload"""
    operation, addresser, request, payload = ingest
    return (operation, addresser, request['plus'], MatchEvent(
        data=payload.SerializeToString(),
        ukey=request['utxq_address'],
        mkey=addresser.txq_item(
            addresser.dimension, operation, str(uuid.uuid4)),
        action=_ACTION_MAP[operation]))


def __create_reciprocate_inputs_outputs(ingest):
    """Create mtxq address (state) authorizations"""
    operation, addresser, signer, payload = ingest
    inputs = [payload.ukey]
    outputs = [payload.ukey, payload.mkey]
    return (
        signer, addresser, {"inputs": inputs, "outputs": outputs}, payload)


def create_utxq(operation, request):
    """Create utxq transaction"""
    quant = __validate_utxq(request)
    # Creaate utxq
    # Create payload
    # Create inputs/outputs
    # Create transaction
    # Create batch
    utxq_build = compose_builder(
        submit_single_txn, create_transaction,
        __create_initiate_inputs_outputs, __create_initiate_payload,
        __create_utxq)
    utxq_build((operation, _utxq_addrs, quant, request))


def create_mtxq(operation, request):
    """Create mtxq transaction"""
    qnd = __validate_mtxq(request)
    # Creaate mtxq
    # Create payload
    # Create inputs/outputs
    # Create transaction
    # Create batch
    mtxq_build = compose_builder(
        submit_single_txn, create_transaction,
        __create_reciprocate_inputs_outputs, __create_reciprocate_payload,
        __create_mtxq)
    mtxq_build((operation, _mtxq_addrs, qnd, request))
