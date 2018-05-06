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

"""asset - Asset business logic

This module is referenced when posting asset proposals and votes
"""
import datetime
import json
import time
from pprint import pprint
from math import sqrt
from itertools import count, islice
from shared.transactions import submit_single_batch, create_single_batch
from shared.transactions import create_single_transaction, compose_builder
from modules.address import Address
from modules.config import valid_signer
from modules.decode import decode_asset_unit_list, decode_proposals
from modules.exceptions import DataException, NotPrimeException

from protobuf.asset_pb2 import AssetPayload
from protobuf.asset_pb2 import AssetProposal
from protobuf.asset_pb2 import AssetVote
from protobuf.asset_pb2 import Unit
from protobuf.asset_pb2 import Resource


ASSET_KEY_SET = {'signer', 'key', 'value', 'system'}
VOTE_KEY_SET = {'signer', 'proposal_id', 'vote'}
VOTE_SET = {'accept', 'reject', 'rescind'}
VOTE_ITEMS = ['rescind', 'accept', 'reject']

# {
#     'action': 'ask',
#     'plus': 'turing',
#     'minus': 'church',
#     'quantity': {
#         'value': '5',
#         'resource': 'food.peanuts',
#         'unit': 'imperial.bags'
#     }
# }

_addresser = Address(Address.FAMILY_ASSET, "0.1.0")


def __isPrime(n):
    """Validate number is prime"""
    if n == 1:
        return True
    else:
        return all(n % i for i in islice(count(2), int(sqrt(n) - 1)))


def __validate_asset(address, alist, data):
    """Exception if asset already exists"""
    data_value = data['value']
    if alist:
        prime_list = [
            t['value'] for t in alist['data']
            if t['value'] == data_value or t['link'] == address]
        if prime_list:
            raise DataException


def __validate_proposal(dimension, data):
    """Validate the proposal being submitted"""
    print("Validating {} proposal {}".format(dimension, data))
    if set(data.keys()) != ASSET_KEY_SET:
        raise DataException
    if not data['signer']:
        raise DataException
    valid_signer(data['signer'])
    if not __isPrime(int(data['value'])):
        raise NotPrimeException

    target_address = _addresser.asset_item(
        dimension, data['system'], data['key'])
    __validate_asset(
        target_address,
        decode_asset_unit_list(_addresser.asset_prefix(dimension)),
        data)
    return target_address


def __validate_vote(dimension, data):
    """Validate the vote content"""
    print("Validating {} vote {}".format(dimension, data))
    if set(data.keys()) != VOTE_KEY_SET:
        print("Keys mismatch {} {}".format(data.keys, VOTE_KEY_SET))
        raise DataException
    if not data['signer']:
        print("No signer value")
        raise DataException
    valid_signer(data['signer'])
    if not data['vote'] or data['vote'] not in VOTE_SET:
        print("Vote not regognized {} {}".format(data['vote'], VOTE_SET))
        raise DataException
    # Check proposal id exists
    proposal_id = data['proposal_id']
    result = decode_proposals(
        _addresser.candidates(dimension))['data']
    pprint(result)
    if result:
        proposal_match = []
        for x in result:
            if x['proposalId'] == proposal_id:
                proposal_match.append(x['proposalId'])
                break
        if not proposal_match:
            print("No match for id {}".format(proposal_id))
            raise DataException
    else:
        print("No result for proposals")
        raise DataException


def __create_asset_vote(ingest):
    """Create a vote for an asset"""
    signatore, address, data = ingest
    proposal_id = data['proposal_id']
    return (signatore, address, proposal_id, AssetVote(
        proposal_id=proposal_id,
        vote=VOTE_ITEMS.index(data['vote'])))


def __create_resource_asset(ingest):
    """Create a resource asset unit"""
    signatore, address, data = ingest
    return (signatore, address, Resource(
        system=data['system'],
        key=data['key'],
        value=data['value'],
        sku=''))


def __create_unit_asset(ingest):
    """Create a unif-of-measure asset unit"""
    signatore, address, data = ingest
    return (signatore, address, Unit(
        system=data['system'],
        key=data['key'],
        value=data['value']))


def __create_propose_txn(ingest):
    """Create an asset proposal and payload"""
    signatore, address, asset = ingest
    nonce = str(datetime.datetime.utcnow().timestamp())
    proposal = AssetProposal(
        type=AssetProposal.UNIT
        if address.dimension == Address.DIMENSION_UNIT
        else AssetProposal.RESOURCE,
        asset=asset.SerializeToString(),
        nonce=nonce)

    print("Proposal = {}".format(proposal))
    return (signatore, address, asset, AssetPayload(
        data=proposal.SerializeToString(),
        dimension=address.dimension,
        action=AssetPayload.ACTION_PROPOSE))


def __create_vote_txn(ingest):
    """Create an asset proposal and payload"""
    signatore, address, prop_id, vote = ingest
    print("Create vote payload for {}".format(vote))
    if vote.vote == AssetVote.VOTE_UNSET:
        action = AssetPayload.ACTION_UNSET
    else:
        action = AssetPayload.ACTION_VOTE
    return (signatore, address, prop_id, AssetPayload(
        data=vote.SerializeToString(),
        dimension=address.dimension,
        action=action))


def __create_proposal_inputs_outputs(ingest):
    """Create asset transaction inputs and outputs"""
    signatore, address, asset, payload = ingest
    asset_addr = address.asset_item(
        address.dimension, asset.system, asset.key)
    candidate_addr = address.candidates(address.dimension)
    inputs = [
        asset_addr,
        candidate_addr,
        Address(Address.FAMILY_SETTING).settings(address.dimension)]
    outputs = [
        asset_addr,
        candidate_addr]
    return (
        signatore, address, {"inputs": inputs, "outputs": outputs}, payload)


def __create_vote_inputs_outputs(ingest):
    """Create asset transaction inputs and outputs"""
    signatore, address, prop_id, payload = ingest
    candidate_addr = address.candidates(address.dimension)
    inputs = [
        prop_id,
        candidate_addr,
        Address(Address.FAMILY_SETTING).settings(address.dimension)]
    outputs = [
        prop_id,
        candidate_addr]
    return (
        signatore, address, {"inputs": inputs, "outputs": outputs}, payload)


def create_proposal(dimension, data):
    """Create a asset proposal"""
    proposal_id = __validate_proposal(dimension, data)
    # Creaate asset
    # Create proposal payload
    # Create inputs/outputs
    # Create transaction
    # Create batch
    propose = compose_builder(
        submit_single_batch, create_single_batch, create_single_transaction,
        __create_proposal_inputs_outputs, __create_propose_txn,
        __create_resource_asset
        if dimension == Address.DIMENSION_RESOURCE else __create_unit_asset)
    propose((
        data['signer'],
        Address(Address.FAMILY_ASSET, "0.1.0", dimension),
        data))
    return proposal_id


def create_vote(dimension, data):
    """Vote on an asset proposal"""
    __validate_vote(dimension, data)
    # Creaate asset
    # Create vote payload
    # Create inputs/outputs
    # Create transaction
    # Create batch
    vote = compose_builder(
        submit_single_batch, create_single_batch, create_single_transaction,
        __create_vote_inputs_outputs, __create_vote_txn,
        __create_asset_vote)
    vote((
        data['signer'],
        Address(Address.FAMILY_ASSET, "0.1.0", dimension),
        data))


def create_asset_batch(json_file):
    """Consume a batch of json entities and convert to assets"""
    id_track = {}
    with open(json_file) as data_file:
        data = json.loads(data_file.read())
    for asset in data['proposals']:
        asset_id = asset['id']
        dimension = asset['dimension']
        if id_track.get(asset_id, None):
            raise DataException
        id_track[asset['id']] = (dimension, _addresser.asset_item(
            asset['dimension'], asset['system'], asset['key']))
        del asset['id']
        del asset['dimension']
        create_proposal(dimension, asset)

    time.sleep(5)
    for vote in data['votes']:
        dimension, prop_id = id_track[vote['proposal_id']]
        vote['proposal_id'] = prop_id
        create_vote(dimension, vote)
