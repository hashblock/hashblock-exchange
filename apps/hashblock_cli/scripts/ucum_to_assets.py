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
from xml.dom import minidom, Node


def get_name(parent_node):
    """Fetches the node tag value for 'name'"""
    return parent_node.getElementsByTagName('name')[0].childNodes[0].nodeValue


def get_code(parent_node):
    """Fetches the node attribute value for 'Code'"""
    return str(parent_node.attributes["Code"].value)


def get_symbol(parent_node):
    """Fetches the node tag value for 'printSymbol'"""
    def traverse(node):
        while node != Node.TEXT_NODE:
            if len(node.childNodes) != 0:
                traverse(node.childNodes[0])
            else:
                return get_name(parent_node)
        return node.data

    x = parent_node.getElementsByTagName('printSymbol')
    if len(x) == 0:
        return get_name(parent_node)
    else:
        x0 = x[0]
        cn = x0.childNodes
        if len(cn) == 0:
            return get_name(parent_node)
        else:
            return traverse(cn[0])


def genucum():
    """Generates a list of dictionaries representing ucum base units
    and units"""
    ucum = urllib.request.urlopen(
        'http://unitsofmeasure.org/ucum-essence.xml').read()
    dom = minidom.parseString(ucum)

    base_units = dom.getElementsByTagName('base-unit')
    units = dom.getElementsByTagName('unit')

    primes = [2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37]
    used_primes = set()

    genesis_array = [
        {"system": "universal", "prime": "1".zfill(44), "key": "unity"}]

    for b in base_units:
        prime_id = None
        for p in primes:
            if p not in used_primes:
                used_primes.add(p)
                prime_id = "{:x}".format(p)
                break
        bname = {
            "system": "ucum",
            "prime": prime_id.zfill(44),
            "key": get_code(b)}
        genesis_array.append(bname)

    for u in units:
        uname = {"system": "ucum", "prime": "", "key": get_code(u)}
        genesis_array.append(uname)

    # print("{}".format(json.dumps(genesis_array)))
    return genesis_array


if __name__ == '__main__':
    x = genucum()
    print("{}".format(x))
