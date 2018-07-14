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


class ExchangeTransactionHandler(TransactionHandler):

    def __init__(self):
        self._addresser = Address.exchange_utxq_addresser()

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
        """exchange-tp transaction handling entry point"""
        Service.factory(
            self.addresser,
            transaction,
            context).apply()
