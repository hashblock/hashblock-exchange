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

import os
import logging
from abc import ABC, abstractmethod

from sawtooth_sdk.processor.exceptions import InvalidTransaction

from modules.state import State, StateDataNotFound
from modules.hashblock_zksnark import zksnark_verify

from protobuf.exchange_pb2 import (ExchangePayload)


LOGGER = logging.getLogger(__name__)
KEYS_PATH = os.environ['HASHBLOCK_KEYS'] + '/'


class Service(ABC):

    @classmethod
    def factory(cls, addresser, txn, context):
        key = txn.header.family_version
        if key not in addresser.family_versions:
            raise InvalidTransaction("Unhandled version {}".format(key))
        else:
            handler = V020apply(txn, State(context))
        return handler

    @abstractmethod
    def apply(self):
        pass

    @abstractmethod
    def initiate(self):
        pass

    @abstractmethod
    def reciprocate(self):
        pass

    @property
    @abstractmethod
    def state(self):
        pass

    @property
    @abstractmethod
    def transaction(self):
        pass

    @property
    @abstractmethod
    def payload(self):
        pass


class BaseService(Service):
    def __init__(self, txn, state):
        self._txn = txn
        self._state = state
        self._payload = ExchangePayload()
        self._payload.ParseFromString(txn.payload)

    @property
    def state(self):
        return self._state

    @property
    def transaction(self):
        return self._txn

    @property
    def payload(self):
        return self._payload

    def process(self, initiateFn, reciprocateFn):
        if self.payload.type == ExchangePayload.UTXQ:
            initiateFn()
        elif self.payload.type == ExchangePayload.MTXQ:
            reciprocateFn()
        else:
            raise InvalidTransaction(
                "Payload 'type' must be one of: {} or {}".
                format([ExchangePayload.UTXQ, ExchangePayload.MTXQ]))


class V020apply(BaseService):

    def __init__(self, txn, state):
        super().__init__(txn, state)

    def initiate(self):
        """Version 0.2.0 works with enrypted data blobs"""
        self.state.set(self.payload.udata, self.payload.ukey)

    def reciprocate(self):
        """Version 0.2.0 works with encrypted data blobs
        and leverages the proof/verify capability of zksnark."""
        try:
            self.state.get_state_data(self.payload.ukey)
            raise InvalidTransaction(
                "UTXQ {} already exchangeed".format(self.payload.ukey))
        except StateDataNotFound:
            pass

        vres = zksnark_verify(
            KEYS_PATH,
            self.payload.proof.decode(),
            self.payload.pairings.decode())
        if vres:
            LOGGER.info("UTXQ and MTXQ Balance!")
            self.state.set(self.payload.udata, self.payload.ukey)
            self.state.set(self.payload.mdata, self.payload.mkey)
        else:
            raise InvalidTransaction(
                "Invalid zksnark exchange with reciprocating")

    def apply(self):
        self.process(self.initiate, self.reciprocate)
