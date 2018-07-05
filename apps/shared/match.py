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
import os
import uuid
import binascii

from shared.transactions import (
    submit_single_txn, create_transaction, compose_builder)

from modules.address import Address
from modules.hashblock_zksnark import zksnark_genproof
from modules.config import (
    public_key, private_key,
    valid_partnership, partnership_secret)
from modules.decode import (
    asset_addresser,
    decode_asset_list,
    STATE_CRYPTO,
    get_utxq_obj_json)
from modules.exceptions import (
    AuthException, RestException, DataException, AssetNotExistException)
from protobuf.match_pb2 import (
    MatchEvent, UTXQ, MTXQ, Quantity, Ratio)

KEYS_PATH = os.environ['HASHBLOCK_KEYS'] + '/'
_utxq_addrs = Address.match_utxq_addresser()
_mtxq_addrs = Address.match_utxq_addresser()


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
    if valid_partnership(plus, minus):
        pass
    else:
        AuthException(
            "No partnership for {} and {}".format(plus, minus))


def __validate_assets(value, unit, resource):
    """Validate and return asset addresses that are reachable"""
    unit_result = None
    resource_result = None
    int(value)
    unit_add = asset_addresser.asset_item_syskey(
        Address.DIMENSION_UNIT,
        unit['system'], unit['key'])
    resource_add = asset_addresser.asset_item_syskey(
        Address.DIMENSION_RESOURCE,
        resource['system'], resource['key'])

    def in_list(ent, elist):
        result = None
        for el in elist['data']:
            if el['system'] == ent['system'] and el['name'] == ent['key']:
                el['value'] = str(int(el['value'], 16))
                result = el
                break
        return result

    unit_result = in_list(unit, decode_asset_list(unit_add))
    resource_result = in_list(resource, decode_asset_list(resource_add))

    if not unit_result or not resource_result:
        raise AssetNotExistException("Asset does not exist")

    return (unit_result, resource_result)


def __get_and_validate_utxq(address, secret):
    """Check that the utxq exists to recipricate on"""
    print("Address to check utxq {}".format(address[24]))
    if address[24] == '1':
        raise DataException(
            'Attempt to match on already matched transaction')
    try:
        utxq = get_utxq_obj_json(address, secret)
        return utxq
    except RestException:
        raise DataException('Invalid initiate (utxq) address')


def __validate_utxq(request):
    """Validate the content for utxq"""
    __validate_partners(request["plus"], request["minus"])
    quantity_assets = __validate_assets(
        request['quantity']['value'],
        request['quantity']['unit'],
        request['quantity']['resource'])
    return (quantity_assets)


def __validate_mtxq(request):
    """Validate the content for mtxq"""
    __validate_partners(request["plus"], request["minus"])
    utxq, json = __get_and_validate_utxq(
        request["utxq_address"],
        partnership_secret(request["plus"], request["minus"]))
    utxq_qblock = json['data']['quantity']
    quantity_assets = __validate_assets(
        request['quantity']['value'],
        request['quantity']['unit'],
        request['quantity']['resource'])
    numerator_assets = __validate_assets(
        request['ratio']['numerator']['value'],
        request['ratio']['numerator']['unit'],
        request['ratio']['numerator']['resource'])
    denominator_assets = __validate_assets(
        request['ratio']['denominator']['value'],
        request['ratio']['denominator']['unit'],
        request['ratio']['denominator']['resource'])
    data_tuple = []

    data_tuple.append(str(utxq_qblock['value']))
    data_tuple.append(request['ratio']['numerator']['value'])
    data_tuple.append(request['ratio']['denominator']['value'])
    data_tuple.append(request['quantity']['value'])

    data_tuple.append(str(utxq_qblock['unit']))
    data_tuple.append(numerator_assets[0]['value'])
    data_tuple.append(denominator_assets[0]['value'])
    data_tuple.append(quantity_assets[0]['value'])

    data_tuple.append(str(utxq_qblock['resource']))
    data_tuple.append(numerator_assets[1]['value'])
    data_tuple.append(denominator_assets[1]['value'])
    data_tuple.append(quantity_assets[1]['value'])
    data_str = ",".join(data_tuple)
    prf_pair = zksnark_genproof(KEYS_PATH, data_str)
    return (
        utxq,
        request["utxq_address"],
        quantity_assets,
        numerator_assets,
        denominator_assets,
        prf_pair)


def __create_quantity(value, quantity):
    """Converts a quantity type into byte string from prime number"""
    unit_data, resource_data = quantity
    return Quantity(
        value=int(value).to_bytes(len(value), byteorder='little'),
        unit=int(unit_data['value']).to_bytes(
            len(unit_data['value']), byteorder='little'),
        resource=int(resource_data['value']).to_bytes(
            len(resource_data['value']), byteorder='little'))


def __create_utxq(ingest):
    """Create a utxq object"""
    operation, quantity, request = ingest
    return (operation, request, UTXQ(
        matched=False,
        plus=public_key(request['plus']).encode(),
        minus=public_key(request['minus']).encode(),
        quantity=__create_quantity(request['quantity']['value'], quantity)))


def __create_initiate_payload(ingest):
    """Create the utxq payload"""
    operation, request, data = ingest
    utxq_addr = _utxq_addrs.match2_initiate_unmatched(
        _utxq_addrs.dimension, operation, str(uuid.uuid4))
    encrypted = binascii.hexlify(
        STATE_CRYPTO.encrypt_from(
            data.SerializeToString(),
            private_key(request['plus']),
            public_key(request['minus'])))
    return (operation, request['plus'], MatchEvent(
        udata=encrypted,
        ukey=utxq_addr,
        action=_ACTION_MAP[operation]))


def __create_initiate_inputs_outputs(ingest):
    """Create utxq address (state) authorizations"""
    operation, signer, payload = ingest
    inputs = []
    outputs = [payload.ukey]
    return (
        signer, _utxq_addrs, {"inputs": inputs, "outputs": outputs}, payload)


def __create_mtxq(ingest):
    """Create the mtxq object"""
    operation, qassets, data = ingest
    utxq, uaddr, quantity, numerator, denominator, prf_pair = qassets
    # mtxq = MTXQ()
    utxq.matched = True
    return (operation, utxq, uaddr, prf_pair, data, MTXQ(
        plus=public_key(data['plus']).encode(),
        minus=public_key(data['minus']).encode(),
        quantity=__create_quantity(data['quantity']['value'], quantity),
        ratio=Ratio(
            numerator=__create_quantity(
                data['ratio']['numerator']['value'], numerator),
            denominator=__create_quantity(
                data['ratio']['denominator']['value'], denominator)),
        utxq_addr=_mtxq_addrs.set_utxq_matched(uaddr).encode()))


def __create_reciprocate_payload(ingest):
    """Create the mtxq payload"""
    operation, utxq, uaddr, prf_pair, request, payload = ingest
    proof, pairing = prf_pair
    e_utxq = binascii.hexlify(
        STATE_CRYPTO.encrypt_from(
            utxq.SerializeToString(),
            private_key(request['plus']),
            public_key(request['minus'])))
    e_mtxq = binascii.hexlify(
        STATE_CRYPTO.encrypt_from(
            payload.SerializeToString(),
            private_key(request['plus']),
            public_key(request['minus'])))
    return (operation, uaddr, request['plus'], MatchEvent(
        action=_ACTION_MAP[operation],
        ukey=_mtxq_addrs.set_utxq_matched(uaddr),
        mkey=_mtxq_addrs.txq_item(
            _mtxq_addrs.dimension, operation, str(uuid.uuid4)),
        mdata=e_mtxq,
        udata=e_utxq,
        pairings=pairing.encode(),
        proof=proof.encode()))


def __create_reciprocate_inputs_outputs(ingest):
    """Create mtxq address (state) authorizations"""
    operation, uaddr, signer, payload = ingest
    inputs = [uaddr, payload.ukey]
    outputs = [payload.ukey, payload.mkey]
    return (
        signer, _mtxq_addrs, {"inputs": inputs, "outputs": outputs}, payload)


def create_utxq(operation, request):
    """Create utxq transaction"""
    quant = __validate_utxq(request)
    utxq_build = compose_builder(
        submit_single_txn, create_transaction,
        __create_initiate_inputs_outputs, __create_initiate_payload,
        __create_utxq)
    utxq_build((operation, quant, request))


def create_mtxq(operation, request):
    """Create mtxq transaction"""
    qnd = __validate_mtxq(request)
    mtxq_build = compose_builder(
        submit_single_txn, create_transaction,
        __create_reciprocate_inputs_outputs, __create_reciprocate_payload,
        __create_mtxq)
    mtxq_build((operation, qnd, request))
