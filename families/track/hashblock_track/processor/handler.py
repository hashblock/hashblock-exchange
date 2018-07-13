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

import logging

from sawtooth_sdk.processor.handler import TransactionHandler
from sawtooth_sdk.messaging.future import FutureTimeoutError
from sawtooth_sdk.processor.exceptions import InvalidTransaction
from sawtooth_sdk.processor.exceptions import InternalError

from protobuf.track_pb2 import TrackPayload
from protobuf.track_pb2 import Track

from modules.address import Address

LOGGER = logging.getLogger(__name__)

# Number of seconds to wait for state operations to succeed
STATE_TIMEOUT_SEC = 10


class TrackTransactionHandler(TransactionHandler):

    def __init__(self):
        self._addresser = Address.track_addresser()
        self._auth_list = None
        self._action = None

    @property
    def addresser(self):
        return self._addresser

    @property
    def family_name(self):
        return self.addresser.family_ns_name

    @property
    def family_versions(self):
        return self.addresser.family_versions

    @property
    def namespaces(self):
        return [self.addresser.family_ns_hash]

    def apply(self, transaction, context):
        track_payload = TrackPayload()
        track_payload.ParseFromString(transaction.payload)
        track = Track()
        track.ParseFromString(track_payload.data)
        address = self.addresser.track(track.asset_ident, track.property)

        return self._set_track(context, track, address)

    def _set_track(self, context, track, address):
        """Change the hashblock tracks on the block
        """
        LOGGER.debug("Processing track payload")

        try:
            context.set_state(
                {address: track.SerializeToString()},
                timeout=STATE_TIMEOUT_SEC)
        except FutureTimeoutError:
            LOGGER.warning(
                'Timeout occured on set_state([%s, <value>])',
                self.address)
            raise InternalError(
                'Unable to set {}'.format(self.address))
        if self.action == TrackPayload.CREATE:
            pass


def _get_track(context, address, default_value=None):
    """Get a hashblock tracks from the block
    """
    track = Track()
    results = _get_state(context, address)
    if results:
        track.ParseFromString(results[0].data)
        return track
    return default_value


def _get_state(context, address):
    try:
        results = context.get_state([address], timeout=STATE_TIMEOUT_SEC)
    except FutureTimeoutError:
        LOGGER.warning(
            'Timeout occured on context.get_state([%s])',
            address)
        raise InternalError('Unable to get {}'.format(address))
    return results
