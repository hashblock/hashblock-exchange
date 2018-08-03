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

"""validator-client - ZMQ wrapper to validator

This supports the interaction (state/batch/etc) to validator
using ZMQ versus going through REST-API
"""

import asyncio
import logging

from zmq.asyncio import ZMQEventLoop
from sawtooth_sdk.protobuf import (
    client_state_pb2, client_batch_submit_pb2)
from sawtooth_sdk.protobuf.validator_pb2 import Message
from google.protobuf.json_format import MessageToDict
from google.protobuf.message import DecodeError

from shared.messaging import (
    Connection, DisconnectError, SendBackoffTimeoutError)

LOGGER = logging.getLogger(__name__)


class ValidatorDisconnected(Exception):
    pass


class SendBackoffTimeout(Exception):
    pass


class ValidatorTimedOut(Exception):
    pass


class ValidatorResponseInvalid(Exception):
    pass


class CountInvalid(Exception):
    pass


class Validator(object):
    _connection = None

    def __init__(self, url):
        if not Validator._connection:
            self._url = url
            self._loop = ZMQEventLoop()
            asyncio.set_event_loop(self._loop)
            Validator._connection = Connection(self._url)
            Validator._connection.open()

    def _check_status_errors(self, proto, content, etraps=None):
        pass

    def _message_to_dict(self, message):
        """Converts a Protobuf object to a python dict with desired settings.
        """
        return MessageToDict(
            message,
            including_default_value_fields=True,
            preserving_proto_field_name=True)

    def _parse_response(self, proto, response):
        """Parses the content from a validator response Message."""
        try:
            content = proto()
            content.ParseFromString(response.content)
            return content
        except (DecodeError, AttributeError):
            LOGGER.error('Validator response was not parsable: %s', response)
            raise ValidatorResponseInvalid()

    def _get_paging_controls(self, start=None, limit=300):
        """Parses start and/or limit queries into a paging controls dict."""
        controls = {}

        if limit is not None:
            try:
                controls['limit'] = int(limit)
            except ValueError:
                print('Request query had an invalid limit: %s', limit)
                raise CountInvalid()

            if controls['limit'] <= 0:
                print('Request query had an invalid limit: %s', limit)
                raise CountInvalid()

        if start is not None:
            controls['start'] = start

        return controls

    async def _send_request(self, request_type, payload):
        """Uses an executor to send an asynchronous ZMQ request to the
        validator with the handler's Connection
        """
        print("In _send_request")
        try:
            return await self._connection.send(
                message_type=request_type,
                message_content=payload,
                timeout=100)
        except DisconnectError:
            LOGGER.warning('Validator disconnected while waiting for response')
            raise ValidatorDisconnected()
        except asyncio.TimeoutError:
            LOGGER.warning('Timed out while waiting for validator response')
            raise ValidatorTimedOut()
        except SendBackoffTimeoutError:
            LOGGER.warning('Failed sending message - Backoff timed out')
            raise SendBackoffTimeout()

    async def _query_validator(
        self, request_type, response_proto, payload, error_traps=None):
        """Sends a request to the validator and parses the response."""

        print('Sending %s request to validator {}'.format(request_type))

        payload_bytes = payload.SerializeToString()
        response = await self._send_request(request_type, payload_bytes)
        content = self._parse_response(response_proto, response)

        # LOGGER.debug(
        #     'Received %s response from validator with status %s',
        #     self._get_type_name(response.message_type),
        #     self._get_status_name(response_proto, content.status))

        self._check_status_errors(response_proto, content, error_traps)
        return self._message_to_dict(content)

    async def _state_leaf(self, addy):
        """Fetches data from a specific address in the validator's state tree.
        Request:
            query:
                - head: The id of the block to use as the head of the chain
                - address: The 70 character address of the data to be fetched
        Response:
            entries: An array of 1 map [{data:, address:}]
        """

        validator_query = client_state_pb2.ClientStateGetRequest(
            state_root=None,
            address=addy)

        response = await self._query_validator(
            Message.CLIENT_STATE_GET_REQUEST,
            client_state_pb2.ClientStateGetResponse,
            validator_query)

        return {'address': addy, 'data': response['value']}

    def get_state_leaf(self, address):
        """Get a data leaf from state"""
        result = asyncio.get_event_loop().run_until_complete(
            self._state_leaf(address))
        return result

    async def _get_next(self, root=None, addy=None, paging=None):
        validator_query = client_state_pb2.ClientStateListRequest(
            state_root=root,
            address=addy,
            paging=paging)
        return await self._query_validator(
            Message.CLIENT_STATE_LIST_REQUEST,
            client_state_pb2.ClientStateListResponse,
            validator_query)

    async def _state_list(self, addy=None):
        """Fetches list of data entries, optionally filtered by address prefix.
        Request:
            - _connection: Sawtooth messaging.Connection
            - address: Return entries whose addresses begin with this prefix
        Response:
            entries: An array of maps [{data:, address:},...]
        """

        fetch_more = True
        entries = []
        paging_controls = self._get_paging_controls()
        print("List request with starting address => {}".format(addy))

        while fetch_more:
            response = await self._get_next(addy=addy, paging=paging_controls)
            entries.extend(response.get('entries', []))
            if response['paging']['next']:
                paging_controls = self._get_paging_controls(
                    response['paging']['next'])
            else:
                fetch_more = False

        # print("First entry = {}".format(entries[0]))
        # print("list entries = {}".format(entries))
        return {'data': entries}

    def get_state_list(self, address):
        """Get a listing of data from state"""
        result = asyncio.get_event_loop().run_until_complete(
            self._state_list(address))
        return result

    async def _submit_batches(self, batch_list):
        """Accepts a BatchList and submits it to the validator.
        batch_list:
        Response:
        """
        # Query validator
        # error_traps = [error_handlers.BatchInvalidTrap,
        #                error_handlers.BatchQueueFullTrap]
        validator_query = client_batch_submit_pb2.ClientBatchSubmitRequest(
            batches=batch_list.batches)

        return await self._query_validator(
            Message.CLIENT_BATCH_SUBMIT_REQUEST,
            client_batch_submit_pb2.ClientBatchSubmitResponse,
            validator_query)

    def submit_batches(self, batch_list):
        """Get a data leaf from state"""
        result = asyncio.get_event_loop().run_until_complete(
            self._submit_batches(batch_list))
        print("Batch submit result = {}".format(result))
        return result
