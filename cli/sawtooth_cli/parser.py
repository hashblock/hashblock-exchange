from scanner import tokens
from ply import yacc
import sys


def p_quantity(p):
    '''
    quantity : main_term event_quantity
    '''
    p[0] = ('quantity_of', p[1])

def p_event_quantity(p):
    '''
    event_quantity : FOR event_quantity
                   | OF main_term
                   | main_term
    '''
    p[0] = p[1]    


def p_main_term(p):
    '''
    main_term : SOLIDUS term 
              | SYMBOL term
              | term
    '''
    if len(p) == 3:
        p[0] = ('main_term_'+p[1],p[2])
    else:
        p[0] = ('main_term',p[1])


def p_term(p):
    '''
    term : term DOT component
         | term SOLIDUS component
         | component
    '''
    if len(p) == 4:
        p[0] = ('term_'+p[2],p[1],p[3])
    else:
        p[0] = ('term',p[1])

def p_component(p):
    '''
    component : annotatable annotation
              | annotatable
              | annotation
              | factor
              | LPAR term RPAR
    '''
    if len(p) == 3:
        p[0] = ('component', p[1], p[2])
    else:
        p[0] = ('component', p[1], None)
         

def p_annotation(p):
    '''
    annotation : LBRACE RBRACE
    '''
    p[0] = ('annotation')


def p_annotatable(p):
    '''
    annotatable : simple_unit exponent
                | simple_unit
    '''
    p[0] = ('annotatable', p[1])


def p_simple_unit(p):
    '''
    simple_unit : ATOM
                | PREFIX ATOM
    '''
    if len(p) == 3:
        p[0] = ('simple_unit', p[2], p[1])
    else:
        p[0] = ('simple_unit', p[1], 1)


def p_exponent(p):
    '''
    exponent : sign digits
             | digits
    '''
    if len(p) == 3:
        p[0] = ('exponent', p[1]*int(p[2]))
    else:
        p[0] = ('exponent', int(p[1]))


def p_sign(p):
    '''
    sign : PLUS
         | MINUS
    '''
    if p[1] == '+':
        p[0] = 1
    else:
        p[0] = -1


def p_factor(p):
    '''
    factor : digits
    '''
    p[0] = ('factor', int(p[1]))


def p_digits(p):
    '''
    digits : DIGIT digits
           | DIGIT
    '''
    if len(p) == 3:
        p[0] = p[1]+p[2]
    else:
        p[0] = p[1]


def p_error(p):
    print("Syntax error in input!",p)    


parser = yacc.yacc()
result = parser.parse('$10 of USD')
print(result)
parser = yacc.yacc()
result = parser.parse('1.bag of peanuts')
print(result)
parser = yacc.yacc()
result = parser.parse('$1 of USD for 1.bag of peanuts')
print(result)
#result = parser.parse('$10 of USD @ $1 of USD for 1.bag of peanuts')

