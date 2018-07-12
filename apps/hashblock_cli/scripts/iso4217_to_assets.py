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
from functools import reduce


def get_element(parent_node, elname):
    el = parent_node.getElementsByTagName(elname)
    if len(el) == 0:
        return "Unknown"
    else:
        return el[0].childNodes[0].nodeValue


def get_key(parent_node):
    """Fetches the node tag value for 'Ccy'"""
    return get_element(parent_node, 'Ccy')


def get_code(parent_node):
    """Fetches the node tag value for 'CcyNbr'"""
    return get_element(parent_node, 'CcyNbr')


def get_precision(parent_node):
    """Fetches the node tag value for 'CcyMnrUnts' which is precision"""
    el = get_element(parent_node, 'CcyMnrUnts')
    return el if el != "N.A." else "0"


def __dedupe(rdict, parent):
    res_key = get_key(parent)
    # If main element is Unknown, skip it
    if res_key == "Unknown":
        return rdict
    else:
        res_code = get_code(parent)
        # If already in set of codes, skip it
        if res_code in rdict["set"]:
            return rdict
        else:
            rdict["set"].add(res_code)
            rdict["array"].append(
                {
                    "system": "iso4217",
                    "key": res_key,
                    "prime": "",
                    "properties": [
                        {
                            "name": "currency_precision",
                            "value": get_precision(parent)
                        },
                        {
                            "name": "country_code",
                            "value": res_code
                        }]
                })
            return rdict


def geniso4217():
    """Generates a list of dictionaries representing iso4217 currenty units"""
    ucum = urllib.request.urlopen(
        'https://www.currency-iso.org/dam/downloads/lists/list_one.xml').read()
    dom = minidom.parseString(ucum)
    codes = dom.getElementsByTagName('CcyNtry')
    genesis_array = []
    ident_set = set()
    red_dict = {"array": genesis_array, "set": ident_set}
    reduce(__dedupe, codes, red_dict)
    return genesis_array


if __name__ == '__main__':
    x = geniso4217()
    print("Assets => {}".format(x))
