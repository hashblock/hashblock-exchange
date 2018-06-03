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
from abc import ABC, abstractmethod

from sawtooth_sdk.processor.exceptions import InvalidTransaction

from modules.state import State

from protobuf.match_pb2 import MatchEvent

LOGGER = logging.getLogger(__name__)

initiate_actions = frozenset([
    MatchEvent.UTXQ_ASK,
    MatchEvent.UTXQ_OFFER,
    MatchEvent.UTXQ_COMMITMENT,
    MatchEvent.UTXQ_GIVE])

reciprocate_actions = frozenset([
    MatchEvent.MTXQ_TELL,
    MatchEvent.MTXQ_ACCEPT,
    MatchEvent.MTXQ_OBLIGATION,
    MatchEvent.MTXQ_TAKE])


class Service(ABC):
    _version_list = ['0.1.0', '0.2.0']

    @classmethod
    def factory(cls, txn, context, address):
        key = txn.header.family_version
        LOGGER.debug("Service test for key {}".format(key))
        if key not in cls._version_list:
            raise InvalidTransaction("Unhandled version {}".format(key))
        else:
            state = State(context, address)
            if key == '0.1.0':
                handler = V010apply(txn, state)
            else:
                handler = V020apply(txn, state)
        LOGGER.debug("Service returning {}".format(type(handler).__name__))
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
        exchange_payload = MatchEvent()
        exchange_payload.ParseFromString(txn.payload)
        self._payload = exchange_payload

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
        if self.payload.action in initiate_actions:
            initiateFn()
        elif self.payload.action in reciprocate_actions:
            reciprocateFn()
        else:
            raise InvalidTransaction(
                "payload 'action' must be one of {} or {}".
                format([initiate_actions, reciprocate_actions]))


class V020apply(BaseService):

    def __init__(self, txn, state):
        super().__init__(txn, state)

    def initiate(self):
        LOGGER.debug("Initiate 0.2.0")
        pass

    def reciprocate(self):
        LOGGER.debug("Reciprocate 0.2.0")
        pass

    def apply(self):
        LOGGER.debug("Applying 0.2.0 logic")
        self.process(self.initiate, self.reciprocate)


class V010apply(BaseService):

    def __init__(self, txn, state):
        super().__init__(txn, state)

    def initiate(self):
        LOGGER.debug("Initiate 0.1.0")
        pass

    def reciprocate(self):
        LOGGER.debug("Reciprocate 0.1.0")
        pass

    def apply(self):
        LOGGER.debug("Applying 0.1.0 logic")
        self.process(self.initiate, self.reciprocate)
