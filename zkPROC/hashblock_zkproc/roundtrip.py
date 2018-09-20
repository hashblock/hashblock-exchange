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

tree_i = "0000000000000000000000000000000000000000000000000000000000000000"

secret_str = "13dc0ddd3ff7431ea297f517c4878b682655a892da3b38e85da00cefe8975bb3"
value_str = ["5", "10", "1", "9"]
unit_str = [
    "F1B94C743FD09943",
    "CA66A94FBBF9D5F7",
    "C6B362C50A27038B",
    "CF05392F72684BD7"]
asset_str = [
    "D73F2B8A5D5C5A7B",
    "C75CA75D7FBD0FF5",
    "D6E4DA34225CB635",
    "FFF1FD716E918B99"]


def commit_run(secret, tree, value, unit, asset):
    """ """
    print("----------------------------------------------------")
    print("In Tree ".format(tree))
    print("In Value {}".format(value))
    print("In Unit {}".format(unit))
    print("In Asset {}".format(asset))
    qcm_gen = subprocess.run(
        ['build/hbzkproc', '-qc', secret, value, unit, asset],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    if qcm_gen.returncode == 0:
        v_note, u_note, a_note = qcm_gen.stderr.decode("utf-8").split()
        # print("Out Value Note {}".format(v_note))
        # print("Out Unit Note {}".format(u_note))
        # print("Out Asset Note {}".format(a_note))
        ctm = subprocess.run(
            [
                'build/hbzkproc', '-ctm',
                tree, secret,
                v_note, u_note, a_note],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if(ctm.returncode == 0):
            new_tree, vprf, uprf, aprf = ctm.stderr.decode("utf-8").split()
            print("Tree output {}".format(new_tree))
            print("Value proof {}".format(vprf))
            print("Unit proof {}".format(uprf))
            print("Asset proof {}".format(aprf))
        else:
            print("Turing's commitment to tree fault {}".format(ctm.stderr))
            print("Log {}".format(ctm.stdout.decode()))
            new_tree = tree
        return new_tree
    else:
        print("Turing's quantity commitment fault {}".format(qcm_gen.stderr))
        print("Log {}".format(qcm_gen.stdout.decode()))
        return tree_i


def main():
    tree = tree_i
    res = []

    for v, u, a in zip(value_str, unit_str, asset_str):
        tree = commit_run(secret_str, tree, v, u, a)
        res.append(tree)


if __name__ == '__main__':
    main()
