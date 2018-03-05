from ply import lex
from ply import yacc
import sys

reserved = {
   'of' : 'OF'
}

tokens = [
    'PLUS',
    'MINUS',
    'LPAR',
    'RPAR',
    'SOLIDUS',
    'STAR',
    'DOT',
    'DIGITS',
    'PREFIX',
    'SYMBOL',
    'ATOM' ] + list(reserved.values())

t_PLUS      = r'\+'
t_MINUS     = r'\-'
t_LPAR      = r'\('
t_RPAR      = r'\)'
t_SOLIDUS   = r'\/'
t_STAR      = r'\*'
t_DOT       = r'\.'


def t_DIGITS(t):
    r'\d+'
    t.value = int(t.value)
    return t

def t_PREFIX(t): 
    r'^[Y|Z|E|P|T|G|M|k|h|da|d|c|m|u|n|p|f|a|z|y]'
    return t

def t_SYMBOL(t): 
    r'^[$]'
    return t

def t_ATOM(t):
    r'[A-Za-z]+'
    if t.value in reserved:
        t.type = reserved[ t.value ]
    return t      

def t_error(t):
    raise TypeError("Unknown text '%s'" % (t.value,))

lex.lex()
lex.input("15")
for tok in iter(lex.token, None):
    print(repr(tok.type), repr(tok.value))

def p_factor(p):
    'factor : digits'
    p[0] = p[1]

def p_error(p):
    print("Syntax error in input!")    

parser = yacc.yacc()
result = parser.parse("15")

