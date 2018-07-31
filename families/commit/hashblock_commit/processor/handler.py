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

from protobuf.commit_pb2 import CommitPayload
from protobuf.commit_pb2 import CommitWrapper

from modules.address import Address

LOGGER = logging.getLogger(__name__)

# Number of seconds to wait for state operations to succeed
STATE_TIMEOUT_SEC = 10


class CommitTransactionHandler(TransactionHandler):

    def __init__(self):
        self._addresser = Address.commit_addresser()
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
        commit_payload = CommitPayload()
        commit_payload.ParseFromString(transaction.payload)
        commit = CommitWrapper()
        commit.ParseFromString(commit_payload.data)
        # address = self.addresser.commit(commit.id, commit.property)
        # return self._set_commit(context, commit, address)

    def _set_commit(self, context, commit, address):
        """Change the hashblock commits on the block
        """
        LOGGER.debug("Processing commit payload")

        try:
            context.set_state(
                {address: commit.SerializeToString()},
                timeout=STATE_TIMEOUT_SEC)
        except FutureTimeoutError:
            LOGGER.warning(
                'Timeout occured on set_state([%s, <value>])',
                self.address)
            raise InternalError(
                'Unable to set {}'.format(self.address))
        if self.action == CommitPayload.CREATE:
            pass


def _get_commit(context, address, default_value=None):
    """Get a hashblock commits from the block
    """
    commit = CommitWrapper()
    results = _get_state(context, address)
    if results:
        commit.ParseFromString(results[0].data)
        return commit
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
