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

import logging
import shared.hblangparse.parse_context as pc
import shared.hblangparse.ast as ast

import modules.config as config
from modules.dualities import Duality

_context = None
_logger = None

# _base_terms = ['PREPOSITION', 'ARTICLES']
# _cfg_terms = ['PPARTNER', 'IVERB', 'RVERB', 'CCONJS']
# _dterms = [
#     ('PPARTNER', ['church', 'turing']),
#     ('IVERB', ['asks', 'ask']),
#     ('RVERB', ['tells', 'tell']),
#     ('CCONJS', ['price', 'prices', 'weight', 'volume', 'mass'])]

# _bterms = [
#     ('PREPOSITION', ['is', 'for', 'of', 'at', '@']),
#     ('ARTICLES', ['a', 'an', 'the'])]


def initialize_parse(logger=None):
    global _context
    global _logger

    if not logger:
        _logger = logging.getLogger()
    else:
        _logger = logger

    _context = pc.ParseContext

    for ns in config.agreement_list():
        d = Duality.duality_for_ns(ns)
        if d:
            dterms = [
                ('PPARTNER', config.agreement_partners(ns)),
                ('IVERB', d.initiates),
                ('RVERB', d.reciprocates),
                ('CCONJS', d.objects)]
            bterms = [
                ('PREPOSITION', d.prepositions),
                ('ARTICLES', d.articles)]
            _context.register_context(ns, dterms, bterms)
        else:
            _logger.warn("Namespace '{}' has no dualities".format(ns))


def parse_with_ns(ns, expression):
    # _logger.debug("Parse {} with namespace {}".format(expression, ns))
    results = _context.parse_expression(ns, expression)
    ast.ast_trace(results['ast'])
    results['ast'].eval()
