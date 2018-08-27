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

import argparse
# import logging
import os
import sys
from ast import ast_trace
from parse_context import ParseContext

tests = [
    """
    church asks turing price 5 purchasing.bag food.peanuts
    """,
    """
    church asks turing the price for 5 purchasing.bag of food.peanuts
    """,
    """
    turing tells church price
    95768292a8fd1de17daa001fdd0000000000000000000000000000cee0bfacf900bc6b
    10 currency.$ iso4217.USD
    1 currency.$ iso4217.USD
    1 purchasing.bag food.peanuts
    """,
    """
    turing tells church the price
    for 95768292a8fd1de17daa001fdd0000000000000000000000000000cee0bfacf900bc6b
    is 10 currency.$ iso4217.USD
    at 1 currency.$ iso4217.USD
    for 1 purchasing.bag food.peanuts
    """]


def create_parser(prog_name):
    """Bootstrap command line parser
    """
    aparser = argparse.ArgumentParser(
        prog=prog_name,
        description='Bootstrap FOIDL generator.',
        epilog='This process is required to build FOIDL',
        formatter_class=argparse.RawDescriptionHelpFormatter)

    aparser.add_argument(
        '-e',
        help='AST evaluate - Debugging')
    aparser.add_argument(
        '-t',
        help='AST trace - Debugging')
    return aparser


_dterms = [
    ('PPARTNER', ['church', 'turing']),
    ('IVERB', ['asks', 'ask']),
    ('RVERB', ['tells', 'tell']),
    ('CCONJS', ['price', 'prices', 'weight', 'volume', 'mass'])]

_bterms = [
    ('PREPOSITION', ['is', 'for', 'of', 'at', '@']),
    ('ARTICLES', ['a', 'an', 'the'])]


def process_ast(args, ast):
    print()
    print("Expression => {}".format(ast['expression']))
    if args.t:
        print("AST Trace")
        ast_trace(ast['ast'])
    if args.e:
        print("AST Evaluate (print)")
        ast['ast'].eval()


def main(prog_name=os.path.basename(sys.argv[0]), args=None,
         with_loggers=True):
    """Main entry point for parser bootstrap
    """
    if args is None:
        args = sys.argv[1:]
    aparser = create_parser(prog_name)
    args = aparser.parse_args(args)
    ParseContext.register_context('demo', _dterms, _bterms)
    # mlex = Lexer()
    # mlex.add_terms(_dterms, _bterms)
    # lexer = mlex.get_lexer()
    # pg = Parser(mlex)
    # pg.parse()
    # parser = pg.get_parser()
    for t in tests:
        process_ast(args, ParseContext.parse_expression('demo', t))
        # parse_string(args, lexer, t, parser)


if __name__ == '__main__':
    main()
