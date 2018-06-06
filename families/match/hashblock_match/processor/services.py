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

from modules.state import State
from modules.hashblock_zksnark import zksnark_verify

from protobuf.match_pb2 import (MatchEvent)


LOGGER = logging.getLogger(__name__)
KEYS_PATH = os.environ['HASHBLOCK_KEYS'] + '/'

_initiate_actions = frozenset([
    MatchEvent.UTXQ_ASK,
    MatchEvent.UTXQ_OFFER,
    MatchEvent.UTXQ_COMMITMENT,
    MatchEvent.UTXQ_GIVE])

_reciprocate_actions = frozenset([
    MatchEvent.MTXQ_TELL,
    MatchEvent.MTXQ_ACCEPT,
    MatchEvent.MTXQ_OBLIGATION,
    MatchEvent.MTXQ_TAKE])


class Service(ABC):
    _version_list = ['0.2.0']

    @classmethod
    def factory(cls, txn, context):
        key = txn.header.family_version
        if key not in cls._version_list:
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
        self._payload = MatchEvent()
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
        if self.payload.action in _initiate_actions:
            initiateFn()
        elif self.payload.action in _reciprocate_actions:
            reciprocateFn()
        else:
            raise InvalidTransaction(
                "Payload 'action' must be one of {} or {}".
                format([_initiate_actions, _reciprocate_actions]))


class V020apply(BaseService):

    def __init__(self, txn, state):
        super().__init__(txn, state)

    def initiate(self):
        """Version 0.2.0 works with enrypted data blobs"""
        self.state.set(self.payload.udata, self.payload.ukey)

    def reciprocate(self):
        """Version 0.2.0 works with encrypted data blobs
        and leverages the proof/verify capability of zksnark."""
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
                "Invalid zksnark match with reciprocating")

    def apply(self):
        self.process(self.initiate, self.reciprocate)
