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


class Address():

    # Namespace and family strings for TP's
    NAMESPACE = "hashblock"
    NAMESPACE_ASSET = 'hashblock_asset'
    NAMESPACE_MATCH = 'hashblock_match'
    NAMESPACE_SETTING = 'hashblock_setting'

    # Families
    FAMILY_ASSET = "asset"
    FAMILY_MATCH = "match"
    FAMILY_SETTING = "setting"

    # Dimensions, used by families
    DIMENSION_UNIT = "unit"
    DIMENSION_RESOURCE = "resource"
    DIMENSION_UTXQ = "utxq"
    DIMENSION_MTXQ = "mtxq"

    # Settings
    SETTING_AUTHKEYS = "authorized-keys"
    SETTING_APPTHRESH = "approval-threshold"

    # Proposals
    ASSET_CANDIDATES = "candidates"

    _namespace_hash = hashlib.sha512(
        NAMESPACE.encode("utf-8")).hexdigest()[0:6]
    _filler_hash26 = hashlib.sha512('filler'.encode("utf-8")).hexdigest()[0:52]
    _filler_hash23 = _filler_hash26[0:46]
    _candidates_hash = hashlib.sha512(
        ASSET_CANDIDATES.encode("utf-8")).hexdigest()[0:6]

    def __init__(self, family):
        self._family = family
        self._family_hash = self.hashup(family)[0:6]

    @property
    def ns_family(self):
        """Return the namespace family unique hash id
        """
        return self._namespace_hash + self._family_hash

    def hashup(self, value):
        """Create a suitable hash from value
        """
        return hashlib.sha512(value.encode("utf-8")).hexdigest()

    # E.g. hashblock.asset.candidates
    # 0-2 namespace
    # 3-5 family
    # 6-8 candidates
    @property
    def candidates_base(self):
        return self.ns_family \
            + self._candidates_hash

    # E.g. hashblock.asset.candidates.dimension.filler
    # 0-2 namespace
    # 3-5 family
    # 6-8 candidates
    # 9-11 dimension
    # 12-34 filler23
    def candidates(self, dimension):
        """Create the dimensions proposal address
        """
        return self.candidates_base \
            + self.hashup(dimension)[0:6] \
            + self._filler_hash23

    # E.g. hashblock.setting.unit.authorized_keys
    # 0-2 namespace
    # 3-5 family
    # 6-8 dimension
    # 9-34 filler26
    def settings(self, dimension):
        """Create the dimension settings address using key
        """
        return self.ns_family \
            + self.hashup(dimension)[0:6] \
            + self._filler_hash26

    # E.g. hashblock.asset.unit.imperial.foot
    # 0-2  namespace
    # 3-5  family
    # 6-8  dimension
    # 9-11 system
    # 12-34 item
    def asset_item(self, dimension, system, item):
        """Create a specific asset address based on dimension, system and id
        """
        return self.ns_family \
            + self.hashup(dimension)[0:6] \
            + self.hashup(system)[0:6] \
            + self.hashup(item)[0:46]

    # E.g. hashblock.match.utxq.ask
    # 0-2 namespace
    # 3-5 family
    # 6-8 dimension
    def txq_dimension(self, dimension):
        return self.ns_family \
            + self.hashup(dimension)[0:6]

    # E.g. hashblock.match.utxq.ask
    # 0-2 namespace
    # 3-5 family
    # 6-8 dimension
    # 9-11 ops
    def txq_list(self, dimension, ops):
        return self.txq_dimension(dimension) \
            + self.hashup(ops)[0:6]

    # E.g. hashblock.match.utxq.ask.ident
    # 0-2 namespace
    # 3-5 family
    # 6-8 dimension
    # 9-11 ops
    # 12-34 id
    def txq_item(self, dimension, ops, ident):
        """Create a specific match address based on dimenstion, operation and id
        """
        return self.txq_list(dimension, ops) \
            + self.hashup(ident)[0:46]
