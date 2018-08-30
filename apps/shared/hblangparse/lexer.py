# ------------------------------------------------------------------------------
# Copyright 2018 Frank V. Castellucci
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

from rply import LexerGenerator

""" Hashblock lexer
initiate: church asks turing the price for 5 bags of peanuts
<plus church> <verb asks> <minus turing> <article the>
<coordinating conjunction price> <preposition for>
<magnitude 5> <unit bags> <preposition of> <asset peanuts>

reciprocate: turing tells churh the price for 98343faaf is
    10 $ USD at 1 $ USD for 1 bag peanuts

reciprocate: <plus> <verb> <minus> <article> <coordinating conjunction>
    <preposition> <address 70 char hex>
    <state-of-being-verb> <magnitude> <unit> <asset>
    <preposition> <magnitude> <unit> <asset>
    <preposition> <magnitude> <unit> <asset>

"""

import re


class LexException(Exception):
    pass


class Lexer():
    _base_terms = ['PREPOSITION', 'ARTICLES']
    _cfg_terms = ['PPARTNER', 'IVERB', 'RVERB', 'CCONJS']

    def __init__(self):
        self.lexer = LexerGenerator()

    @property
    def lexgen(self):
        return self.lexer

    def _add_base(self, term, tlist):
        """Adds tokens to the generator"""
        print("Base add {} with {}".format(term, tlist))
        if term in self._base_terms:
            blist = [r'\b' + x + r'\b' for x in tlist]
            self.lexgen.add(term, "|".join(blist), flags=re.I)
        else:
            raise LexException("Unsupported term {}".format(term))

    def _add_dyn(self, term, tlist):
        """Adds tokens to the generator"""
        print("Dyn add {} with {}".format(term, tlist))
        if term in self._cfg_terms:
            blist = [r'\b' + x + r'\b' for x in tlist]
            self.lexgen.add(term, "|".join(blist), flags=re.I)
        else:
            raise LexException("Unsupported term {}".format(term))

    def add_terms(self, dlist, blist):
        [self._add_dyn(x, y) for x, y in dlist]
        [self._add_base(x, y) for x, y in blist]

    def _add_tokens(self):
        # Prepositions
        # self.lexer.add('PREPOSITION', r'is|for|of|at|@', flags=re.I)
        # Articles
        self.lexer.add('ARTICLES', r'a|an|the', flags=re.I)
        # Address
        self.lexer.add('HEX', r"[0-9a-fA-F]{70}")
        # Magnitudes
        self.lexer.add('REAL', r"[0-9]+\.[0-9]+")
        self.lexer.add('INTEGER', r"[0-9]+")
        # Qualified Symbols (e.g. sysmtem.key)
        self.lexer.add(
            'QSYMBOL', r'[a-zA-Z]([a-zA-Z0-9]*?)\.[!-~]+')

        # Ignore spaces
        self.lexer.ignore(r"\s+")

    def get_tokens(self):
        return [x.name for x in self.lexer.rules]

    def get_lexer(self):
        self._add_tokens()
        return self.lexer.build()
