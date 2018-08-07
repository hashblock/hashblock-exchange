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

secret_str = "13dc0ddd3ff7431ea297f517c4878b682655a892da3b38e85da00cefe8975bb3"
value_str = "5"
unit_str = "0E77546B264D97ED79C0E8A00BF62F7C2A0F8BA6BE3D"
asset_str = "0F2538C94209E2E2C98D319352C3630FCDA76F802E1F"

qcm_gen = subprocess.run(
    ['build/hbzkproc', '-qc', secret_str, value_str, unit_str, asset_str],
    stdout=subprocess.PIPE, stderr=subprocess.PIPE)

if qcm_gen.returncode == 0:
    val_cm, unit_cm, asset_cm = qcm_gen.stderr.decode("utf-8").split()
    print("Value CM {}".format(val_cm))
    print("Unit CM {}".format(unit_cm))
    print("Asset CM {}".format(asset_cm))
    print()
    print("Log {}".format(qcm_gen.stdout.decode("utf-8")))
else:
    print("Turing's quantity commitment fault {}".format(qcm_gen.stderr))
