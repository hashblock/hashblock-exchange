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

from abc import ABC, abstractmethod

from sawtooth_sdk.processor.exceptions import InvalidTransaction

from protobuf.asset_pb2 import Unit
from protobuf.asset_pb2 import Resource
from modules.address import Address


class AssetType(ABC):
    _addresser = Address(Address.FAMILY_ASSET)

    @property
    def addresser(cls):
        return cls._addresser

    @classmethod
    def type_instance(cls, dimension):
        if dimension == Address.DIMENSION_UNIT:
            return TypeUnit(dimension)
        elif dimension == Address.DIMENSION_RESOURCE:
            return TypeResource(dimension)
        else:
            raise InvalidTransaction(
                'Invalid asset type {}'.format(dimension))

    @abstractmethod
    def empty_asset(self):
        pass

    @property
    @abstractmethod
    def asset(self):
        pass

    @asset.setter
    @abstractmethod
    def asset(self, asset):
        pass

    @property
    @abstractmethod
    def setting_address(self):
        pass

    @property
    @abstractmethod
    def candidates_address(self):
        pass

    @property
    @abstractmethod
    def asset_address(self):
        pass

    @abstractmethod
    def asset_from_proposal(self, proposal):
        pass

    @property
    @abstractmethod
    def settings(self):
        pass

    @settings.setter
    @abstractmethod
    def settings(self, settings):
        pass


class BaseAssetType(AssetType):
    def __init__(self, dimension):
        self._asset = None
        self._settings = None
        self._dimension = dimension
        self._candidates_addr = self.addresser.candidates(
            dimension)
        self._sett_addr = Address(Address.FAMILY_SETTING).settings(dimension)

    @property
    def asset(self):
        return self._asset

    @asset.setter
    def asset(self, asset):
        self._asset = asset

    @property
    def settings(self):
        return self._settings

    @settings.setter
    def settings(self, settings):
        self._settings = settings

    @property
    def dimension(self):
        return self._dimension

    @property
    def candidates_address(self):
        return self._candidates_addr

    @property
    def setting_address(self):
        return self._sett_addr

    def asset_from_payload(self, payload):
        x = self.empty_asset()
        x.ParseFromString(payload.data)
        self.asset = x

    def asset_from_proposal(self, proposal):
        x = self.empty_asset()
        x.ParseFromString(proposal.asset)
        self.asset = x

    @property
    def asset_address(self):
        return self.addresser.asset_item(
            self.dimension,
            self.asset.system,
            self.asset.key,
            self.asset.value)


class TypeUnit(BaseAssetType):
    def __init__(self, dimension):
        super().__init__(dimension)

    def empty_asset(self):
        return Unit()


class TypeResource(BaseAssetType):
    def __init__(self, dimension):
        super().__init__(dimension)

    def empty_asset(self):
        return Resource()
