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

import urllib.request
from xml.dom import minidom


def get_key(parent_node):
    """Fetches the node tag value for 'Ccy'"""
    ccys = parent_node.getElementsByTagName('Ccy')
    if len(ccys) == 0:
        return "Unknown"
    else:
        return ccys[0].childNodes[0].nodeValue


def get_precision(parent_node):
    """Fetches the node tag value for 'CcyMnrUnts' which is precision"""
    cmus = parent_node.getElementsByTagName('CcyMnrUnts')
    if len(cmus) == 0:
        return "Unknown"
    else:
        return cmus[0].childNodes[0].nodeValue


def geniso4217():
    """Generates a list of dictionaries representing iso4217 currenty units"""
    ucum = urllib.request.urlopen(
        'https://www.currency-iso.org/dam/downloads/lists/list_one.xml').read()
    dom = minidom.parseString(ucum)
    codes = dom.getElementsByTagName('CcyNtry')
    genesis_array = []
    for c in codes:
        res_key = get_key(c)
        if res_key != "Unknown":
            res_minor = get_precision(c)
            if res_minor == "N.A.":
                res_minor = "0"
        else:
            res_key = None
        if res_key:
            genesis_array.append(
                {
                    "system": "iso4217",
                    "key": res_key,
                    "prime": "",
                    "precision": res_minor
                })
    return genesis_array


if __name__ == '__main__':
    x = geniso4217()
    print("{}".format(x))
