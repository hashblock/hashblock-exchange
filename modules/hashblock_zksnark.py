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
    """Generates a proof based on data string"""
    prf_gen = subprocess.run(
        ['hbzksnark', '-p', file_path, data_str],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if prf_gen.returncode == 0:
        return prf_gen.stderr
    else:
        raise InternalError(
            "hbzksnark key generated failed with {}".
            format(prf_gen))


def zksnark_verify(file_path, proof_str, data_str):
    """Verifies equation match"""
    ver_gen = subprocess.run(
        ['hbzksnark', '-v', file_path, proof_str, data_str],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if ver_gen.returncode == 0:
        return True
    else:
        return False
