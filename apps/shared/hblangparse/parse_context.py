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

from shared.hblangparse.lexer import Lexer
from shared.hblangparse.parser import Parser


# Exception types
class ContextRegistrar(Exception):
    pass


# Context Keys
_LEXER = 'lexer'
_PARSER = 'parser'
_DVERBS = 'dverbs'
_BVERBS = 'bverbs'


class ParseContext(object):
    _context_map = {}

    @classmethod
    def register_context(cls, namespace, domain_verbs, base_verbs):
        if not cls._context_map.get(namespace, None):
            lex = Lexer()
            lex.add_terms(domain_verbs, base_verbs)
            lexer = lex.get_lexer()
            parse_gen = Parser(lex)
            parse_gen.parse()
            cls._context_map[namespace] = {
                _LEXER: lexer,
                _PARSER: parse_gen.get_parser(),
                _DVERBS: domain_verbs,
                _BVERBS: base_verbs
            }
        else:
            pass

    @classmethod
    def parse_expression(cls, namespace, expression):
        if not cls._context_map.get(namespace, None):
            raise ContextRegistrar(
                "The namespace {} is not registered".format(namespace))
        else:
            context = cls._context_map[namespace]
            return {
                'expression': expression,
                'ast': context[_PARSER].parse(context[_LEXER].lex(expression))}
