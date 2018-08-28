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
import logging
from yaml import load
from abc import ABC, abstractmethod

LOGGER = logging


def _load_dualities(cfg_path, configfile):
    """Reads the duality configuration file"""
    LOGGER.info("Reading {} from {}".format(configfile, cfg_path))
    try:
        with open(os.path.join(cfg_path, configfile), 'r') as f:
            doc = load(f)
    except IOError:
        LOGGER.error("Could not read {}".format(configfile))
        raise
    return doc


HB_KEY = 'hashblock'
INIT_KEY = 'initiates'
RECP_KEY = 'reciprocates'
VERS_KEY = 'version'
NSS_KEY = 'namespaces'
DEPS_KEY = 'depends_on'
VERBS_KEY = 'verbs'
BASEVERBS_KEY = 'base_verbs'
PRP_KEY = 'prepositions'
ART_KEY = 'articles'
OBJ_KEY = 'objects'
SYN_KEY = 'synonyms'


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

    @classmethod
    def spec_names(cls):
        return list(cls._lookup.keys())

    @classmethod
    def duality_for_ns(cls, namespace):
        return cls._lookup.get(namespace, None)

    @classmethod
    def breakqname(cls, ns_vs):
        return ns_vs.split('.')

    @classmethod
    def is_valid_verb(cls, ns, vs):
        spec = cls.duality_for_ns(ns)
        if vs in spec.initiates or vs in spec.reciprocates:
            return True
        else:
            return False

    @classmethod
    def reciprocate_depends_on(cls, ns, vs):
        spec = cls.duality_for_ns(ns)
        dpo = spec.depends_on(vs)
        if '.' in dpo:
            dns, dvs = cls.breakqname(dpo)
            dnspec = cls.duality_for_ns(dns)
            if dvs in dnspec.initiates:
                return dvs
            else:
                raise RuntimeError(
                    "{} not found in duality {}".format(dvs, dns))
        else:
            return dpo


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
    def prepositions(self):
        """Return a list of prepositions from spec"""
        pass

    @property
    @abstractmethod
    def articles(self):
        """Return a list of articles from spec"""
        pass

    @property
    @abstractmethod
    def objects(self):
        """Return a list of objects from spec"""
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
    def prepositions(self):
        """Return a list of prepositions from spec"""
        raise RuntimeError("hashblock spec does not support prepositions")

    @property
    def articles(self):
        """Return a list of articles from spec"""
        raise RuntimeError("hashblock spec does not support articles")

    @property
    def objects(self):
        """Return a list of objects from spec"""
        raise RuntimeError("hashblock spec does not support objects")

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
        iverbs = []
        for iv in self.specmap[INIT_KEY].keys():
            iverbs.append(iv)
            iverbs.extend(self.specmap[INIT_KEY][iv][SYN_KEY])
        self._initiates = iverbs
        rverbs = []
        for rv in self.specmap[RECP_KEY].keys():
            rverbs.append(rv)
            rverbs.extend(self.specmap[RECP_KEY][rv][SYN_KEY])
        self._reciprocates = rverbs

    @property
    def prepositions(self):
        """Return a list of prepositions from spec"""
        return self.specmap[VERBS_KEY][BASEVERBS_KEY][PRP_KEY]

    @property
    def articles(self):
        """Return a list of articles from spec"""
        return self.specmap[VERBS_KEY][BASEVERBS_KEY][ART_KEY]

    @property
    def objects(self):
        """Return a list of objects from spec"""
        return self.specmap[VERBS_KEY][BASEVERBS_KEY][OBJ_KEY]

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
