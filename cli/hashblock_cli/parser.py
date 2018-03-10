from sawtooth_cli.scanner import tokens
from ply import yacc
import sys


def p_event_quantity(p):
    '''
    event_quantity : quantity FOR quantity
                   | quantity
    '''
    if len(p) == 4:
        p[0] = ('event_quantity_ratio', p[1],p[3])
    elif len(p) == 2:
        p[0] = ('event_quantity', p[1])


def p_quantity(p):
    '''
    quantity : SOLIDUS term 
             | SYMBOL term 
             | term
    '''
    if len(p) == 3:
        p[0] = ('quantity_prefix',p[1],p[2])
    elif len(p) == 2:
        p[0] = ('quantity',p[1])


def p_term(p):
    '''
    term : term DOT component
         | term SOLIDUS component
         | component
    '''
    if len(p) == 4:
        p[0] = ('term_binary', p[2], p[1],p[3])
    elif len(p) == 2:
        p[0] = ('term',p[1])


def p_component(p):
    '''
    component : annotatable ANNOTATION
              | annotatable
              | ANNOTATION
              | factor
              | LPAR term RPAR
    '''
    if len(p) == 4:
        p[0] = ('component', p[2])
    elif len(p) == 3:
        p[0] = ('component_binary', p[1], p[2])
    elif len(p) == 2:
        p[0] = ('component_unary', p[1])
         

def p_annotatable(p):
    '''
    annotatable : simple_unit exponent
                | simple_unit
    '''
    if len(p) == 3:
        p[0] = ('annotatable_exponent', p[1], p[2])
    elif len(p) == 2:
        p[0] = ('annotatable', p[1])


def p_simple_unit(p):
    '''
    simple_unit : ATOM
                | PREFIX ATOM
    '''
    if len(p) == 3:
        p[0] = ('simple_unit_prefix', p[2], p[1])
    elif len(p) == 2:
        p[0] = ('simple_unit', p[1])


def p_exponent(p):
    '''
    exponent : sign digits
             | digits
    '''
    if len(p) == 3:
        p[0] = ('exponent', p[1]*int(p[2]))
    elif len(p) == 2:
        p[0] = ('exponent', int(p[1]))


def p_sign(p):
    '''
    sign : PLUS
         | MINUS
    '''
    if p[1] == '+':
        p[0] = 1
    elif p[1] == '-':
        p[0] = -1


def p_factor(p):
    '''
    factor : digits ANNOTATION
           | digits
    '''
    if len(p) == 3:
        p[0] = ('factor_annotation', int(p[1]), p[2])
    elif len(p) == 2:
        p[0] = ('factor', int(p[1]))


def p_digits(p):
    '''
    digits : DIGIT digits
           | DIGIT
    '''
    if len(p) == 3:
        p[0] = p[1]+p[2]
    elif len(p) == 2:
        p[0] = p[1]


def p_error(p):
    print("Syntax error in input!",p)    


parser = yacc.yacc()
#result = parser.parse('$10 {USD}')
#print(result)
#parser = yacc.yacc()
#result = parser.parse('1.bag {peanuts}')
#print(result)
#parser = yacc.yacc()
#result = parser.parse('$1 {USD} for 1.bag {peanuts}')
#print(result)
