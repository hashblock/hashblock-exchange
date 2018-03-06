from ply import lex

reserved = {
   'of' : 'OF',
   'for' : 'FOR'
}

tokens = [
    'PLUS',
    'MINUS',
    'LPAR',
    'RPAR',
    'LBRACE',
    'RBRACE',
    'SOLIDUS',
    'AT',
    'DOT',
    'DIGIT',
    'PREFIX',
    'SYMBOL',
    'ATOM' ] + list(reserved.values())

t_PLUS      = r'\+'
t_MINUS     = r'\-'
t_LPAR      = r'\('
t_RPAR      = r'\)'
t_LBRACE    = r'\{'
t_RBRACE    = r'\}'
t_SOLIDUS   = r'\/'
t_AT        = r'\@'
t_DOT       = r'\.'
t_DIGIT     = r'\d'
t_ignore    = ' \t'

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

lexer = lex.lex()

#lexer.input("+15")
#for tok in iter(lexer.token, None):
#    print(repr(tok.type), repr(tok.value))
