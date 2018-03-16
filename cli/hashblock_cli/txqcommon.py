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

import hashlib

INITIATE_EVENT_KEY = 'utxq'
RECIPROCATE_EVENT_KEY = 'mtxq'
ADDRESS_PREFIX = 'hashblock_match'

MATCH_NAMESPACE = hashlib.sha512(
    ADDRESS_PREFIX.encode("utf-8")).hexdigest()[0:6]
INITIATE_LIST_ADDRESS = MATCH_NAMESPACE + \
    hashlib.sha512(INITIATE_EVENT_KEY.encode("utf-8")).hexdigest()[0:6]
RECIPROCATE_LIST_ADDRESS = MATCH_NAMESPACE + \
    hashlib.sha512(RECIPROCATE_EVENT_KEY.encode("utf-8")).hexdigest()[0:6]

_MIN_PRINT_WIDTH = 15
_MAX_KEY_PARTS = 4
_ADDRESS_PART_SIZE = 16


hash_lookup = {
    "bag": 2,
    "bags": 2,
    "{peanuts}": 3,
    "$": 5,
    "{usd}": 7,
    "bale": 11,
    "bales": 11,
    "{hay}": 13
}
