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

from sdk.python.address import Address


class AssetType(ABC):
    _addresser = Address(Address.FAMILY_ASSET)

    @property
    def addresser(cls):
        return cls._addresser

    @classmethod
    def type_instance(cls, dimension):
        if dimension == Address.DIMENSION_UNIT:
            return TypeUnit(
                dimension,
                Address(Address.FAMILY_SETTING).settings(dimension))
        elif dimension == Address.DIMENSION_RESOURCE:
            return TypeResource(
                dimension,
                Address(Address.FAMILY_SETTING).settings(dimension))
        else:
            raise InvalidTransaction(
                'Invalid asset type {}'.format(dimension))

    @abstractmethod
    def empty_asset(self):
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
    def settings(self):
        pass

    @settings.setter
    @abstractmethod
    def settings(self, settings):
        pass


class BaseAssetType(AssetType):
    def __init__(self, dimension):
        self._settings = None
        self._dimension = dimension
        self._sett_addr = Address(Address.FAMILY_SETTING).settings(dimension)

    @property
    def setting_address(self):
        return self._sett_addr

    @property
    def candidates_address(self):
        return self._candidates_addr

    @property
    def settings(self):
        return self._settings

    @settings.setter
    def settings(self, settings):
        self._settings = settings


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
