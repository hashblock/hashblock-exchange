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


from shared.transactions import (
    submit_single_txn, create_transaction, compose_builder)

from modules.decode import commit_addresser


def _validate_quantity(data):
    pass


def _create_mint(ingest):
    pass


def _create_commit_wrapper(ingest):
    pass


def _create_inputs_outputs(ingest):
    pass


def create_minted_quantity(data):
    return
    # direct = compose_builder(
    #     submit_single_txn, create_transaction, _create_inputs_outputs,
    #     _create_commit_wrapper, _create_mint)
    # direct((
    #     data['signer'],
    #     commit_addresser,
    #     data))
