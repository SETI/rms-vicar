##########################################################################################
# vicar/_LABEL_GRAMMAR.py
##########################################################################################
"""\
_LABEL_GRAMMAR.parse_string(text) receives the contents of VICAR label and returns a list
of tuples. Each tuple defines the name and value of a label parameter. When the formatting
of that "name=value" pair is non-standard, the tuple provides additional information
indicating how the name and value were formatted. The tuple contains up to six items:
   (name, value, format, after_name, before_value, after_value)
where:
  name            VICAR parameter name.
  value           Value of the parameter, represented by an int, float, string, or list.
  format          optional format by which this value is represented in the label;
                  included only for ints and floats and only if the format is different
                  from the representation produced by str(value).
  name_blanks     number of blank characters after the name and before the equal sign;
                  included only if this number is nonzero.
  value_blanks    number of blank characters after the equal sign and before the value;
                  included if this number is nonzero or if name_blanks is nonzero.
  sep_blanks      number of blank characters after this value and before either the next
                  value or the end of the label; included if this value does not equal 2
                  or if either of the previous values is nonzero.

In other words, the possible tuples returned are these:
  (name, value)
  (name, value, format)
  (name, value, format, sep_blanks)
  (name, value, format, value_blanks, sep_blanks)
  (name, value, format, name_blanks, value_blanks, sep_blanks)
  (name, value, sep_blanks)
  (name, value, value_blanks, sep_blanks)
  (name, value, name_blanks, value_blanks, sep_blanks)

In summary:
  - the first two items in the tuple are always the name and value.
  - the third item, if present and a string, is the format.
  - subsequent items are integers that define the number of blank characters surrounding
    the equal sign and following the value's end; these are included only if one or more
    of their values are non-standard.

If the label value is a list, then each value in the parsed list is an int, float,
or tuple containing up to four values:
  value           the value of this item as an in int, float, or string.
  format          optional format by which this value is represented in the label;
                  included only for ints and floats and only if the format is different
                  from the representation produced by str(value).
  blanks_before   number of blanks before the item and after the left parenthesis or
                  comma; included only if this number is nonzero.
  blanks_after    number of blanks after the value and before the next comma or the right
                  parenthesis; included if this number is nonzero or if blanks_before is
                  nonzero.

In other words, the possible items in a parsed list are these:
  value
  (value, format)
  (value, format, blanks_after)
  (value, format, blanks_before, blanks_after)
  (value, blanks_after)
  (value, blanks_before, blanks_after)

Most users will only care about the name and value, but the remaining information in each
tuple is included in case the user wants to write out a label string that preserves the
formatting of the original source.
"""
##########################################################################################

from pyparsing import (CharsNotIn,
                       Combine,
                       FollowedBy,
                       Literal,
                       nums,
                       oneOf,
                       OneOrMore,
                       Optional,
                       ParserElement,
                       StringEnd,
                       Suppress,
                       White,
                       Word,
                       ZeroOrMore)

ParserElement.set_default_whitespace_chars(' ')

BREAK = ((ZeroOrMore(White(' ')) + (FollowedBy(oneOf(', )'))
                                    | (Suppress(ZeroOrMore('\0')) + StringEnd())))
         | OneOrMore(White(' \t\n\r')))

OPT_WHITE = ZeroOrMore(White(' '))

############################################
# INTEGER
############################################

def _int_info(token):
    rstripped = token.rstrip()
    len_rstripped = len(rstripped)
    after = len(token) - len_rstripped

    stripped = rstripped.lstrip()
    len_stripped = len(stripped)
    before = len_rstripped - len_stripped

    value = int(stripped)

    plus = '+' if stripped[0] == '+' else ''
    unsigned = stripped[1:] if stripped[0] in '+-' else stripped
    zero = unsigned[0] == '0' and len(unsigned) > 1
    if zero:
        fmt = '%' + plus + '0' + str(len_stripped) + 'd'
    elif plus:
        fmt = '%+d'
    else:
        fmt = ''

    return (value, fmt, before, after)

INT = Word(nums)
OPT_INT = Optional(INT)
OPT_SIGN = Optional(oneOf('+ -'))

INTEGER = Combine(OPT_WHITE + OPT_SIGN + INT + BREAK)
INTEGER.set_name('INTEGER')
INTEGER.set_parse_action(lambda s,l,t: _int_info(t[0]))

############################################
# FLOAT
############################################

def _float_info(token):
    rstripped = token.rstrip()
    len_rstripped = len(rstripped)
    after = len(token) - len_rstripped

    stripped = rstripped.lstrip()
    len_stripped = len(stripped)
    before = len_rstripped - len_stripped

    value = float(stripped)

    mantissa, e, expo = stripped.partition('e')
    plus = '+' if mantissa[0] == '+' else ''
    unsigned = mantissa[1:] if mantissa[0] in '+-' else mantissa
    (head, dot, tail) = unsigned.partition('.')

    if e:
        prec = len(head) + len(tail) - 1
        letter = 'E'
    else:
        prec = len(tail)
        letter = 'f'

    fmt = '%#' + plus + '.' + str(prec) + letter

    return (value, fmt, before, after)

DOT = Literal('.')

EXPO = Combine(Suppress(oneOf('e E d D')) + OPT_SIGN + INT)
EXPO.set_parse_action(lambda s,l,t: 'e' + t[0])
OPT_EXPO = Optional(EXPO)

FLOAT_W_INT  = Combine(OPT_WHITE + OPT_SIGN + INT + DOT + OPT_INT + OPT_EXPO + BREAK)
FLOAT_WO_INT = Combine(OPT_WHITE + OPT_SIGN + DOT + INT + OPT_EXPO + BREAK)
FLOAT_WO_DOT = Combine(OPT_WHITE + OPT_SIGN + INT + EXPO + BREAK)
FLOAT        = FLOAT_W_INT | FLOAT_WO_INT | FLOAT_WO_DOT
FLOAT.set_name('FLOAT')
FLOAT.set_parse_action(lambda s,l,t: _float_info(t[0]))

############################################
# STRING
############################################

def _str_info(token):
    rstripped = token.rstrip()
    after = len(token) - len(rstripped)

    stripped = rstripped.lstrip()
    before = len(rstripped) - len(stripped)

    value = stripped[1:-1].replace("''", "'")
    return (value, '', before, after)

QUOTE = Literal("'")
QQUOTE = Literal("''")
STRING = Combine(OPT_WHITE + QUOTE + ZeroOrMore(CharsNotIn("'") | QQUOTE) + QUOTE + BREAK)
STRING.set_name('STRING')
STRING.set_parse_action(lambda s,l,t: _str_info(t[0]))

############################################
# LIST
############################################

def _list_info(tokens):
    before = len(tokens[0])
    after  = len(tokens[-1])

    return (tokens[1:-1], '', before, after)

SCALAR = INTEGER | FLOAT | STRING

LPAREN = Combine(OPT_WHITE + Suppress(Literal('(')))
RPAREN = Combine(Suppress(Literal(')')) + BREAK)
COMMA  = Suppress(Literal(','))

LIST = LPAREN + SCALAR + ZeroOrMore(COMMA + SCALAR) + RPAREN
LIST.set_name('LIST')
LIST.set_parse_action(lambda s,l,t: _list_info(t))

############################################
# VALUE
############################################

VALUE = SCALAR | LIST

############################################
# NAME
############################################

def _name_info(token):
    rstripped = token.rstrip()
    after = len(token) - len(rstripped)
    return (rstripped, after)

ALPHAS = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
ALNUMS = ALPHAS + '0123456789_'
NAME = Combine(Word(ALPHAS, ALNUMS, max=32) + OPT_WHITE)
NAME.set_name('NAME')
NAME.set_parse_action(lambda s,l,t: _name_info(t[0]))

############################################
# STATEMENT
############################################

def _statement_info(tokens):
    (name, blanks0) = tokens[0]
    (value, fmt, blanks1, blanks2) = tokens[1]

    # Strip unnecessary formatting info from the items in a list
    if isinstance(value, list):
        new_value = []
        for (item_value, item_fmt, before, after) in value:
            result = [item_value]
            if item_fmt:
                result.append(item_fmt)
            if before:
                result += [before, after]
            elif after != 0:
                result += [after]

            if len(result) == 1:
                new_value.append(result[0])
            else:
                new_value.append(tuple(result))

        value = new_value

    # Construct the result as a new tuple
    result = [name, value]
    if fmt:
        result.append(fmt)

    # Append up to three counts of blank values
    if blanks0:
        result += [blanks0, blanks1, blanks2]
    elif blanks1:
        result += [blanks1, blanks2]
    elif blanks2 != 2:
        result += [blanks2]

    return tuple(result)

EQUAL = Suppress(Literal('='))
STATEMENT = NAME + EQUAL + VALUE
STATEMENT.set_name('STATEMENT')
STATEMENT.set_parse_action(lambda s,l,t: _statement_info(t))

############################################
# _LABEL_GRAMMAR
############################################

_LABEL_GRAMMAR = OneOrMore(STATEMENT) + StringEnd()
_LABEL_GRAMMAR.set_name('_LABEL_GRAMMAR')

##########################################################################################
