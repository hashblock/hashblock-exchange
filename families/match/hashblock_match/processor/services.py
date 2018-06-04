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

from modules.config import valid_key
from modules.state import State
from modules.hashblock_zksnark import zksnark_verify

from protobuf.match_pb2 import (
    MatchEvent,
    UTXQ,
    MTXQ)


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

_initiate_key_set = frozenset(['plus', 'minus', 'quantity'])
_reciprocate010_key_set = frozenset(['plus', 'minus', 'quantity', 'ratio'])
_reciprocate020_key_set = frozenset(['proof']).union(_reciprocate010_key_set)


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
        if self.payload.action in _initiate_actions:
            initiateFn()
        elif self.payload.action in _reciprocate_actions:
            reciprocateFn()
        else:
            raise InvalidTransaction(
                "Payload 'action' must be one of {} or {}".
                format([_initiate_actions, _reciprocate_actions]))

    def match(self, utxq, mtxq):
        """Utilizes hbzksnark in 0.x.0"""
        return True

    def check_payload_coherence(self, exchange, basis):
        """Validate coherent transaction payload content"""
        ep = valid_key(exchange.plus.decode())
        em = valid_key(exchange.minus.decode())
        zset = set([f[0].name for f in exchange.ListFields()])
        if basis != zset or not ep or not em:
            raise InvalidTransaction("Incoherent transaction payload")


class V020apply(BaseService):

    def __init__(self, txn, state):
        super().__init__(txn, state)

    def initiate(self):
        """Version 0.2.0 works with enrypted data blobs"""
        LOGGER.debug("Initiate 0.2.0")
        pass

    def reciprocate(self):
        LOGGER.debug("Reciprocate 0.2.0")
        pass

    def apply(self):
        LOGGER.debug("Applying 0.2.0 logic")
        self.process(self.initiate, self.reciprocate)


class V010apply(BaseService):
    """Handles 0.1.0 transactions

    With the refactoring also comes a way to leverage
    the zkSNARK verification of the balancing equation
    during MTXQ processing as the proof (so to speak)
    is part of the MTXQ structure
    """
    def __init__(self, txn, state):
        super().__init__(txn, state)

    def initiate(self):
        exchange = UTXQ()
        exchange.ParseFromString(self.payload.mdata)
        self.check_payload_coherence(exchange, _initiate_key_set)
        self.state.set(self.payload.mdata, self.payload.ukey)

    def reciprocate(self):
        exchange = MTXQ()
        exchange.ParseFromString(self.payload.mdata)
        self.check_payload_coherence(exchange, _reciprocate010_key_set)

    def apply(self):
        LOGGER.debug("Applying 0.1.0 logic")
        self.process(self.initiate, self.reciprocate)
