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

from modules.address import Address
from modules.config import load_hashblock_config

from processor.services import Service


LOGGER = logging.getLogger(__name__)
load_hashblock_config()


class MatchTransactionHandler(TransactionHandler):

    def __init__(self):
        self._addresser = Address(Address.FAMILY_MATCH, ['0.2.0'])

    @property
    def addresser(self):
        return self._addresser

    @property
    def family_name(self):
        return self.addresser.namespace

    @property
    def family_versions(self):
        return self.addresser.version

    @property
    def namespaces(self):
        return [self.addresser.ns_family]

    def apply(self, transaction, context):
        """match-tp transaction handling entry point"""
        Service.factory(
            transaction,
            context).apply()
