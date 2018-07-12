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

from modules.exceptions import DataException
from modules.hashblock_zksnark import prime_gen
from modules.config import valid_signer
from modules.decode import (
    asset_addresser, unit_addresser,
    decode_unit_list, decode_asset_list, decode_proposals)

from protobuf.asset_pb2 import (
    AssetPayload, AssetProposal, AssetVote, Asset, Property)

from protobuf.unit_pb2 import (
    UnitPayload, UnitProposal, UnitVote, Unit)

ASSET_KEY_SET = {'signer', 'key', 'system'}
UNIT_KEY_SET = {'signer', 'key', 'system'}
VOTE_KEY_SET = {'signer', 'proposal_id', 'vote'}
VOTE_SET = {'accept', 'reject', 'rescind'}
VOTE_ITEMS = ['rescind', 'accept', 'reject']


ASSET_ADDRESSER = asset_addresser
UNIT_ADDRESSER = unit_addresser


def __get_prime():
    return prime_gen().decode().lower()


def __fail_if_exists(address, alist, data):
    """Exception if asset already exists"""
    if alist:
        prime_list = [
            t['value'] for t in alist['data']
            if t['value'] == data or t['link'] == address]
        if prime_list:
            raise DataException("Have result {}".format(prime_list))


def __validate_signer(signer):
    """Exception if signer not provided or not resolved"""
    if not signer:
        raise DataException("Missing signer value")
    valid_signer(signer)


def __validate_element(key_set, data, gen_prime=False):
    if not key_set <= data.keys():
        raise DataException(
            "Keys {} are not in expected keys {}".format(data.keys(), key_set))
    __validate_signer(data['signer'])
    if gen_prime:
        return __get_prime()
    else:
        pass


def __validate_proposal(addresser, key_set, data, listFN):
    """Validate the proposal being submitted"""
    prime_id = __validate_element(key_set, data, True)
    target_address = addresser.element_address(
        data['system'], data['key'], prime_id)
    __fail_if_exists(
        target_address,
        listFN(target_address),
        prime_id)
    return target_address


def __validate_asset_proposal(data, ignoreAddress=False):
    """Vaidate an asset proposal"""
    return __validate_proposal(
        ASSET_ADDRESSER,
        ASSET_KEY_SET,
        data,
        decode_asset_list)


def __validate_unit_proposal(data, ignoreAddress=False):
    """Validate a unit proposal"""
    return __validate_proposal(
        UNIT_ADDRESSER,
        UNIT_KEY_SET,
        data,
        decode_unit_list)


def __validate_vote(addr, data, ignoreAddress=False):
    """Validate the vote attempt"""
    if set(data.keys()) != VOTE_KEY_SET:
        raise DataException(
            "Keys mismatch {} {}".format(data.keys, VOTE_KEY_SET))
    __validate_signer(data['signer'])
    if not data['vote'] or data['vote'] not in VOTE_SET:
        raise DataException(
            "Vote not regognized {} {}".format(data['vote'], VOTE_SET))
    # Check proposal id exists
    proposal_id = data['proposal_id']
    result = decode_proposals(addr.candidate_address)['data']
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


def __validate_asset_vote(data, ignoreAddress=False):
    """Validate an asset vote"""
    return __validate_vote(ASSET_ADDRESSER, data, ignoreAddress)


def __validate_unit_vote(data, ignoreAddress=False):
    """Validate a unit vote"""
    return __validate_vote(UNIT_ADDRESSER, data, ignoreAddress)


def property_list_generalize(intake):
    if "properties" in intake:
        intake["properties"] = \
            {d['name']: d['value'] for d in intake["properties"]}
    return intake


def __property_list(data):
    """Extract properties, if they exist to Property"""
    return [Property(
        name=x.encode(),
        value=y.encode()) for (x, y) in data["properties"].items()] \
        if "properties" in data else []


def __create_asset(ingest):
    """Create a asset"""
    signatore, proposal_id, address, data = ingest
    return (signatore, proposal_id, address, Asset(
        system=data['system'],
        key=data['key'],
        value=proposal_id[-44:],
        properties=__property_list(property_list_generalize(data))))


def __create_unit(ingest):
    """Create a unif-of-measure"""
    signatore, proposal_id, address, data = ingest
    return (signatore, proposal_id, address, Unit(
        system=data['system'],
        key=data['key'],
        value=proposal_id[-44:]))


def __create_asset_proposal(ingest):
    """Create an asset proposal and payload"""
    signatore, proposal_id, address, asset = ingest
    proposal = AssetProposal(
        asset=asset.SerializeToString(),
        nonce=str(datetime.datetime.utcnow().timestamp()))

    return (signatore, proposal_id, address, asset, AssetPayload(
        data=proposal.SerializeToString(),
        action=AssetPayload.ACTION_PROPOSE))


def __create_unit_proposal(ingest):
    """Create an unit proposal and payload"""
    signatore, proposal_id, address, unit = ingest
    proposal = UnitProposal(
        unit=unit.SerializeToString(),
        nonce=str(datetime.datetime.utcnow().timestamp()))

    return (signatore, proposal_id, address, unit, UnitPayload(
        data=proposal.SerializeToString(),
        action=UnitPayload.ACTION_PROPOSE))


def __create_asset_vote(ingest):
    """Create a asset vote"""
    signatore, address, data = ingest
    proposal_id = data['proposal_id']
    return (signatore, address, proposal_id, AssetVote(
        proposal_id=proposal_id,
        vote=VOTE_ITEMS.index(data['vote'])))


def __create_unit_vote(ingest):
    """Create a unit vote"""
    signatore, address, data = ingest
    proposal_id = data['proposal_id']
    return (signatore, address, proposal_id, UnitVote(
        proposal_id=proposal_id,
        vote=VOTE_ITEMS.index(data['vote'])))


def __create_asset_vote_payload(ingest):
    """Create an asset vote payload"""
    signatore, address, prop_id, vote = ingest
    if vote.vote == AssetVote.VOTE_UNSET:
        action = AssetPayload.ACTION_UNSET
    else:
        action = AssetPayload.ACTION_VOTE
    return (signatore, address, prop_id, AssetPayload(
        data=vote.SerializeToString(),
        action=action))


def __create_unit_vote_payload(ingest):
    """Create an unit vote payload"""
    signatore, address, prop_id, vote = ingest
    if vote.vote == UnitVote.VOTE_UNSET:
        action = UnitPayload.ACTION_UNSET
    else:
        action = UnitPayload.ACTION_VOTE
    return (signatore, address, prop_id, UnitPayload(
        data=vote.SerializeToString(),
        action=action))


def __create_asset_genesis_payload(ingest):
    signatore, proposal_id, address, asset = ingest
    return (signatore, proposal_id, address, AssetPayload(
        data=asset.SerializeToString(),
        action=AssetPayload.ACTION_GENESIS))


def __create_unit_genesis_payload(ingest):
    signatore, proposal_id, address, unit = ingest
    return (signatore, proposal_id, address, UnitPayload(
        data=unit.SerializeToString(),
        action=UnitPayload.ACTION_GENESIS))


def __create_asset_direct_payload(ingest):
    signatore, proposal_id, address, asset = ingest
    return (signatore, proposal_id, address, AssetPayload(
        data=asset.SerializeToString(),
        action=AssetPayload.ACTION_DIRECT))


def __create_unit_direct_payload(ingest):
    signatore, proposal_id, address, unit = ingest
    return (signatore, proposal_id, address, UnitPayload(
        data=unit.SerializeToString(),
        action=UnitPayload.ACTION_DIRECT))


def __create_inputs_outputs(ingest):
    signatore, proposal_id, address, payload = ingest
    inputs = [
        proposal_id,
        address.setting_address]
    outputs = [proposal_id]
    return (
        signatore, address, {"inputs": inputs, "outputs": outputs}, payload)


def __create_proposal_inputs_outputs(ingest):
    """Create asset transaction inputs and outputs"""
    signatore, proposal_id, address, data, payload = ingest
    inputs = [
        proposal_id,
        address.candidate_address,
        address.setting_address]
    outputs = [
        proposal_id,
        address.candidate_address]
    return (
        signatore, address, {"inputs": inputs, "outputs": outputs}, payload)


def __create_vote_inputs_outputs(ingest):
    """Create asset transaction inputs and outputs"""
    signatore, address, prop_id, payload = ingest
    inputs = [
        prop_id,
        address.candidate_address,
        address.setting_address]
    outputs = [
        prop_id,
        address.candidate_address]
    return (
        signatore, address, {"inputs": inputs, "outputs": outputs}, payload)


def create_asset_proposal(data):
    """Create a asset proposal"""
    proposal_id = __validate_asset_proposal(data)
    # Creaate asset
    # Create proposal payload
    # Create inputs/outputs
    # Create transaction
    # Create batch
    propose = compose_builder(
        submit_single_txn, create_transaction,
        __create_proposal_inputs_outputs, __create_asset_proposal,
        __create_asset)
    propose((
        data['signer'],
        proposal_id,
        ASSET_ADDRESSER,
        data))
    return proposal_id


def create_unit_proposal(data):
    """Create a asset proposal"""
    proposal_id = __validate_unit_proposal(data)
    # Creaate unit
    # Create proposal payload
    # Create inputs/outputs
    # Create transaction
    # Create batch
    propose = compose_builder(
        submit_single_txn, create_transaction,
        __create_proposal_inputs_outputs, __create_unit_proposal,
        __create_unit)
    propose((
        data['signer'],
        proposal_id,
        UNIT_ADDRESSER,
        data))
    return proposal_id


def create_asset_vote(data):
    """Vote on an asset proposal"""
    __validate_asset_vote(data)
    # Create asset vote
    # Create vote payload
    # Create inputs/outputs
    # Create transaction
    # Create batch
    vote = compose_builder(
        submit_single_txn, create_transaction,
        __create_vote_inputs_outputs, __create_asset_vote_payload,
        __create_asset_vote)
    vote((data['signer'], ASSET_ADDRESSER, data))


def create_unit_vote(data):
    """Vote on an unit proposal"""
    __validate_unit_vote(data)
    # Create unit vote
    # Create vote payload
    # Create inputs/outputs
    # Create transaction
    # Create batch
    vote = compose_builder(
        submit_single_txn, create_transaction,
        __create_vote_inputs_outputs, __create_unit_vote_payload,
        __create_unit_vote)
    vote((data['signer'], UNIT_ADDRESSER, data))


def create_direct_asset(data):
    prime_id = __validate_element(ASSET_KEY_SET, data, True)
    direct = compose_builder(
        submit_single_txn, create_transaction, __create_inputs_outputs,
        __create_asset_direct_payload, __create_asset)
    direct((
        data['signer'],
        ASSET_ADDRESSER.asset_address(
            data['system'], data['key'], prime_id),
        ASSET_ADDRESSER,
        data))
    return prime_id


def create_direct_unit(data):
    prime_id = __validate_element(UNIT_KEY_SET, data, True)
    direct = compose_builder(
        submit_single_txn, create_transaction, __create_inputs_outputs,
        __create_unit_direct_payload, __create_unit)
    direct((
        data['signer'],
        UNIT_ADDRESSER.unit_address(
            data['system'], data['key'], prime_id),
        UNIT_ADDRESSER,
        data))
    return prime_id


def create_unit_genesis(signer, unit_list):
    """Generate the transaction batch for genesis block units of measure"""
    txns = []
    genesis = compose_builder(
        create_transaction, __create_inputs_outputs,
        __create_unit_genesis_payload, __create_unit)
    for data in unit_list:
        data["signer"] = signer
        prime_id = data.pop("prime")
        if not prime_id:
            prime_id = __validate_element(UNIT_KEY_SET, data, True)
        else:
            __validate_element(UNIT_KEY_SET, data)
        txns.append(
            genesis((
                signer,
                UNIT_ADDRESSER.unit_address(
                    data['system'], data['key'], prime_id),
                UNIT_ADDRESSER,
                data))[1])
    return txns


def create_asset_genesis(signer, asset_list):
    """Generate the transaction batch for genesis block assets"""
    txns = []
    genesis = compose_builder(
        create_transaction, __create_inputs_outputs,
        __create_asset_genesis_payload, __create_asset)
    for data in asset_list:
        data["signer"] = signer
        prime_id = data.pop("prime")
        if not prime_id:
            prime_id = __validate_element(ASSET_KEY_SET, data, True)
        else:
            __validate_element(ASSET_KEY_SET, data)
        txns.append(
            genesis((
                signer,
                ASSET_ADDRESSER.asset_address(
                    data['system'], data['key'], prime_id),
                ASSET_ADDRESSER,
                data))[1])
    return txns


def create_asset_unit_batch(json_file):
    """Consume a batch of json asset entities"""

    # Proposal boilerplates
    propose_unit = compose_builder(
        create_transaction,
        __create_proposal_inputs_outputs, __create_unit_proposal,
        __create_unit)
    propose_asset = compose_builder(
        create_transaction,
        __create_proposal_inputs_outputs, __create_asset_proposal,
        __create_asset)

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
        dimension = asset.pop('type')
        accum.append(dimension)
        if dimension == 'asset':
            proposal_id = __validate_asset_proposal(asset)
            fn = propose_asset
            addy = asset_addresser
        else:
            proposal_id = __validate_unit_proposal(asset)
            fn = propose_unit
            addy = unit_addresser
        accum.append(proposal_id)
        _, txq = fn((
            asset['signer'],
            proposal_id,
            addy,
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
        asset_vote = compose_builder(
            create_transaction,
            partial(create_dependency, dep=txq_id),
            __create_vote_inputs_outputs, __create_asset_vote_payload,
            __create_asset_vote)
        unit_vote = compose_builder(
            create_transaction,
            partial(create_dependency, dep=txq_id),
            __create_vote_inputs_outputs, __create_unit_vote_payload,
            __create_unit_vote)
        if dimension == 'asset':
            __validate_asset_vote(vote, True)
            fn = asset_vote
            addy = asset_addresser
        else:
            __validate_unit_vote(vote, True)
            fn = unit_vote
            addy = unit_addresser

        _, txq = fn((
            vote['signer'],
            addy,
            vote))
        vote_txns.append(txq)

    # Submit votes
    submit_batch([create_batch((voteSigner, vote_txns))])
