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

import subprocess
from sawtooth_sdk.processor.exceptions import InternalError


def prime_gen():
    """Returns prime based on 172 bit range. Results is 44 char"""
    x = subprocess.run(
        ['openssl', 'prime', '-generate', '-bits', '64', '-hex'],
        stdout=subprocess.PIPE)
    return x.stdout[:-1].zfill(44)


def zkproc_quantity_cm(secret, value, unit, asset):
    """Generates the commitments for quantity

        Returns:
            [value_commitment, unit_commitment, asset_commitment]
    """
    zkp_gen = subprocess.run(
        ['hbzkproc', '-qc', secret, value, unit, asset],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if zkp_gen.returncode == 0:
        return zkp_gen.stderr.decode("utf-8").split()
    else:
        raise InternalError(
            "hbzkproc quantity commitments failed with {}".
            format(zkp_gen.returncode))


def zkproc_insert_cm(tree, value_cm, unit_cm, asset_cm):
    """Inserts quantity commitments into merkle trie

        Returns:
            [new_tree,
                [val tree pos, val_commitment],
                [unit tree pos, unit_commitment],
                [asset tree pos, asset_commitment]]
    """
    zkp_gen = subprocess.run(
        ['hbzkproc', '-ctm', tree, value_cm, unit_cm, asset_cm],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if zkp_gen.returncode == 0:
        val_tup, unit_tup, asset_tup, new_tree = \
            zkp_gen.stderr.decode("utf-8").split()
        return [
            new_tree,
            val_tup.split(','),
            unit_tup.split(','),
            asset_tup.split(',')]
    else:
        raise InternalError(
            "hbzkproc commitments to tree failed with {}".
            format(zkp_gen.returncode))


def zksnark_genkeys(file_path, secret_str):
    """Generates the proover and verifyer 'keys'"""
    key_gen = subprocess.run(
        ['hbzksnark', '-g', file_path, secret_str],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if key_gen.returncode != 0:
        raise InternalError(
            "hbzksnark key generated failed with {}".
            format(key_gen.returncode))


def zksnark_genproof(file_path, data_str):
    """Generates a proof based on data string

    Returns a tuple of ('proof' and 'pairing' base64 encoded strings)

    """
    prf_gen = subprocess.run(
        ['hbzksnark', '-p', file_path, data_str],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if prf_gen.returncode == 0:
        return prf_gen.stderr.decode("utf-8").split()
    else:
        raise InternalError(
            "hbzksnark proof generated failed with {}".
            format(prf_gen))


def zksnark_verify(file_path, proof_str, pairing_str):
    """Verifies equation match"""
    ver_gen = subprocess.run(
        ['hbzksnark', '-v', file_path, proof_str, pairing_str],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if ver_gen.returncode == 0:
        return True
    else:
        return False
