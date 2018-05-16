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

from sawtooth_processor_test.message_factory import MessageFactory
from protobuf.asset_pb2 import AssetProposal
from protobuf.asset_pb2 import AssetVote
from protobuf.asset_pb2 import AssetPayload

from modules.address import Address

LOGGER = logging.getLogger(__name__)


class AssetMessageFactory(object):
    def __init__(self, signer=None):
        self._asset_addr = Address(Address.FAMILY_ASSET)
        self._setting_addr = Address(Address.FAMILY_SETTING)
        self._factory = MessageFactory(
            family_name=Address.NAMESPACE_ASSET,
            family_version="0.1.0",
            namespace=[self._asset_addr.ns_family],
            signer=signer)

    @property
    def public_key(self):
        return self._factory.get_public_key()

    def create_tp_register(self):
        return self._factory.create_tp_register()

    def create_tp_response(self, status):
        return self._factory.create_tp_response(status)

    def _create_tp_process_request(self, asset, dimension, payload):
        asset_address = self._asset_addr.asset_item(
            dimension,
            asset.system,
            asset.key)
        inputs = [
            self._setting_addr.settings(dimension),
            self._asset_addr.candidates(dimension),
            asset_address
        ]

        outputs = [
            self._asset_addr.candidates(dimension),
            asset_address
        ]

        return self._factory.create_tp_process_request(
            payload.SerializeToString(), inputs, outputs, [])

    def create_proposal_transaction(self, asset, dimension, nonce):
        proposal = AssetProposal(
            asset=asset.SerializeToString(),
            type=AssetProposal.UNIT
            if dimension is Address.DIMENSION_UNIT
            else AssetProposal.RESOURCE,
            nonce=nonce)
        payload = AssetPayload(
            action=AssetPayload.ACTION_PROPOSE,
            dimension=dimension,
            data=proposal.SerializeToString())

        return self._create_tp_process_request(asset, dimension, payload)

    def create_vote_transaction(self, proposal_id, asset, dimension, vote):
        avote = AssetVote(
            proposal_id=proposal_id,
            vote=vote)
        payload = AssetPayload(
            action=AssetPayload.ACTION_VOTE,
            dimension=dimension,
            data=avote.SerializeToString())

        return self._create_tp_process_request(asset, dimension, payload)

    def create_unset_vote_transaction(
            self, proposal_id, asset, dimension, vote):
        avote = AssetVote(
            proposal_id=proposal_id,
            vote=vote)
        payload = AssetPayload(
            action=AssetPayload.ACTION_UNSET,
            dimension=dimension,
            data=avote.SerializeToString())

        return self._create_tp_process_request(asset, dimension, payload)

    def create_get_request(self, address):
        addresses = [address]
        return self._factory.create_get_request(addresses)

    def create_get_response(self, address, data):
        return self._factory.create_get_response({address: data})

    def create_set_request(self, address, data):
        return self._factory.create_set_request({address: data})

    def create_set_response(self, address):
        addresses = [address]
        return self._factory.create_set_response(addresses)

    def create_add_event_request(self, address):
        return self._factory.create_add_event_request(
            "hashbloc.asset/update",
            [("updated", address)])

    def create_add_event_response(self):
        return self._factory.create_add_event_response()
