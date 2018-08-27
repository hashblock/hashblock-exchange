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

from rply import ParserGenerator
import shared.hblangparse.ast as ast


class Parser():
    def __init__(self, mlexer):
        # A list of all token names accepted by the parser.
        self.pg = ParserGenerator(
            mlexer.get_tokens(),
            precedence=[
                ("left", ["PREPOSITION", "ARTICLES"]),
                ("left", ["QSYMBOL"]),
                ("left", ["PPARTNER", "IVERB", "RVERB", "CCONJS"])])

    def parse(self):
        @self.pg.production('program : request')
        def program(p):
            return p[0]

        @self.pg.production(
            'request : partner iverb partner conjunction quantity')
        @self.pg.production(
            """
            request : partner iverb partner article
             conjunction preposition quantity
             """)
        def i_request(p):
            ast_list = [x for x in p if x]
            return ast.Initiate(ast_list)

        @self.pg.production(
            """
            request : partner rverb partner
             conjunction address quantity ratio
             """)
        @self.pg.production(
            """
            request : partner rverb partner article
             conjunction preposition address preposition quantity ratio
             """)
        def r_request(p):
            ast_list = [x for x in p if x]
            return ast.Reciprocate(ast_list)

        @self.pg.production('partner : PPARTNER')
        def partner(p):
            # print("Partner {}".format(p))
            return ast.Partner(p[0].getstr())

        @self.pg.production('iverb : IVERB')
        def iverb(p):
            # print("I-Verb {}".format(p))
            return ast.Verb(p[0].getstr())

        @self.pg.production('rverb : RVERB')
        def rverb(p):
            # print("R-Verb {}".format(p))
            return ast.Verb(p[0].getstr())

        @self.pg.production('article : ARTICLES')
        def article(p):
            # print("Article {}".format(p))
            pass

        @self.pg.production('conjunction : CCONJS')
        def conjunction(p):
            # print("Conjunction {}".format(p))
            return ast.Conjunction(p[0].getstr())

        @self.pg.production('ratio : numerator denominator')
        @self.pg.production('ratio : numerator preposition  denominator')
        @self.pg.production('ratio : preposition numerator denominator')
        @self.pg.production(
            'ratio : preposition numerator preposition denominator')
        def ratio(p):
            return ast.Ratio([x[0] for x in p if x])

        @self.pg.production('numerator : quantity')
        def numerator(p):
            return p

        @self.pg.production('denominator : quantity')
        def denominator(p):
            return p

        @self.pg.production('quantity : magnitude unit asset')
        @self.pg.production('quantity : magnitude unit preposition asset')
        def quantity(p):
            return ast.Quantity([x for x in p if x])

        @self.pg.production('preposition : PREPOSITION')
        def preposition(p):
            pass

        @self.pg.production('unit : qsymbol')
        def unit(p):
            # print("Unit {}".format(p))
            return ast.Unit(p)

        @self.pg.production('asset : qsymbol')
        def asset(p):
            # print("Asset {}".format(p))
            return ast.Asset(p)

        @self.pg.production('address : HEX')
        def address(p):
            # print("Address {}".format(p))
            return ast.Address(p[0].getstr())

        @self.pg.production('magnitude : INTEGER')
        @self.pg.production('magnitude : REAL')
        def magnitude(p):
            # print("Magnitude {}".format(p))
            return ast.Magnitude(p[0].getstr())

        @self.pg.production('qsymbol : QSYMBOL')
        def qsymbol(p):
            nsterm = p[0].getstr().split('.')
            # print("QSymbol {}".format(nsterm))
            return ast.QSymbol(nsterm[0], nsterm[1])

        # @self.pg.production('symbol : SYMBOL')
        # def symbol(p):
        #     print("Symbol {}".format(p))
        #     return ast.Symbol(p[0].getstr())

        @self.pg.error
        def error_handle(state, token):
            raise ValueError(
                "%s where it wasn't expected" % token)

    def get_parser(self):
        return self.pg.build()
