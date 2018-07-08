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

"""transactions - Batch and Transaction builders

This module is referenced to create transaction batches
"""
import datetime
import functools
import hashlib
from sawtooth_sdk.protobuf.transaction_pb2 import TransactionHeader
from sawtooth_sdk.protobuf.transaction_pb2 import Transaction
from sawtooth_sdk.protobuf.batch_pb2 import BatchHeader
from sawtooth_sdk.protobuf.batch_pb2 import Batch
from sawtooth_sdk.protobuf.batch_pb2 import BatchList

from shared.rest_client import RestClient
from modules.config import sawtooth_rest_host, valid_submitter, valid_signer


def compose_builder(*functions):
    """Construct composition"""
    return functools.reduce(
        lambda f, g: lambda x: f(g(x)), functions, lambda x: x)


def create_transaction(ingest):
    """Creates and signs a hashblock transaction with a payload."""
    signatore, address, permissions, payload = ingest
    serialized_payload = payload.SerializeToString()
    submitter = valid_submitter(signatore)
    signer = valid_signer(signatore)
    header = TransactionHeader(
        nonce=str(datetime.datetime.utcnow().timestamp()),
        signer_public_key=signer,
        family_name=address.family_ns_name,
        family_version=address.family_current_version,
        inputs=permissions.get('inputs', []),
        outputs=permissions.get('outputs', []),
        dependencies=permissions.get('dependencies', []),
        payload_sha512=hashlib.sha512(serialized_payload).hexdigest(),
        batcher_public_key=signer
    ).SerializeToString()

    return (signatore, Transaction(
        header=header,
        header_signature=submitter.sign(header),
        payload=serialized_payload))


def create_batch(payload):
    """Creates a batch from a list of transactions and a public key, and signs
    the resulting batch with the given signing key.

    Args:
        payload (tuple of):
            signatore (string): name for signing and cryptographic signer

            transactions (list of `Transaction`): The transactions to add
            to the batch.

    Returns:
        `Batch`: The constructed and signed batch.
    """
    signatore, transactions = payload
    signer = valid_signer(signatore)
    submitter = valid_submitter(signatore)
    txn_ids = [txn.header_signature for txn in transactions]
    batch_header = BatchHeader(
        signer_public_key=signer,
        transaction_ids=txn_ids).SerializeToString()

    return Batch(
        header=batch_header,
        header_signature=submitter.sign(batch_header),
        transactions=transactions)


def create_batch_list(batches):
    return BatchList(batches=batches)


def submit_batch(batches):
    """Submit transaction batches using default client URL"""
    batch_list = create_batch_list(batches)
    client = RestClient(sawtooth_rest_host())
    return client.send_batches(batch_list)


def submit_single_txn(ingest):
    """Wraps transaction for batch creation. Submits"""
    signatore, transaction = ingest
    return submit_batch([create_batch((signatore, [transaction]))])
