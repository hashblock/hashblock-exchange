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
from functools import partial
from shared.transactions import (
    create_batch, submit_batch,
    submit_single_txn, create_transaction, compose_builder)
from modules.hashblock_zksnark import prime_gen
from modules.address import Address
from modules.config import valid_signer
from modules.decode import decode_asset_unit_list, decode_proposals
from modules.exceptions import DataException

from protobuf.asset_pb2 import (
    AssetPayload, AssetProposal, AssetVote, Asset)

from protobuf.unit_pb2 import (
    UnitPayload, UnitProposal, UnitVote, Unit)

ASSET_KEY_SET = {'signer', 'key', 'system'}
VOTE_KEY_SET = {'signer', 'proposal_id', 'vote'}
VOTE_SET = {'accept', 'reject', 'rescind'}
VOTE_ITEMS = ['rescind', 'accept', 'reject']


_addresser = Address.asset_addresser()


def __get_prime():
    return prime_gen().decode().lower()


def __validate_asset(address, alist, data):
    """Exception if asset already exists"""
    if alist:
        prime_list = [
            t['value'] for t in alist['data']
            if t['value'] == data or t['link'] == address]
        if prime_list:
            raise DataException("Have result {}".format(prime_list))


def __validate_proposal(dimension, data):
    """Validate the proposal being submitted"""
    if set(data.keys()) != ASSET_KEY_SET:
        raise DataException("{} not in {}".format(data.keys(), ASSET_KEY_SET))
    if not data['signer']:
        raise DataException("Missing signer for proposal")
    valid_signer(data['signer'])
    prime_id = __get_prime()
    target_address = _addresser.asset_item(
        dimension, data['system'], data['key'], prime_id)
    __validate_asset(
        target_address,
        decode_asset_unit_list(_addresser.asset_prefix(dimension)),
        prime_id)
    return target_address


def __validate_vote(dimension, data, ignoreAddress=False):
    """Validate the vote content"""
    if set(data.keys()) != VOTE_KEY_SET:
        raise DataException(
            "Keys mismatch {} {}".format(data.keys, VOTE_KEY_SET))
    if not data['signer']:
        raise DataException("No signer value")
    valid_signer(data['signer'])
    if not data['vote'] or data['vote'] not in VOTE_SET:
        raise DataException(
            "Vote not regognized {} {}".format(data['vote'], VOTE_SET))
    # Check proposal id exists
    proposal_id = data['proposal_id']
    result = decode_proposals(
        _addresser.candidates(dimension))['data']
    if result:
        proposal_match = []
        for x in result:
            if x['proposalId'] == proposal_id:
                proposal_match.append(x['proposalId'])
                break
        if not proposal_match:
            raise DataException("No match for id {}".format(proposal_id))
    elif not ignoreAddress:
        raise DataException("No result for proposals")
    else:
        pass


def __create_asset_vote(ingest):
    """Create a vote for an asset"""
    signatore, address, data = ingest
    proposal_id = data['proposal_id']
    return (signatore, address, proposal_id, AssetVote(
        proposal_id=proposal_id,
        vote=VOTE_ITEMS.index(data['vote'])))


def __create_resource_asset(ingest):
    """Create a resource asset unit"""
    signatore, proposal_id, address, data = ingest
    return (signatore, proposal_id, address, Asset(
        system=data['system'],
        key=data['key'],
        value=proposal_id[-44:]))


def __create_unit_asset(ingest):
    """Create a unif-of-measure asset unit"""
    signatore, proposal_id, address, data = ingest
    return (signatore, proposal_id, address, Unit(
        system=data['system'],
        key=data['key'],
        value=proposal_id[-44:]))


def __create_propose_txn(ingest):
    """Create an asset proposal and payload"""
    signatore, proposal_id, address, asset = ingest
    nonce = str(datetime.datetime.utcnow().timestamp())
    proposal = AssetProposal(
        type=AssetProposal.UNIT
        if address.dimension == Address.DIMENSION_UNIT
        else AssetProposal.RESOURCE,
        asset=asset.SerializeToString(),
        nonce=nonce)

    return (signatore, proposal_id, address, asset, AssetPayload(
        data=proposal.SerializeToString(),
        dimension=address.dimension,
        action=AssetPayload.ACTION_PROPOSE))


def __create_vote_txn(ingest):
    """Create an asset proposal and payload"""
    signatore, address, prop_id, vote = ingest
    if vote.vote == AssetVote.VOTE_UNSET:
        action = AssetPayload.ACTION_UNSET
    else:
        action = AssetPayload.ACTION_VOTE
    return (signatore, address, prop_id, AssetPayload(
        data=vote.SerializeToString(),
        dimension=address.dimension,
        action=action))


def __create_asset_payload(ingest):
    signatore, proposal_id, address, asset = ingest
    return (signatore, proposal_id, address, AssetPayload(
        data=asset.SerializeToString(),
        dimension=address.dimension,
        action=AssetPayload.ACTION_GENESIS))


def __create_asset_inputs_outputs(ingest):
    signatore, proposal_id, address, payload = ingest
    inputs = [
        proposal_id,
        Address(Address.FAMILY_SETTING).settings(address.dimension)]
    outputs = [proposal_id]
    return (
        signatore, address, {"inputs": inputs, "outputs": outputs}, payload)


def __create_proposal_inputs_outputs(ingest):
    """Create asset transaction inputs and outputs"""
    signatore, proposal_id, address, asset, payload = ingest
    candidate_addr = address.candidates(address.dimension)
    inputs = [
        proposal_id,
        candidate_addr,
        Address(Address.FAMILY_SETTING).settings(address.dimension)]
    outputs = [
        proposal_id,
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
        submit_single_txn, create_transaction,
        __create_proposal_inputs_outputs, __create_propose_txn,
        __create_resource_asset
        if dimension == Address.DIMENSION_RESOURCE else __create_unit_asset)
    propose((
        data['signer'],
        proposal_id,
        Address(Address.FAMILY_ASSET, "0.2.0", dimension),
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
        submit_single_txn, create_transaction,
        __create_vote_inputs_outputs, __create_vote_txn,
        __create_asset_vote)
    vote((
        data['signer'],
        Address(Address.FAMILY_ASSET, "0.2.0", dimension),
        data))


def create_asset_genesis(signer, unit_list):
    """Generate the transaction batch for genesis block unit assets"""
    txns = []
    genesis = compose_builder(
        create_transaction, __create_asset_inputs_outputs,
        __create_asset_payload, __create_unit_asset)
    for data in unit_list:
        if data["prime"]:
            proposal_id = data.pop("prime")
        else:
            proposal_id = __get_prime()
        txns.append(
            genesis((
                signer,
                _addresser.asset_item(
                    "unit", data['system'], data['key'], proposal_id),
                Address(Address.FAMILY_ASSET, "0.2.0", "unit"),
                data))[1])
    return txns


def create_asset_batch(json_file):
    """Consume a batch of json asset entities"""

    # Proposal boilerplates
    propose_unit = compose_builder(
        create_transaction,
        __create_proposal_inputs_outputs, __create_propose_txn,
        __create_unit_asset)
    propose_resource = compose_builder(
        create_transaction,
        __create_proposal_inputs_outputs, __create_propose_txn,
        __create_resource_asset)

    # proposal entries {asset_id: [dimension, proposal_id, prop_txq_id]}
    id_track = {}
    # Holds transactions
    prop_txns = []
    # Proposal signer
    propSigner = None
    # Read in the file
    with open(json_file) as data_file:
        try:
            data = json.loads(data_file.read())
        except ValueError as error:
            raise DataException('Error in json read {}'.format(error))

    # Loop through the proposals, collecting data points
    for asset in data['proposals']:
        accum = []
        fn = None
        if not propSigner:
            propSigner = asset['signer']
        asset_id = asset.pop('id')
        if asset_id in id_track:
            raise DataException("Duplicate proposal.id found")
        dimension = asset.pop('dimension')
        accum.append(dimension)
        proposal_id = __validate_proposal(dimension, asset)
        accum.append(proposal_id)
        fn = propose_unit \
            if dimension == Address.DIMENSION_UNIT else propose_resource
        _, txq = fn((
            asset['signer'],
            proposal_id,
            Address(Address.FAMILY_ASSET, "0.2.0", dimension),
            asset))
        prop_txns.append(txq)
        accum.append(txq.header_signature)
        id_track[asset_id] = accum

    # Submit proposals
    submit_batch([create_batch((propSigner, prop_txns))])

    # Vote signer
    voteSigner = None
    # Vote transactions
    vote_txns = []

    def create_dependency(ingest, dep):
        """Imbue asset permissions with dependency"""
        signatore, address, permissions, payload = ingest
        permissions['dependencies'] = [dep]
        return (signatore, address, permissions, payload)

    for vote in data['votes']:
        if not voteSigner:
            voteSigner = vote['signer']
        dimension, prop_id, txq_id = id_track[vote.pop('proposal_id')]
        vote['proposal_id'] = prop_id
        __validate_vote(dimension, vote, True)
        asset_vote = compose_builder(
            create_transaction,
            partial(create_dependency, dep=txq_id),
            __create_vote_inputs_outputs, __create_vote_txn,
            __create_asset_vote)
        _, txq = asset_vote((
            vote['signer'],
            Address(Address.FAMILY_ASSET, "0.2.0", dimension),
            vote))
        vote_txns.append(txq)

    # Submit proposals
    submit_batch([create_batch((voteSigner, vote_txns))])
