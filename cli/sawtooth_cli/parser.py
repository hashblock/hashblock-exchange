from scanner import tokens
from ply import yacc
import sys

def p_sign(p):
    '''
    sign : PLUS    
         | MINUS
    '''
    if p[1] == '+':
        p[0] = 1
    else:
        p[0] = -1

def p_digits(p):
    '''
    digits : DIGIT digits
           | DIGIT
    '''
    if len(p) > 1:
        p[0] = p[1]
    else:
        p[0] = p[1]

def p_error(p):
    print("Syntax error in input!")    

parser = yacc.yacc()
result = parser.parse('1')
print(result)

