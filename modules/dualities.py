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

import os
from yaml import load
from abc import ABC, abstractmethod


def _load_dualities(cfg_path, configfile):
    """Reads the duality configuration file"""
    print("Reading {} from {}".format(configfile, cfg_path))
    try:
        with open(os.path.join(cfg_path, configfile), 'r') as f:
            doc = load(f)
    except IOError:
        print("Could not read {}".format(configfile))
        raise
    return doc


HB_KEY = 'hashblock'
INIT_KEY = 'initiates'
RECP_KEY = 'reciprocates'
VERS_KEY = 'version'
NSS_KEY = 'namespaces'
DEPS_KEY = 'depends_on'


class Duality(object):
    """Duality class is responsible for loading and managing

    user specifications
    """
    _initiated = False

    @classmethod
    def load_dualities(cls, path_env_key, duality_config):
        if not cls._initiated:
            cls._initiated = True
            cls._specification = _load_dualities(
                os.environ.get(path_env_key),
                duality_config)
            cls._base = {
                HB_KEY: HashblockSpec(
                    HB_KEY, cls._specification[NSS_KEY].pop(HB_KEY))}
            cls._lookup = {
                k: AbstractDualitySpec.load_spec(k, v) for (k, v)
                in cls._specification[NSS_KEY].items()}
        else:
            pass

    @classmethod
    def raw_specification(cls):
        return cls._specification

    @property
    @classmethod
    def dualities_version(cls):
        return cls._specification[VERS_KEY]

    @property
    @classmethod
    def spec_names(cls):
        return cls._lookup.keys()

    @classmethod
    def duality_for_ns(cls, namespace):
        return cls._lookup[namespace]

    @classmethod
    def breakqname(cls, ns_vs):
        return ns_vs.split('.')

    @classmethod
    def is_valid_verb(cls, ns_vs):
        parts = cls.breakqname(ns_vs)
        if len(parts) != 2:
            return False
        else:
            spec = cls.duality_for_ns(parts[0])
            if parts[1] in spec.initiates or parts[1] in spec.reciprocates:
                return True
            else:
                return False

    @classmethod
    def reciprocate_depends_on(cls, ns_vs):
        parts = cls.breakqname(ns_vs)
        if len(parts) != 2:
            return None
        else:
            spec = cls.duality_for_ns(parts[0])
            return spec.depends_on(parts[1])


class AbstractDualitySpec(ABC):
    """Abstraction Factory for generating DualitySpecs"""
    def __init__(self, specname, specmap):
        self._specname = specname
        self._specmap = specmap

    @classmethod
    def load_spec(cls, specname, specmap):
        """load_spec class method is factory for creating DualitySpec types"""
        return UserSpec(specname, specmap)

    @property
    @abstractmethod
    def specname(self):
        """Return the namespace of a spec"""
        pass

    @property
    @abstractmethod
    def specmap(self):
        """Return the YAML map of the spec"""
        pass

    @property
    @abstractmethod
    def initiates(self):
        """Return a list of initiate verbs from spec"""
        pass

    @property
    @abstractmethod
    def reciprocates(self):
        """Return a list of reciprocate verbs from spec"""
        pass

    @abstractmethod
    def depends_on(self, rverb):
        """Return an initiate verb that reciprocate verb depends on"""
        pass


class DualitySpec(AbstractDualitySpec):
    """Base duality spec satisfies name and map requests"""
    def __init__(self, specname, specmap):
        super().__init__(specname, specmap)

    @property
    def specname(self):
        return self._specname

    @property
    def specmap(self):
        return self._specmap


class HashblockSpec(DualitySpec):
    """The hashblock spec is actually a template used by

    concrete specifications and it does not support initiate
    or reciprocate verb listings
    """
    def __init__(self, specname, specmap):
        super().__init__(specname, specmap)

    @property
    def initiates(self):
        raise RuntimeError("hashblock spec does not support initiates")

    @property
    def reciprocates(self):
        raise RuntimeError("hashblock spec does not support reciprocates")

    def depends_on(self, rverb):
        raise RuntimeError("hashblock spec does not support depends_on")


class UserSpec(DualitySpec):
    """User specification are true specifications"""
    def __init__(self, specname, specmap):
        super().__init__(specname, specmap)
        self._initiates = self.specmap[INIT_KEY].keys()
        self._reciprocates = self.specmap[RECP_KEY].keys()

    @property
    def initiates(self):
        return self._initiates

    @property
    def reciprocates(self):
        return self._reciprocates

    def depends_on(self, rverb):
        return self.specmap[RECP_KEY][rverb][DEPS_KEY]


if __name__ == '__main__':
    from modules.config import (
        load_hashblock_config,
        ENVIRONMENT_CFGR_PATH)
    x = load_hashblock_config()
    Duality.load_dualities(ENVIRONMENT_CFGR_PATH, "dualities.yaml")
