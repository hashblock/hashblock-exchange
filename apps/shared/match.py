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
from shared.transactions import submit_single_batch, create_single_batch
from shared.transactions import create_single_transaction, compose_builder
from modules.address import Address
from modules.config import valid_signer
from modules.decode import decode_from_leaf
from modules.exceptions import RestException, DataException
from modules.exceptions import AssetNotExistException
from protobuf.match_pb2 import MatchEvent
from protobuf.match_pb2 import UTXQ
from protobuf.match_pb2 import MTXQ
from protobuf.match_pb2 import Quantity
from protobuf.match_pb2 import Ratio


_asset_addrs = Address(Address.FAMILY_ASSET, "0.1.0")

__operation_sets = {
    'utxq': {'ask', 'offer', 'commitment', 'give'},
    'mtxq': {'tell', 'accept', 'obligation', 'take'}
}


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
    print("Validated {} and {}".format(unit, resource))
    return (unit_res['data'], resource_res['data'])


def __validate_utxq_exists(address):
    try:
        decode_from_leaf(address)
    except RestException:
        raise DataException


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
        request['quantity']['unit'], request['quantity']['resource'])
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
    unit_addr, resource_addr = quantity
    pass
    # return Quantity(
    #     value=value,
    #     valueUnit=unit,
    #     valueResource=resource)


def __create_utxq(ingest):
    """Create a utxq object"""
    operation, dimension, addresser, quantity, data = ingest
    # utxq = UTXQ(
    #     plus=valid_signer(data['plus']),
    #     minus=valid_signer(data['minus']),
    #     quantity=__create_quantity(data['value'], quantity)
    #     )
    pass


def __create_mtxq(ingest):
    # mtxq = MTXQ()
    pass


def create_utxq(operation, request):
    """Create utxq transaction"""
    q = __validate_utxq(request)
    # Creaate utxq
    # Create payload
    # Create inputs/outputs
    # Create transaction
    # Create batch

    pass


def create_mtxq(operation, request):
    """Create mtxq transaction"""
    qnd = __validate_mtxq(request)
    # Creaate mtxq
    # Create payload
    # Create inputs/outputs
    # Create transaction
    # Create batch
    pass
