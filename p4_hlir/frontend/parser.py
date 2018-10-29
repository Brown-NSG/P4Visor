# Copyright 2013-present Barefoot Networks, Inc. 
# 
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# 
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from ply import yacc
from tokenizer import P4Lexer
from ast import *

class P4Parser:
    def __init__(self):
        self.lexer = P4Lexer()
        self.lexer.build()
        self.tokens = self.lexer.tokens

        self.parser = yacc.yacc(module = self,
                                write_tables=0,
                                debug=False,
                                start = 'p4_objects')

        self.errors_cnt = 0
        self.current_pragmas = set()
        
        
    def parse(self, data, filename = ''):
        # self.lexer.filename = filename
        self.lexer.reset_lineno()
        p4_objects = self.parser.parse(input = data,
                                       lexer = self.lexer)
        self.errors_cnt += self.lexer.errors_cnt
        # print 'ZP pars-001 p4_objects:', p4_objects
        return p4_objects, self.errors_cnt

    ##
    ## Precedence and associativity of operators
    ##
    precedence = (
        ('left', 'RPAREN'),
        ('left', 'LOR'),
        ('left', 'LAND'),
        ('left', 'OR'),
        ('left', 'XOR'),
        ('left', 'AND'),
        ('left', 'EQ', 'NE'),
        ('left', 'GT', 'GE', 'LT', 'LE'),
        ('left', 'RSHIFT', 'LSHIFT'),
        ('left', 'PLUS', 'MINUS'),
        ('left', 'TIMES', 'DIVIDE', 'MOD'),
        ('right', 'UMINUS'),
        ('right', 'VALID'),
        ('right', 'NOT'),
        ('right', 'LNOT'),
        ('left', 'LPAREN')
    )

    def print_error(self, lineno, msg):
        self.errors_cnt += 1
        print "parse error in file", self.lexer.filename, "at line", lineno, ":", msg

    def get_filename(self):
        return self.lexer.filename

    ##
    ## Grammar productions
    ##

    def p_empty(self, p):
        """ empty :
        """
        pass
    
    def p_p4_objects(self, p):
        """ p4_objects : p4_declaration_list
                       | empty
        """
        if p[1] is None:
            p[0] = []
        else:
            p[0] = p[1]

    def p_p4_declaration_list_1(self, p):
        """ p4_declaration_list : p4_declaration_or_pragma
        """
        if p[1]:
            p[0] = [p[1]]
        else:
            p[0] = []

    def p_p4_declaration_list_2(self, p):
        """ p4_declaration_list : p4_declaration_list p4_declaration_or_pragma
        """
        if p[2]:
            p[0] = p[1] + [p[2]]
        else:
            p[0] = p[1]

    def p_p4_declaration_list_error_1(self, p):
        """ p4_declaration_list : p4_declaration_list error
        """
        p[0] = p[1]
        self.print_error(p.lineno(2),
                         "Invalid P4 declaration: '%s' in not a valid p4 object" \
                         % p[2].value)

    def p_p4_declaration_or_pragma_1(self, p):
        """ p4_declaration_or_pragma : p4_declaration
        """
        p[0] = p[1]
        if p[0]:
            p[0]._pragmas = self.current_pragmas
        self.current_pragmas = set()

    def p_p4_declaration_or_pragma_2(self, p):
        """ p4_declaration_or_pragma : PRAGMA STR
        """
        self.current_pragmas.add(p[2])


# HEADER TYPE

    def p_p4_declaration_1(self, p):
        """ p4_declaration : header_type_declaration
        """
        p[0] = p[1]

    def p_header_type_declaration_1(self, p):
        """ header_type_declaration : HEADER_TYPE ID \
                                      LBRACE header_dec_body RBRACE
        """
        if p[4] is not None:
            layout, length, max_length = p[4]
            p[0] = P4HeaderType(self.get_filename(), p.lineno(1),
                                p[2], layout, length, max_length)

    def p_header_type_declaration_error_1(self, p):
        """ header_type_declaration : HEADER_TYPE ID \
                                      LBRACE error RBRACE
        """
        self.print_error(p.lineno(1),
                         "Invalid body for header_type declaration")

    def p_header_type_declaration_error_2(self, p):
        """ header_type_declaration : HEADER_TYPE error RBRACE
        """
        self.print_error(p.lineno(1),
                         "Invalid header_type declaration")

    # this one is impossible to recover from (missing brace)
    def p_header_type_declaration_error_3(self, p):
        """ header_type_declaration : HEADER_TYPE error
        """
        self.print_error(p.lineno(1),
                         "Invalid header_type declaration")

    def p_header_dec_body(self, p):
        """ header_dec_body : FIELDS LBRACE field_dec_list RBRACE \
                              header_length_opt header_max_length_opt
        """
        p[0] = (p[3], p[5], p[6])

    def p_header_dec_body_error_1(self, p):
        """ header_dec_body : FIELDS LBRACE error RBRACE \
                              header_length_opt header_max_length_opt
        """
        self.print_error(p.lineno(1),
                         "invalid field list in header_type declaration")

    def p_header_length_opt_1(self, p):
        """ header_length_opt : LENGTH COLON length_exp SEMI
        """
        p[0] = p[3]

    def p_header_length_opt_1_error_1(self, p):
        """ header_length_opt : LENGTH COLON error SEMI
        """
        self.print_error(p.lineno(1),
                         "invalid length attribute in "\
                         "header_type declaration, "\
                         "attribute must be a valid expression")

    def p_header_length_opt_1_error_2(self, p):
        """ header_length_opt : LENGTH error SEMI
        """
        self.print_error(p.lineno(1),
                         "invalid length attribute in "\
                         "header_type declaration")

    def p_header_length_opt_2(self, p):
        """ header_length_opt : empty
        """
        p[0] = None

    def p_header_max_length_opt_1(self, p):
        """ header_max_length_opt : MAX_LENGTH COLON const_value SEMI
        """
        p[0] = p[3]

    def p_header_max_length_opt_1_error_1(self, p):
        """ header_max_length_opt : MAX_LENGTH COLON error SEMI
        """
        self.print_error(p.lineno(1),
                         "invalid max_length attribute in "\
                         "header_type declaration, "\
                         "attribute must be a positive constant value")

    def p_header_max_length_opt_1_error_2(self, p):
        """ header_max_length_opt : MAX_LENGTH error SEMI
        """
        self.print_error(p.lineno(1),
                         "invalid max_length attribute in "\
                         "header_type declaration")

    def p_header_max_length_opt_2(self, p):
        """ header_max_length_opt : empty
        """
        p[0] = None

    def p_field_dec_list_1(self, p):
        """ field_dec_list : field_dec
        """
        p[0] = [p[1]]

    def p_field_dec_list_2(self, p):
        """ field_dec_list : field_dec_list field_dec
        """
        p[0] = p[1] + [p[2]]

    def p_field_dec_1(self, p):
        """ field_dec : ID COLON bit_width SEMI
        """
        p[0] = (p[1], p[3], []) # 3-tuple name, width, attributes

    def p_field_dec_2(self, p):
        """ field_dec : ID COLON bit_width LPAREN field_mod_list RPAREN SEMI
        """
        p[0] = (p[1], p[3], p[5])

    def p_field_dec_error_1(self, p):
        """ field_dec : ID COLON error SEMI
        """
        self.print_error(p.lineno(1),
                         "invalid bit width in field declaration, "\
                         "must be positive constant value or *")

    def p_field_dec_error_2(self, p):
        """ field_dec : ID COLON bit_width LPAREN error RPAREN SEMI
        """
        self.print_error(p.lineno(1),
                         "invalid field modifiers list in field declaration")

    def p_field_dec_error_3(self, p):
        """ field_dec : error SEMI
        """
        self.print_error(p.lineno(1),
                         "invalid field declaration")

    def p_field_mod_list_1(self, p):
        """ field_mod_list : field_mod
        """
        p[0] = [p[1]]

    def p_field_mod_list_2(self, p):
        """ field_mod_list : field_mod_list COMMA field_mod
        """
        p[0] = p[1] + [p[3]]

    def p_field_mod(self, p):
        """ field_mod : SIGNED
                      | SATURATING
        """
        p[0] = p[1]  # "signed", "saturating"

    def p_bit_width_1(self, p):
        """ bit_width : const_value
        """
        p[0] = p[1]

    def p_bit_width_2(self, p):
        """ bit_width : TIMES
        """
        p[0] = p[1]   # "*"

    def p_const_value_1(self, p):
        """ const_value : INT_CONST_HEX
        """
        p[0] = P4Integer(self.get_filename(), p.lineno(1), int(p[1], 16))

    def p_const_value_2(self, p):
        """ const_value : INT_CONST_DEC
        """
        p[0] = P4Integer(self.get_filename(), p.lineno(1), int(p[1], 10))

    def p_const_value_with_width_1(self, p):
        """ const_value_with_width : INT_CONST_DEC APOSTROPHE INT_CONST_DEC
        """
        p[0] = P4Integer(self.get_filename(), p.lineno(1),
                         int(p[3], 10), int(p[1], 10))

    def p_const_value_with_width_2(self, p):
        """ const_value_with_width : INT_CONST_DEC APOSTROPHE INT_CONST_HEX
        """
        p[0] = P4Integer(self.get_filename(), p.lineno(1),
                         int(p[3], 16), int(p[1], 10))

    def p_bool_value(self, p):
        """ bool_value : TRUE
                       | FALSE
        """
        value = (p[1] == "true")
        p[0] = P4Bool(self.get_filename(), p.lineno(1), value)

    def p_length_exp(self, p):
        """ length_exp : arith_exp
        """
        p[0] = p[1]

    def p_arith_exp_1(self, p):
        """ arith_exp : arith_exp PLUS arith_exp
                      | arith_exp MINUS arith_exp
                      | arith_exp TIMES arith_exp
                      | arith_exp LSHIFT arith_exp
                      | arith_exp RSHIFT arith_exp
                      | arith_exp MOD arith_exp
                      | arith_exp DIVIDE arith_exp
                      | arith_exp AND arith_exp
                      | arith_exp OR arith_exp
                      | arith_exp XOR arith_exp

        """
        p[0] = P4BinaryExpression(self.get_filename(), p.lineno(1),
                                  p[2], p[1], p[3])

    def p_arith_exp_2(self, p):
        """ arith_exp : LPAREN arith_exp RPAREN
        """
        p[0] = p[2]

    def p_arith_exp_3(self, p):
        """ arith_exp : NOT arith_exp
                      | MINUS arith_exp %prec UMINUS
                      | PLUS arith_exp %prec UMINUS
        """
        p[0] = P4UnaryExpression(self.get_filename(), p.lineno(1), p[1], p[2])

    def p_arith_exp_4(self, p):
        """ arith_exp : const_value
        """
        p[0] = p[1]

    def p_arith_exp_5(self, p):
        """ arith_exp : ID
        """
        p[0] = P4RefExpression(self.get_filename(), p.lineno(1), p[1])

    def p_arith_exp_6(self, p):
        """ arith_exp : field_ref
        """
        p[0] = p[1]


# INSTANCE DECLARATION

    def p_p4_declaration_2(self, p):
        """ p4_declaration : header_instance
                           | metadata_instance
        """
        p[0] = p[1]

    def p_header_instance_1(self, p):
        """ header_instance : HEADER ID ID SEMI
        """
        p[0] = P4HeaderInstanceRegular(self.get_filename(), p.lineno(1),
                                       p[2],
                                       p[3])

    def p_header_instance_2(self, p):
        """ header_instance : HEADER ID ID LBRACKET const_value RBRACKET SEMI
        """
        p[0] = P4HeaderInstanceRegular(self.get_filename(), p.lineno(1),
                                       p[2],
                                       p[3], size = p[5])

    def p_header_instance_error_1(self, p):
        """ header_instance : HEADER error SEMI
        """
        self.print_error(p.lineno(1),
                         "Invalid header instance declaration")

    def p_header_instance_error_2(self, p):
        """ header_instance : HEADER error
        """
        self.print_error(p.lineno(1),
                         "Missing semi-colon in header instance declaration")

    def p_metadata_instance_1(self, p):
        """ metadata_instance : METADATA ID ID SEMI
        """
        p[0] = P4HeaderInstanceMetadata(self.get_filename(), p.lineno(1),
                                        p[2],
                                        p[3])

    def p_metadata_instance_2(self, p):
        """ metadata_instance : METADATA ID ID \
                                LBRACE metadata_initializers RBRACE SEMI
        """
        p[0] = P4HeaderInstanceMetadata(self.get_filename(), p.lineno(1),
                                        p[2],
                                        p[3], initializer = p[5])

    def p_metadata_instance_2_error_1(self, p):
        """ metadata_instance : METADATA ID ID LBRACE error RBRACE SEMI
        """
        self.print_error(p.lineno(1),
                         "Invalid metadata initializer")

    def p_metadata_instance_error_1(self, p):
        """ metadata_instance : METADATA error SEMI
        """
        self.print_error(p.lineno(1),
                         "Invalid metadata instance declaration")

    def p_metadata_instance_error_2(self, p):
        """ metadata_instance : METADATA error
        """
        self.print_error(p.lineno(1),
                         "Missing semi-colon in metadata instance declaration")

    def p_metadata_initializer_1(self, p):
        """ metadata_initializers : metadata_initializers initializer SEMI
        """
        p[0] = p[1] + [p[2]]

    def p_metadata_initializer_2(self, p):
        """ metadata_initializers : initializer SEMI
        """
        p[0] = [p[1]]

    def p_metadata_initializer_error_1(self, p):
        """ metadata_initializers : error SEMI
        """
        self.print_error(p.lineno(1),
                         "Invalid satement in metadata initializer")

    def p_metadata_initializer_error_2(self, p):
        """ metadata_initializers : metadata_initializers error SEMI
        """
        self.print_error(p.lineno(1),
                         "Invalid satement in metadata initializer")

    def p_initializer(self, p):
        """ initializer : ID COLON const_value
        """
        p[0] = (p[1], p[3])

    # FIELD LIST DECLARATION

    def p_p4_declaration_3(self, p):
        """ p4_declaration : field_list_declaration
        """
        p[0] = p[1]

    def p_field_list_declaration(self, p):
        """ field_list_declaration : FIELD_LIST ID \
                                     LBRACE field_list_entries RBRACE
        """
        p[0] = P4FieldList(self.get_filename(), p.lineno(1), p[2], p[4])

    def p_field_list_declaration_error_1(self, p):
        """ field_list_declaration : FIELD_LIST error
        """
        self.print_error(p.lineno(1),
                         "Invalid field list declaration")

    def p_field_list_declaration_error_2(self, p):
        """ field_list_declaration : FIELD_LIST ID \
                                     LBRACE error RBRACE
        """
        self.print_error(p.lineno(1),
                         "Invalid list of entries in field list declaration")

    def p_field_list_entries_1(self, p):
        """ field_list_entries : field_list_entry SEMI
        """
        p[0] = [p[1]]

    def p_field_list_entries_2(self, p):
        """ field_list_entries : field_list_entries field_list_entry SEMI
        """
        p[0] = p[1] + [p[2]]

    def p_field_list_entries_error_1(self, p):
        """ field_list_entries : error SEMI
        """
        self.print_error(p.lineno(2),
                         "Invalid entry in field list")
        p[0] = []

    def p_field_list_entries_error_2(self, p):
        """ field_list_entries : field_list_entries error SEMI
        """
        self.print_error(p.lineno(3),
                         "Invalid entry in field list")
        p[0] = []

    def p_field_list_entry_1(self, p):
        """ field_list_entry : const_value
        """
        p[0] = p[1]

    # temp thing: support for explicit width only for field_list entries
    def p_field_list_entry_11(self, p):
        """ field_list_entry : const_value_with_width
        """
        p[0] = p[1]

    def p_field_list_entry_2(self, p):
        """ field_list_entry : PAYLOAD
        """
        p[0] = P4String(self.get_filename(), p.lineno(1), p[1])   # "payload"

    def p_field_list_entry_3(self, p):
        """ field_list_entry : field_ref
        """
        p[0] = p[1]

    def p_field_list_entry_4(self, p):
        """ field_list_entry : header_ref
        """
        p[0] = p[1]

    # this rule is now useless, it is taken care of by the above one, although
    # it is a bit messy
    # def p_field_list_entry_5(self, p):
    #     """ field_list_entry : ID SEMI
    #     """
    #     pass

    def p_header_ref_1(self, p):
        """ header_ref : ID
        """
        # not necessarily a header ref, namespace conflict, damn
        p[0] = P4RefExpression(self.get_filename(), p.lineno(1), p[1])

    def p_header_ref_2(self, p):
        """ header_ref : ID LBRACKET index RBRACKET
        """
        p[0] = P4HeaderRefExpression(self.get_filename(), p.lineno(1),
                                     p[1], p[3])

    def p_header_error_1(self, p):
        """ header_ref : ID LBRACKET error RBRACKET
        """
        self.print_error(p.lineno(1),
                         "Invalid index in array header reference")
        
    def p_header_index_1(self, p):
        """ index : const_value
        """
        p[0] = p[1]

    def p_header_index_2(self, p):
        """ index : LAST
        """
        p[0] = p[1]   # "last"

    def p_field_ref(self, p):
        """ field_ref : header_ref PERIOD ID
        """
        p[0] = P4FieldRefExpression(self.get_filename(), p.lineno(2),
                                    p[1], p[3])
    
    
# FIELD LIST CALCULATION

    def p_p4_declaration_4(self, p):
        """ p4_declaration : field_list_calculation_declaration
        """
        p[0] = p[1]

    def p_field_list_calculation_declaration(self, p):
        """ field_list_calculation_declaration : \
                FIELD_LIST_CALCULATION ID LBRACE \
                    INPUT LBRACE input_list RBRACE \
                    ALGORITHM COLON ID SEMI \
                    OUTPUT_WIDTH COLON const_value SEMI \
                RBRACE
        """
        p[0] = P4FieldListCalculation(self.get_filename(), p.lineno(1),
                                      p[2], p[6], p[10], p[14])

    def p_field_list_calculation_declaration_error_1(self, p):
        """ field_list_declaration : FIELD_LIST_CALCULATION error
        """
        self.print_error(p.lineno(1),
                         "Invalid field list calculation declaration")

    def p_field_list_calculation_declaration_error_2(self, p):
        """ field_list_calculation_declaration : \
                FIELD_LIST_CALCULATION ID LBRACE \
                    error \
                RBRACE
        """
        self.print_error(p.lineno(1),
                         "Error in body of "
                         "field list calculation declaration \'%s\'" % p[2])

    def p_input_list_1(self, p):
        """ input_list : ID SEMI
        """
        p[0] = [P4RefExpression(self.get_filename(), p.lineno(1), p[1])]

    def p_input_list_2(self, p):
        """ input_list : input_list ID SEMI
        """
        p[0] = p[1] + [P4RefExpression(self.get_filename(), p.lineno(1), p[2])]
        
# CALCULATED FIELD

    def p_p4_declaration_5(self, p):
        """ p4_declaration : calculated_field_declaration
        """
        p[0] = p[1]

    def p_calculated_field_declaration(self, p):
        """ calculated_field_declaration : CALCULATED_FIELD field_ref LBRACE \
                                             update_verify_spec_list \
                                           RBRACE
        """
        p[0] = P4CalculatedField(self.get_filename(), p.lineno(1),
                                 p[2], p[4])

    def p_calculated_field_declaration_error_1(self, p):
        """ calculated_field_declaration : CALCULATED_FIELD error
        """
        self.print_error(p.lineno(1),
                         "Invalid field reference in calculated field declaration")

    def p_calculated_field_declaration_error_2(self, p):
        """ calculated_field_declaration : CALCULATED_FIELD LBRACE error RBRACE
        """
        self.print_error(p.lineno(1),
                         "Invalid update / verify list in calculated field declaration")

    def p_calculated_field_declaration_error_3(self, p):
        """ calculated_field_declaration : CALCULATED_FIELD field_ref error
        """
        self.print_error(p.lineno(1),
                         "Invalid calculated field declaration")

    def p_calculated_field_declaration_error_4(self, p):
        """ calculated_field_declaration : CALCULATED_FIELD error LBRACE \
                                             update_verify_spec_list \
                                           RBRACE
        """
        self.print_error(p.lineno(1),
                         "Invalid field reference in calculated field declaration")

    def p_update_verify_spec_list_1(self, p):
        """ update_verify_spec_list : update_verify_spec SEMI
        """
        p[0] = [p[1]]

    def p_update_verify_spec_list_2(self, p):
        """ update_verify_spec_list : update_verify_spec_list update_verify_spec SEMI
        """
        p[0] = p[1] + [p[2]]

    def p_update_verify_spec_list_error_1(self, p):
        """ update_verify_spec_list : update_verify_spec_list error SEMI
        """
        self.print_error(p.lineno(1),
                         "Invalid update / verify spec in calculated field declaration")
        p[0] = []

    def p_update_verify_spec_list_error_2(self, p):
        """ update_verify_spec_list : error SEMI
        """
        self.print_error(p.lineno(1),
                         "Invalid update / verify spec in calculated field declaration")
        p[0] = []

    def p_update_verify_spec_1(self, p):
        """ update_verify_spec : update_or_verify ID
        """
        p[0] = P4UpdateVerify(self.get_filename(), p.lineno(1),
                              p[1],
                              P4RefExpression(
                                  self.get_filename(),
                                  p.lineno(2),
                                  p[2]
                              ))

    def p_update_verify_spec_2(self, p):
        """ update_verify_spec : update_or_verify ID if_cond
        """
        p[0] = P4UpdateVerify(self.get_filename(), p.lineno(1),
                              p[1],
                              P4RefExpression(
                                  self.get_filename(),
                                  p.lineno(2),
                                  p[2]
                              ),
                              p[3])

    def p_update_verify_spec_error_1(self, p):
        """ update_verify_spec : update_or_verify error
        """
        self.print_error(p.lineno(1),
                         "Invalid update / verify spec in calculated field declaration")        

    def p_update_or_verify(self, p):
        """ update_or_verify : UPDATE
                             | VERIFY
        """
        p[0] = p[1]

    def p_if_cond(self, p):
        """ if_cond : IF LPAREN calc_bool_cond RPAREN
        """
        p[0] = p[3]

    def p_if_cond_error_1(self, p):
        """ if_cond : IF LPAREN error RPAREN
        """
        self.print_error(p.lineno(1),
                         "Invalid if condition in calculated field declaration")        

    def p_if_cond_error_2(self, p):
        """ if_cond : IF error
        """
        self.print_error(p.lineno(1),
                         "Invalid if condition in calculated field declaration")        

    def p_calc_bool_cond_1(self, p):
        """ calc_bool_cond : VALID LPAREN header_ref RPAREN
        """
        p[0] = P4ValidExpression(self.get_filename(), p.lineno(1), p[3])

    def p_calc_bool_cond_2(self, p):
        """ calc_bool_cond : field_ref EQ const_value
        """
        p[0] = P4BinaryExpression(self.get_filename(), p.lineno(1),
                                  p[2], p[1], p[3])

# VALUE SET

    def p_p4_declaration_6(self, p):
        """ p4_declaration : value_set_declaration
        """
        p[0] = p[1]

    def p_p4_value_set_declaration(self, p):
        """ value_set_declaration : PARSER_VALUE_SET ID SEMI
        """
        p[0] = P4ValueSet(self.get_filename(), p.lineno(1), p[2])

    def p_p4_value_set_declaration_error_1(self, p):
        """ value_set_declaration : PARSER_VALUE_SET error SEMI
        """
        self.print_error(p.lineno(1),
                         "Invalid value set declaration")

    def p_p4_value_set_declaration_error_2(self, p):
        """ value_set_declaration : PARSER_VALUE_SET error
        """
        self.print_error(p.lineno(1),
                         "Missing semi-colon in value set declaration")


# PARSER FUNCTION

    def p_p4_declaration_7(self, p):
        """ p4_declaration : parser_function_declaration
        """
        p[0] = p[1]

    def p_parser_function_declaration(self, p):
        """ parser_function_declaration : PARSER ID \
                                          LBRACE parser_function_body RBRACE
        """
        if p[4] is not None:
            extract_and_set_statements, return_statement = p[4]
            p[0] = P4ParserFunction(self.get_filename(), p.lineno(1), p[2],
                                    extract_and_set_statements, return_statement)

    # not very pretty, but that's the best I could think of
    def p_parser_function_declaration_error_0(self, p):
        """ parser_function_declaration : PARSER ID \
                                          LBRACE extract_or_set_statement_list RBRACE
        """
        self.print_error(p.lineno(1),
                         "Missing return statement for parser function %s" % p[2])


    def p_parser_function_declaration_error_1(self, p):
        """ parser_function_declaration : PARSER ID LBRACE error RBRACE
        """
        self.print_error(p.lineno(1),
                         "Invalid body for parser function %s" % p[2])

    def p_parser_function_declaration_error_2(self, p):
        """ parser_function_declaration : PARSER error RBRACE
        """
        self.print_error(p.lineno(1),
                         "Invalid parser function declaration")

    # this one is impossible to recover from (missing brace)
    def p_parser_function_declaration_error_3(self, p):
        """ parser_function_declaration : PARSER error
        """
        self.print_error(p.lineno(1),
                         "Invalid parser function declaration")


    def p_parser_function_body_1(self, p):
        """ parser_function_body : extract_or_set_statement_list return_statement
        """
        p[0] = (p[1], p[2])

    def p_parser_function_body_2(self, p):
        """ parser_function_body : return_statement
        """
        p[0] = ([], p[1])

    def p_extract_or_set_statement_list_1(self, p):
        """ extract_or_set_statement_list : extract_or_set_statement SEMI
        """
        p[0] = [p[1]]

    def p_extract_or_set_statement_list_2(self, p):
        """ extract_or_set_statement_list : extract_or_set_statement_list \
                                              extract_or_set_statement SEMI
        """
        p[0] = p[1] + [p[2]]

    def p_extract_or_set_statement_list_error_1(self, p):
        """ extract_or_set_statement_list : error SEMI
        """
        self.print_error(p.lineno(1),
                         "Invalid statement in parser function body")

    def p_extract_or_set_statement_list_error_2(self, p):
        """ extract_or_set_statement_list : extract_or_set_statement_list error SEMI
        """
        self.print_error(p.lineno(2),
                         "Invalid statement in parser function body")

    def p_extract_or_set_statement(self, p):
        """ extract_or_set_statement : extract_statement
                                     | set_statement
        """
        p[0] = p[1]

    def p_extract_statement(self, p):
        """ extract_statement : EXTRACT LPAREN header_extract_ref RPAREN
        """
        p[0] = P4ParserExtract(self.get_filename(), p.lineno(1), p[3])

    def p_extract_statement_error_1(self, p):
        """ extract_statement : EXTRACT error
        """
        self.print_error(p.lineno(1),
                         "Invalid extract statement")

    def p_extract_statement_error_2(self, p):
        """ extract_statement : EXTRACT LPAREN error RPAREN
        """
        self.print_error(p.lineno(1),
                         "Invalid header reference in extract statement")

    def p_set_statement(self, p):
        """ set_statement : SET_METADATA \
                                LPAREN field_ref COMMA metadata_expr RPAREN
        """
        p[0] = P4ParserSetMetadata(self.get_filename(), p.lineno(1),
                                   p[3], p[5])

    def p_set_statement_error_1(self, p):
        """ set_statement : SET_METADATA error
        """
        self.print_error(p.lineno(1),
                         "Invalid set_metadata statement")

    def p_set_statement_error_2(self, p):
        """ set_statement : SET_METADATA \
                                LPAREN field_ref COMMA error RPAREN
        """
        self.print_error(p.lineno(1),
                         "Invalid expression in set_metadata statement")

    def p_header_extract_ref_1(self, p):
        """ header_extract_ref : ID
        """
        p[0] = P4HeaderRefExpression(self.get_filename(), p.lineno(1), p[1])

    def p_header_extract_ref_2(self, p):
        """ header_extract_ref : ID LBRACKET const_value RBRACKET
        """
        p[0] = P4HeaderRefExpression(self.get_filename(), p.lineno(1),
                                     p[1], p[3])

    def p_header_extract_ref_3(self, p):
        """ header_extract_ref : ID LBRACKET NEXT RBRACKET
        """
        p[0] = P4HeaderRefExpression(self.get_filename(), p.lineno(1),
                                     p[1], p[3])   # "next"


    def p_metadata_expr_1(self, p):
        """ metadata_expr : arith_exp
        """
        p[0] = p[1]

    def p_metadata_expr_2(self, p):
        """ metadata_expr : LATEST PERIOD ID
        """
        p[0] = P4FieldRefExpression(self.get_filename(), p.lineno(1),
                                    p[1], p[3])   # "latest" is header ref

    def p_metadata_expr_3(self, p):
        """ metadata_expr : CURRENT LPAREN const_value COMMA const_value RPAREN
        """
        p[0] = P4CurrentExpression(self.get_filename(), p.lineno(1), p[3], p[5])

    def p_return_statement(self, p):
        """ return_statement : RETURN return_select_statement
                             | RETURN return_immediate_statement
        """
        p[0] = p[2]

    def p_return_statement_error_1(self, p):
        """ return_statement : RETURN error
        """
        self.print_error(p.lineno(1),
                         "Invalid return statement")

    def p_return_select_statement(self, p):
        """ return_select_statement : SELECT LPAREN select_exp RPAREN \
                                      LBRACE case_list RBRACE
        """
        p[0] = P4ParserSelectReturn(self.get_filename(), p.lineno(1),
                                    p[3], p[6])

    def p_return_select_statement_error_1(self, p):
        """ return_select_statement : SELECT LPAREN error RPAREN \
                                      LBRACE case_list RBRACE
        """
        self.print_error(p.lineno(1),
                         "Invalid select expression in select statement")

    def p_return_select_statement_error_2(self, p):
        """ return_select_statement : SELECT LPAREN select_exp RPAREN \
                                      LBRACE error RBRACE
        """
        self.print_error(p.lineno(1),
                         "Invalid case list in select statement")

    def p_return_select_statement_error_3(self, p):
        """ return_select_statement : SELECT error
        """
        self.print_error(p.lineno(1),
                         "Invalid select statement in parser function")

    def p_select_exp_1(self, p):
        """ select_exp : select_field_ref
        """
        p[0] = [p[1]]

    def p_select_exp_2(self, p):
        """ select_exp : select_exp COMMA select_field_ref
        """
        p[0] = p[1] + [p[3]]

    def p_select_field_ref_1(self, p):
        """ select_field_ref : field_ref
        """
        p[0] = p[1]

    def p_select_field_ref_2(self, p):
        """ select_field_ref : LATEST PERIOD ID
        """
        p[0] = P4FieldRefExpression(self.get_filename(), p.lineno(1),
                                    p[1], p[3])   # "latest" is header ref

    def p_select_field_ref_3(self, p):
        """ select_field_ref : CURRENT LPAREN const_value COMMA const_value RPAREN
        """
        p[0] = P4CurrentExpression(self.get_filename(), p.lineno(1), p[3], p[5])

    def p_case_list_1(self, p):
        """ case_list : case_entry
        """
        p[0] = [p[1]]

    def p_case_list_2(self, p):
        """ case_list : case_list case_entry
        """
        p[0] = p[1] + [p[2]]

    def p_case_entry_1(self, p):
        """ case_entry : value_list COLON return_value_type SEMI
        """
        p[0] = P4ParserSelectCase(self.get_filename(), p.lineno(1),
                                  p[1], p[3])

    def p_case_entry_2(self, p):
        """ case_entry : DEFAULT COLON return_value_type SEMI
        """
        p[0] = P4ParserSelectDefaultCase(self.get_filename(), p.lineno(1), p[3])

    def p_case_entry_error_1(self, p):
        """ case_entry : error SEMI
        """
        self.print_error(p.lineno(1),
                         "Invalid case entry")

    def p_value_list_1(self, p):
        """ value_list : value_masked_or_set
        """
        p[0] = [p[1]]

    def p_value_list_2(self, p):
        """ value_list : value_list COMMA value_masked_or_set
        """
        p[0] = p[1] + [p[3]]

    def p_value_masked_or_set_1(self, p):
        """ value_masked_or_set : const_value
        """
        p[0] = (p[1], )

    def p_value_masked_or_set_2(self, p):
        """ value_masked_or_set : const_value MASK const_value
        """
        p[0] = (p[1], p[3])
        
    def p_value_masked_or_set_3(self, p):
        """ value_masked_or_set : ID
        """
        p[0] = (P4RefExpression(self.get_filename(), p.lineno(1), p[1]), )

    def p_return_value_type_1(self, p):
        """ return_value_type : ID
        """
        p[0] = P4RefExpression(self.get_filename(), p.lineno(1), p[1])

    def p_return_value_type_2(self, p):
        """ return_value_type : PARSE_ERROR ID
        """
        # TODO
        p[0] = P4ParserParseError(
            self.get_filename(), p.lineno(1),
            P4RefExpression(self.get_filename(), p.lineno(2), p[2])
        )

    def p_return_immediate_statement(self, p):
        """ return_immediate_statement : return_value_type SEMI
        """
        p[0] = P4ParserImmediateReturn(self.get_filename(), p.lineno(1), p[1])

    def p_return_immediate_statement_error_1(self, p):
        """ return_immediate_statement : error SEMI
        """
        self.print_error(p.lineno(1),
                         "Invalid return statement in parser function")

    
# COUNTER

    def p_p4_declaration_8(self, p):
        """ p4_declaration : counter_declaration
        """
        p[0] = p[1]

    def p_counter_declaration(self, p):
        """ counter_declaration : COUNTER ID LBRACE \
                                      TYPE COLON counter_type SEMI \
                                      direct_or_static \
                                      instance_count \
                                      counter_min_width \
                                      counter_attributes \
                                  RBRACE
        """
        p[0] = P4Counter(self.get_filename(), p.lineno(1),
                         p[2], p[6], p[8], p[9], p[10], p[11])

    def p_counter_declaration_error_1(self, p):
        """ counter_declaration : COUNTER ID LBRACE error RBRACE
        """
        self.print_error(p.lineno(1),
                         "Invalid body for counter declaration %s" % p[2])

    def p_counter_declaration_error_2(self, p):
        """ counter_declaration : COUNTER error RBRACE
        """
        self.print_error(p.lineno(1),
                         "Invalid counter declaration")

    # this one is impossible to recover from (missing brace) ?
    def p_counter_declaration_error_3(self, p):
        """ counter_declaration : COUNTER error
        """
        self.print_error(p.lineno(1),
                         "Invalid counter declaration")

    def p_counter_type(self, p):
        """ counter_type : BYTES
                         | PACKETS
                         | PACKETS_AND_BYTES
        """
        p[0] = p[1]

    def p_direct_or_static_opt_1(self, p):
        """ direct_or_static : empty
        """
        pass # None

    def p_direct_or_static_opt_2(self, p):
        """ direct_or_static : DIRECT COLON ID SEMI
        """
        p[0] = ("direct",
                P4RefExpression(self.get_filename(), p.lineno(3), p[3]))

    def p_direct_or_static_opt_2_error_1(self, p):
        """ direct_or_static : DIRECT error SEMI
        """
        self.print_error(p.lineno(1),
                         "Invalid direct attribute for counter")

    def p_direct_or_static_opt_3(self, p):
        """ direct_or_static : STATIC COLON ID SEMI
        """
        p[0] = ("static",
                P4RefExpression(self.get_filename(), p.lineno(3), p[3]))

    def p_direct_or_static_opt_3_error_1(self, p):
        """ direct_or_static : STATIC error SEMI
        """
        self.print_error(p.lineno(1),
                         "Invalid static attribute for counter")
        
    def p_instance_count_1(self, p):
        """ instance_count : empty
        """
        pass # None

    def p_instance_count_2(self, p):
        """ instance_count : INSTANCE_COUNT COLON const_value SEMI
        """
        p[0] = p[3]

    def p_instance_count_error_1(self, p):
        """ instance_count : INSTANCE_COUNT error SEMI
        """
        self.print_error(p.lineno(1),
                         "Invalid instance_count attribute for counter")

    def p_counter_min_width_1(self, p):
        """ counter_min_width : empty
        """
        pass # None

    def p_counter_min_width_2(self, p):
        """ counter_min_width : MIN_WIDTH COLON const_value SEMI
        """
        p[0] = p[3]

    def p_counter_min_width_error_1(self, p):
        """ counter_min_width : MIN_WIDTH error SEMI
        """
        self.print_error(p.lineno(1),
                         "Invalid min_width attribute for counter")

    def p_counter_attributes_1(self, p):
        """ counter_attributes : empty
        """
        p[0] = []

    def p_counter_attributes_2(self, p):
        """ counter_attributes : SATURATING SEMI
        """
        p[0] = ["saturating"]

    
# METER

    def p_p4_declaration_9(self, p):
        """ p4_declaration : meter_declaration
        """
        p[0] = p[1]

    def p_meter_declaration(self, p):
        """ meter_declaration : METER ID LBRACE \
                                    TYPE COLON meter_type SEMI \
                                    direct_or_static \
                                    direct_result \
                                    instance_count \
                                RBRACE
        """
        p[0] = P4Meter(self.get_filename(), p.lineno(1),
                       p[2], p[6], p[8], p[9], p[10])

    def p_meter_declaration_error_1(self, p):
        """ meter_declaration : METER ID LBRACE error RBRACE
        """
        self.print_error(p.lineno(1),
                         "Invalid body for meter declaration %s" % p[2])

    def p_meter_declaration_error_2(self, p):
        """ meter_declaration : METER error RBRACE
        """
        self.print_error(p.lineno(1),
                         "Invalid meter declaration")

    # this one is impossible to recover from (missing brace) ?
    def p_meter_declaration_error_3(self, p):
        """ meter_declaration : METER error
        """
        self.print_error(p.lineno(1),
                         "Invalid meter declaration")

    def p_meter_type(self, p):
        """ meter_type : BYTES
                       | PACKETS
        """
        p[0] = p[1]

    def p_direct_result_1(self, p):
        """ direct_result : empty
        """
        pass # None

    def p_direct_result_2(self, p):
        """ direct_result : RESULT COLON field_ref SEMI
        """
        p[0] = p[3]

    def p_direct_result_error_1(self, p):
        """ direct_result : RESULT error SEMI
        """
        self.print_error(p.lineno(1),
                         "Invalid result attribute for counter")

# REGISTER

    def p_p4_declaration_10(self, p):
        """ p4_declaration : register_declaration
        """
        p[0] = p[1]

    def p_register_declaration(self, p):
        """ register_declaration : REGISTER ID LBRACE \
                                     width_or_layout \
                                     direct_or_static \
                                     instance_count \
                                     register_attributes \
                                   RBRACE
        """
        width, layout = p[4]
        p[0] = P4Register(self.get_filename(), p.lineno(1),
                          p[2], width, layout, p[5], p[6], p[7])

    def p_register_declaration_error_1(self, p):
        """ register_declaration : REGISTER ID LBRACE error RBRACE
        """
        self.print_error(p.lineno(1),
                         "Invalid body for register declaration %s" % p[2])

    def p_register_declaration_error_2(self, p):
        """ register_declaration : REGISTER error RBRACE
        """
        self.print_error(p.lineno(1),
                         "Invalid register declaration")

    def p_width_or_layout_1(self, p):
        """ width_or_layout : register_width
        """
        p[0] = p[1], None

    def p_width_or_layout_2(self, p):
        """ width_or_layout : register_layout
        """
        p[0] = None, p[1]

    def p_register_width(self, p):
        """ register_width : WIDTH COLON const_value SEMI
        """
        p[0] = p[3]

    def p_register_width_error_1(self, p):
        """ register_width : WIDTH error SEMI
        """
        self.print_error(p.lineno(1),
                         "Invalid width attribute for register")

    def p_register_layout(self, p):
        """ register_layout : LAYOUT COLON ID SEMI
        """
        p[0] = P4RefExpression(self.get_filename(), p.lineno(3), p[3])

    def p_register_layout_error_1(self, p):
        """ register_layout : LAYOUT error SEMI
        """
        self.print_error(p.lineno(1),
                         "Invalid layout attribute for register")

    def p_register_attributes_1(self, p):
        """ register_attributes : empty
        """
        p[0] = []

    def p_register_attributes_2(self, p):
        """ register_attributes : ATTRIBUTES COLON register_attribute_list SEMI
        """
        p[0] = p[3]

    def p_register_attributes_2_error_1(self, p):
        """ register_attributes : ATTRIBUTES error SEMI
        """
        self.print_error(p.lineno(1),
                         "Invalid attributes list for register")

    def p_register_attribute_list_1(self, p):
        """ register_attribute_list : register_attribute_list COMMA register_attribute
        """
        p[0] = p[1] + [p[3]]

    def p_register_attribute_list_2(self, p):
        """ register_attribute_list : register_attribute
        """
        p[0] = [p[1]]

    def p_register_attribute(self, p):
        """ register_attribute : SIGNED
                               | SATURATING
        """
        p[0] = p[1]  # "signed", "saturating"


# PRIMITIVE ACTION

    def p_p4_declaration_11(self, p):
        """ p4_declaration : primitive_action_declaration
        """
        # TODO not supported because still changing
        p[0] = p[1]

    def p_primitive_action_declaration_1(self, p):
        """ primitive_action_declaration : PRIMITIVE_ACTION ID \
                                           LPAREN RPAREN SEMI
        """
        p[0] = P4PrimitiveAction(self.get_filename(), p.lineno(1), p[2])

    def p_primitive_action_declaration_2(self, p):
        """ primitive_action_declaration : PRIMITIVE_ACTION ID \
                                           LPAREN param_list RPAREN SEMI
        """
        p[0] = P4PrimitiveAction(self.get_filename(), p.lineno(1), p[2], p[4])

    def p_primitive_action_declaration_error_1(self, p):
        """ primitive_action_declaration : PRIMITIVE_ACTION ID \
                                           LPAREN error RPAREN SEMI
        """
        self.print_error(p.lineno(1),
                         "Invalid param list for primitive action %s" % p[2])

    def p_primitive_action_declaration_error_2(self, p):
        """ primitive_action_declaration : PRIMITIVE_ACTION error SEMI
        """
        self.print_error(p.lineno(1),
                         "Invalid primitive action declaration")

    def p_primitive_action_declaration_error_3(self, p):
        """ primitive_action_declaration : PRIMITIVE_ACTION error
        """
        self.print_error(p.lineno(1),
                         "Invalid primitive action declaration")

    def p_param_list_1(self, p):
        """ param_list : ID
        """
        p[0] = [p[1]]

    def p_param_list_2(self, p):
        """ param_list : param_list COMMA ID
        """
        p[0] = p[1] + [p[3]]

    
# ACTION FUNCTION

    def p_p4_declaration_12(self, p):
        """ p4_declaration : action_function_declaration
        """
        p[0] = p[1]

    def p_action_function_declaration(self, p):
        """ action_function_declaration : ACTION action_header LBRACE \
                                              action_statement_list \
                                          RBRACE
        """
        if p[2] is not None:
            name, param_list = p[2]
            p[0] = P4ActionFunction(self.get_filename(), p.lineno(1),
                                    name, param_list, p[4])

    def p_action_function_declaration_error_1(self, p):
        """ action_function_declaration : ACTION action_header LBRACE error RBRACE
        """
        self.print_error(p.lineno(1),
                         "Error in body of action function %s" % p[2])

    def p_action_function_declaration_error_2(self, p):
        """ action_function_declaration : ACTION error RBRACE
        """
        self.print_error(p.lineno(1),
                         "Error in action function declaration")

    def p_action_function_declaration_error_3(self, p):
        """ action_function_declaration : ACTION error
        """
        self.print_error(p.lineno(1),
                         "Error in action function declaration")

    def p_action_header_1(self, p):
        """ action_header : ID LPAREN RPAREN
        """
        p[0] = (p[1], [])
        pass

    def p_action_header_2(self, p):
        """ action_header : ID LPAREN param_list RPAREN
        """
        p[0] = (p[1], p[3])

    def p_action_header_error_1(self, p):
        """ action_header : ID LPAREN error RPAREN
        """
        self.print_error(p.lineno(1),
                         "Invalid param list for action function %s" % p[2])

    def p_action_statement_list_1(self, p):
        """ action_statement_list : empty
        """
        p[0] = []

    def p_action_statement_list_2(self, p):
        """ action_statement_list : action_statement_list action_statement
        """
        p[0] = p[1] + [p[2]]

    def p_action_satement_1(self, p):
        """ action_statement : ID LPAREN RPAREN SEMI
        """
        p[0] = P4ActionCall(
            self.get_filename(), p.lineno(1),
            P4RefExpression(self.get_filename(), p.lineno(1), p[1])
        )

    def p_action_satement_2(self, p):
        """ action_statement : ID LPAREN arg_list RPAREN SEMI
        """
        p[0] = P4ActionCall(
            self.get_filename(), p.lineno(1),
            P4RefExpression(self.get_filename(), p.lineno(1), p[1]),
            p[3]
        )

    def p_action_satement_error_1(self, p):
        """ action_statement : ID error SEMI
        """
        self.print_error(p.lineno(1),
                         "Invalid action statement in action body")

    def p_arg_list_1(self, p):
        """ arg_list : arg
        """
        p[0] = [p[1]]

    def p_arg_list_2(self, p):
        """ arg_list : arg_list COMMA arg
        """
        p[0] = p[1] + [p[3]]

    def p_arg(self, p):
        """ arg : general_exp
        """
        p[0] = p[1]

    
# TABLE DECLARATION

    def p_p4_declaration_13(self, p):
        """ p4_declaration : table_declaration
        """
        p[0] = p[1]

    def p_table_declaration_1(self, p):
        """ table_declaration : TABLE ID LBRACE \
                                     table_reads \
                                     action_specification \
                                     default_action \
                                     table_min_size \
                                     table_max_size \
                                     table_size \
                                     table_timeout \
                                RBRACE
        """
        p[0] = P4Table(self.get_filename(), p.lineno(1),
                       p[2], p[5], None, p[6], p[4], p[7], p[8], p[9], p[10])

    def p_table_declaration_2(self, p):
        """ table_declaration : TABLE ID LBRACE \
                                     table_reads \
                                     action_profile \
                                     table_min_size \
                                     table_max_size \
                                     table_size \
                                     table_timeout \
                                RBRACE
        """
        p[0] = P4Table(self.get_filename(), p.lineno(1),
                       p[2], None, p[5], None, p[4], p[6], p[7], p[8], p[9])

    def p_table_declaration_error_1(self, p):
        """ table_declaration : TABLE ID LBRACE error RBRACE
        """
        self.print_error(p.lineno(1),
                         "Invalid body for table declaration %s" % p[2])

    def p_table_declaration_error_2(self, p):
        """ table_declaration : TABLE error RBRACE
        """
        self.print_error(p.lineno(1),
                         "Invalid table declaration")

    # this one is impossible to recover from (missing brace) ?
    def p_table_declaration_error_3(self, p):
        """ table_declaration : TABLE error
        """
        self.print_error(p.lineno(1),
                         "Invalid table declaration")

    def p_table_reads_1(self, p):
        """ table_reads : empty
        """
        p[0] = []

    def p_table_reads_2(self, p):
        """ table_reads : READS LBRACE field_match_list RBRACE
        """
        p[0] = p[3]

    def p_field_match_list_1(self, p):
        """ field_match_list : field_match SEMI
        """
        p[0] = [p[1]]

    def p_field_match_list_2(self, p):
        """ field_match_list : field_match_list field_match SEMI
        """
        p[0] = p[1] + [p[2]]

    def p_field_match_error_1(self, p):
        """ field_match_list : error SEMI
        """
        self.print_error(p.lineno(2),
                         "Invalid field match specification")
        p[0] = []

    def p_field_match_error_2(self, p):
        """ field_match_list : field_match_list error SEMI
        """
        self.print_error(p.lineno(2),
                         "Invalid field match specification")
        p[0] = []

    # made a conscious choice not to hardcode the match types here
    # see semantic checker
    def p_field_match(self, p):
        # ooooh that second rule, so so so ugly :(
        """ field_match : field_or_masked_ref COLON ID
                        | field_or_masked_ref COLON VALID
        """
        p[0] = P4TableFieldMatch(self.get_filename(), p.lineno(1), p[1], p[3])

    def p_field_or_masked_ref_1(self, p):
        """ field_or_masked_ref : header_ref
        """
        p[0] = (p[1],)

    def p_field_or_masked_ref_2(self, p):
        """ field_or_masked_ref : field_ref
        """
        p[0] = (p[1],)

    def p_field_or_masked_ref_3(self, p):
        """ field_or_masked_ref : field_ref MASK const_value
        """
        p[0] = (p[1], p[3])

    def p_action_profile(self, p):
        """ action_profile : ACTION_PROFILE COLON ID SEMI
        """
        p[0] = P4RefExpression(self.get_filename(), p.lineno(3), p[3])

    def p_action_specification(self, p):
        """ action_specification : ACTIONS LBRACE action_list RBRACE
        """
        p[0] = p[3]

    def p_action_specification_error_1(self, p):
        """ action_specification : ACTIONS LBRACE error RBRACE
        """
        self.print_error(p.lineno(1),
                         "Invalid list of actions")

    def p_action_list_1(self, p):
        """ action_list : action_and_next SEMI
        """
        p[0] = [p[1]]

    def p_action_list_2(self, p):
        """ action_list : action_list action_and_next SEMI
        """
        p[0] = p[1] + [p[2]]

    def p_action_list_error_1(self, p):
        """ action_list : error SEMI
        """
        self.print_error(p.lineno(1),
                         "Invalid action-and-next specification")
        p[0] = []

    def p_action_list_error_2(self, p):
        """ action_list : action_list error SEMI
        """
        self.print_error(p.lineno(2),
                         "Invalid action-and-next specification")
        p[0] = []

    def p_action_list_error_3(self, p):
        """ action_list : action_list error
        """
        self.print_error(p.lineno(2),
                         "Invalid action-and-next specification")
        p[0] = []

    def p_action_and_next(self, p):
        """ action_and_next : ID
        """
        p[0] = P4RefExpression(self.get_filename(), p.lineno(1), p[1])

    def p_default_action_1(self, p):
        """ default_action : empty
        """
        pass   # None

    def p_default_action_2(self, p):
        """ default_action : DEFAULT_ACTION COLON ID LPAREN action_data RPAREN SEMI
        """
        p[0] = P4TableDefaultAction(
            self.get_filename(), p.lineno(1),
            P4RefExpression(self.get_filename(), p.lineno(3), p[3]),
            p[5]
        )

    def p_default_action_3(self, p):
        """ default_action : DEFAULT_ACTION COLON ID SEMI
        """
        p[0] = P4TableDefaultAction(
            self.get_filename(), p.lineno(1),
            P4RefExpression(self.get_filename(), p.lineno(3), p[3]),
            None
        )

    def p_default_action_error_1(self, p):
        """ default_action : DEFAULT_ACTION error SEMI
        """
        self.print_error(p.lineno(1),
                         "Invalid default_action attribute for table")

    def p_default_action_error_2(self, p):
        """ default_action : DEFAULT_ACTION error
        """
        self.print_error(p.lineno(1),
                         "Invalid default_action attribute for table, missing semi-colon")

    def p_action_data_1(self, p):
        """ action_data : empty
        """
        p[0] = []

    def p_action_data_2(self, p):
        """ action_data : action_data_list
        """
        p[0] = p[1]

    def p_action_data_list_1(self, p):
        """ action_data_list : const_value
        """
        p[0] = [p[1]]

    def p_action_data_list_2(self, p):
        """ action_data_list : const_value COMMA action_data_list
        """
        p[0] = [p[1]] + p[3]
    
    def p_table_min_size_1(self, p):
        """ table_min_size : empty
        """
        pass   # None

    def p_table_min_size_2(self, p):
        """ table_min_size : MIN_SIZE COLON const_value SEMI
        """
        p[0] = p[3]

    def p_table_min_size_2_error_1(self, p):
        """ table_min_size : MIN_SIZE error SEMI
        """
        self.print_error(p.lineno(1),
                         "Invalid min_size attribute for table")

    def p_table_min_size_2_error_2(self, p):
        """ table_min_size : MIN_SIZE error
        """
        self.print_error(p.lineno(1),
                         "Invalid min_size attribute for table, missing semi-colon")

    def p_table_max_size_1(self, p):
        """ table_max_size : empty
        """
        pass   # None

    def p_table_max_size_2(self, p):
        """ table_max_size : MAX_SIZE COLON const_value SEMI
        """
        p[0] = p[3]

    def p_table_max_size_2_error_1(self, p):
        """ table_max_size : MAX_SIZE error SEMI
        """
        self.print_error(p.lineno(1),
                         "Invalid max_size attribute for table")

    def p_table_max_size_2_error_2(self, p):
        """ table_max_size : MAX_SIZE error
        """
        self.print_error(p.lineno(1),
                         "Invalid max_size attribute for table, missing semi-colon")

    def p_table_size_1(self, p):
        """ table_size : empty
        """
        pass   # None

    def p_table_size_2(self, p):
        """ table_size : SIZE COLON const_value SEMI
        """
        p[0] = p[3]

    def p_table_size_2_error_1(self, p):
        """ table_size : SIZE error SEMI
        """
        self.print_error(p.lineno(1),
                         "Invalid size attribute for table")

    def p_table_size_2_error_2(self, p):
        """ table_size : SIZE error
        """
        self.print_error(p.lineno(1),
                         "Invalid size attribute for table, missing semi-colon")

    def p_table_timeout_1(self, p):
        """ table_timeout : empty
        """
        pass   # None

    def p_table_timeout_2(self, p):
        """ table_timeout : SUPPORT_TIMEOUT COLON bool_value SEMI
        """
        p[0] = p[3]

#  CONTROL FUNCTION
    
    def p_p4_declaration_14(self, p):
        """ p4_declaration : control_function_declaration
        """
        p[0] = p[1]

    def p_control_function_declaration(self, p):
        """ control_function_declaration : CONTROL ID control_statement
        """
        p[0] = P4ControlFunction(self.get_filename(), p.lineno(1), p[2], p[3])

    def p_control_function_declaration_error_2(self, p):
        """ control_function_declaration : CONTROL error
        """
        self.print_error(p.lineno(1),
                         "Error in control function")

    def p_control_statement_1(self, p):
        """ control_statement : expression_statement
        """
        p[0] = [p[1]]

    def p_control_statement_2(self, p):
        """ control_statement : compound_statement
        """
        p[0] = p[1]

    def p_compound_statement_1(self, p):
        """ compound_statement : LBRACE control_statement_list RBRACE
        """
        p[0] = p[2]

    def p_compound_statement_1_error_1(self, p):
        """ compound_statement : LBRACE error RBRACE
        """
        self.print_error(p.lineno(1),
                         "Error in compound statement")
        p[0] = []

    def p_compound_statement_2(self, p):
        """ compound_statement : LBRACE RBRACE
        """
        p[0] = []

    def p_control_statement_list_1(self, p):
        """ control_statement_list : control_statement
        """
        p[0] = p[1]

    def p_control_statement_list_2(self, p):
        """ control_statement_list : control_statement control_statement_list
        """
        p[0] = p[1] + p[2]

    def p_expresssion_statement_1(self, p):
        """ expression_statement : APPLY LPAREN ID RPAREN SEMI
        """
        p[0] = P4ControlFunctionApply(
            self.get_filename(), p.lineno(1),
            P4RefExpression(self.get_filename(), p.lineno(3), p[3])
        )

    def p_expression_statement_1_error_1(self, p):
        """ expression_statement : APPLY error SEMI
        """
        self.print_error(p.lineno(1),
                         "Invalid apply_table statement")

    def p_expression_statement_2(self, p):
        """ expression_statement : IF LPAREN bool_exp RPAREN \
                                       control_statement \
                                   ELSE \
                                       control_statement
        """
        p[0] = P4ControlFunctionIfElse(self.get_filename(), p.lineno(1),
                                       p[3], p[5], p[7])

    def p_expression_statement_2_error_1(self, p):
        """ expression_statement : IF LPAREN error RPAREN \
                                       control_statement \
                                   ELSE \
                                       control_statement
        """
        self.print_error(p.lineno(1),
                         "Invalid boolean expression")

    def p_expression_statement_3(self, p):
        """ expression_statement : IF LPAREN bool_exp RPAREN control_statement
        """
        p[0] = P4ControlFunctionIfElse(self.get_filename(), p.lineno(1),
                                       p[3], p[5])

    def p_expression_statement_3_error_1(self, p):
        """ expression_statement : IF LPAREN error RPAREN control_statement
        """
        self.print_error(p.lineno(1),
                         "Invalid boolean expression")

    def p_expression_statement_4(self, p):
        """ expression_statement : ID LPAREN RPAREN SEMI
        """
        p[0] = P4ControlFunctionCall(
            self.get_filename(), p.lineno(1),
            P4RefExpression(self.get_filename(), p.lineno(1), p[1])
        )

    def p_expression_statement_5(self, p):
        """ expression_statement : APPLY LPAREN ID RPAREN \
                                     LBRACE apply_case_list RBRACE
        """
        p[0] = P4ControlFunctionApplyAndSelect(
            self.get_filename(), p.lineno(1),
            P4RefExpression(self.get_filename(), p.lineno(3), p[3]),
            p[6]
        )

    def p_expression_statement_5_error_1(self, p):
        """ expression_statement : APPLY LPAREN ID RPAREN \
                                     LBRACE error RBRACE
        """
        self.print_error(p.lineno(6),
                         "Invalid case list in apply_table select block")

    def p_expression_statement_5_error_2(self, p):
        """ expression_statement : APPLY error
        """
        self.print_error(p.lineno(1),
                         "Invalid apply_table statement")

    def p_apply_case_list_1(self, p):
        """ apply_case_list : apply_case
        """
        p[0] = [p[1]]

    def p_apply_case_list_2(self, p):
        """ apply_case_list : apply_case_list apply_case
        """
        p[0] = p[1] + [p[2]]

    def p_apply_case_list_error_1(self, p):
        """ apply_case_list : apply_case_list error
        """
        self.print_error(p.lineno(2),
                         "Invalid case in apply_table select block")
        p[0] = p[1]

    # Note that this is different from the P4 spec, which separates action cases
    # and hit miss cases in the BNF grammar. We will enforce the separation /
    # incompatibility in the semantic checker, to get a more informative error
    # message 

    def p_apply_case_1(self, p):
        """ apply_case : action_case_list control_statement
        """
        p[0] = P4ControlFunctionApplyActionCase(
            self.get_filename(), p.lineno(2),
            p[1],
            p[2]
        )

    def p_action_case_list_1(self, p):
        """ action_case_list : action_case
        """
        p[0] = [p[1]]

    def p_action_case_list_2(self, p):
        """ action_case_list : action_case_list COMMA action_case
        """
        p[0] = p[1] + [p[3]]

    def p_action_case(self, p):
        """ action_case : ID
        """
        p[0] = P4RefExpression(self.get_filename(), p.lineno(1), p[1])

    def p_apply_case_2(self, p):
        """ apply_case : DEFAULT control_statement
        """
        p[0] = P4ControlFunctionApplyActionDefaultCase(
            self.get_filename(), p.lineno(1), p[2]
        )

    def p_apply_case_3(self, p):
        """ apply_case : HIT control_statement
        """
        p[0] = P4ControlFunctionApplyHitMissCase(
            self.get_filename(), p.lineno(1), p[1], p[2]
        )

    def p_apply_case_4(self, p):
        """ apply_case : MISS control_statement
        """
        p[0] = P4ControlFunctionApplyHitMissCase(
            self.get_filename(), p.lineno(1), p[1], p[2]
        )
    
    def p_bool_exp_1(self, p):
        """ bool_exp : VALID LPAREN header_ref RPAREN
        """
        p[0] = P4ValidExpression(self.get_filename(), p.lineno(1), p[3])

    def p_bool_exp_2(self, p):
        """ bool_exp : bool_exp LOR bool_exp
                     | bool_exp LAND bool_exp
        """
        p[0] = P4BoolBinaryExpression(self.get_filename(), p.lineno(1),
                                      p[2], p[1], p[3])

    def p_bool_exp_3(self, p):
        """ bool_exp : LNOT bool_exp
        """
        p[0] = P4BoolUnaryExpression(self.get_filename(), p.lineno(1),
                                     "not", p[2])

    def p_bool_exp_4(self, p):
        """ bool_exp : LPAREN bool_exp RPAREN
        """
        p[0] = p[2]

    def p_bool_exp_5(self, p):
        """ bool_exp : bool_value
        """
        p[0] = p[1]

    def p_bool_exp_6(self, p):
        """ bool_exp : arith_exp LT arith_exp
                     | arith_exp GT arith_exp
                     | arith_exp LE arith_exp
                     | arith_exp GE arith_exp
                     | arith_exp EQ arith_exp
                     | arith_exp NE arith_exp
        """
        p[0] = P4BinaryExpression(self.get_filename(), p.lineno(1),
                                  p[2], p[1], p[3])

    def p_general_exp(self, p):
        """ general_exp : expression
        """
        p[0] = p[1]

    def p_expression_1(self, p):
        """ expression : expression LT expression 
                       | expression GT expression
                       | expression LE expression
                       | expression GE expression
                       | expression EQ expression
                       | expression NE expression
                       | expression PLUS expression
                       | expression MINUS expression
                       | expression TIMES expression
                       | expression LSHIFT expression
                       | expression RSHIFT expression
                       | expression MOD expression
                       | expression DIVIDE expression
                       | expression AND expression
                       | expression OR expression
                       | expression XOR expression
        """
        p[0] = P4BinaryExpression(self.get_filename(), p.lineno(1),
                                  p[2], p[1], p[3])

    def p_expression_2(self, p):
        """ expression : expression LOR expression
                       | expression LAND expression
        """
        p[0] = P4BoolBinaryExpression(self.get_filename(), p.lineno(1),
                                      p[2], p[1], p[3])

    def p_expression_3(self, p):
        """ expression : LNOT expression
        """
        p[0] = P4BoolUnaryExpression(self.get_filename(), p.lineno(1),
                                     p[1], p[2])

    def p_expression_4(self, p):
        """ expression : NOT expression
                       | MINUS expression %prec UMINUS
                       | PLUS expression %prec UMINUS
        """
        p[0] = P4UnaryExpression(self.get_filename(), p.lineno(1),
                                 p[1], p[2])

    def p_expression_5(self, p):
        """ expression : LPAREN expression RPAREN
        """
        p[0] = p[2]

    def p_expression_6(self, p):
        """ expression : bool_value
        """
        p[0] = p[1]

    def p_expression_7(self, p):
        """ expression : VALID LPAREN header_ref RPAREN
        """
        p[0] = P4ValidExpression(self.get_filename(), p.lineno(1), p[3])

    def p_expression_8(self, p):
        """ expression : const_value
        """
        p[0] = p[1]

    def p_expression_9(self, p):
        """ expression : field_ref
        """
        p[0] = p[1]

    # included in 'header_ref' rule

    # def p_expression_10(self, p):
    #     """ expression : ID
    #     """
    #     p[0] = P4RefExpression(self.get_filename(), p.lineno(1), p[1])

    def p_expression_11(self, p):
        """ expression : header_ref
        """
        p[0] = p[1]

    # PARSER EXCEPTIONS

    def p_p4_declaration_15(self, p):
        """ p4_declaration : PARSER_EXCEPTION ID LBRACE \
                               set_statement_list \
                               return_or_drop SEMI \
                             RBRACE 
        """
        p[0] = P4ParserException(self.get_filename(), p.lineno(1),
                                 p[2], p[4], p[5])

    def p_return_or_drop_1(self, p):
        """ return_or_drop : PARSER_DROP
        """
        p[0] = P4ParserExceptionDrop(self.get_filename(), p.lineno(1))

    def p_return_or_drop_2(self, p):
        """ return_or_drop : RETURN ID
        """
        p[0] = P4ParserExceptionReturn(
            self.get_filename(), p.lineno(1),
            P4RefExpression(self.get_filename(), p.lineno(1), p[2])
        )

    def p_set_statement_list_1(self, p):
        """ set_statement_list : empty
        """
        p[0] = []

    def p_set_statement_list_2(self, p):
        """ set_statement_list : set_statement_list set_statement SEMI
        """
        p[0] = p[1] + [p[2]]

    def p_set_statement_list_error_1(self, p):
        """ set_statement_list : set_statement_list error SEMI
        """
        self.print_error(p.lineno(2),
                         "Invalid set_statement in parser exception declaration")
        p[0] = p[1]


# ACTION PROFILE DECLARATION

    def p_p4_declaration_16(self, p):
        """ p4_declaration : action_profile_declaration
        """
        p[0] = p[1]

    def p_action_profile_declaration(self, p):
        """ action_profile_declaration : ACTION_PROFILE ID LBRACE \
                                             action_specification \
                                             table_size \
                                             action_selector \
                                         RBRACE
        """
        p[0] = P4ActionProfile(self.get_filename(), p.lineno(1),
                               p[2], p[4], p[5], p[6])

    def p_action_selector_1(self, p):
        """ action_selector : empty
        """
        p[0] = None

    def p_action_selector_2(self, p):
        """ action_selector : DYNAMIC_ACTION_SELECTION COLON ID SEMI
        """
        p[0] = P4RefExpression(self.get_filename(), p.lineno(3), p[3])


    # ACTION SELECTOR DECLARATION

    def p_p4_declaration_17(self, p):
        """ p4_declaration : action_selector_declaration
        """
        p[0] = p[1]

    def p_action_selector_declaration(self, p):
        """ action_selector_declaration : ACTION_SELECTOR ID LBRACE \
                                              selection_key \
                                              selection_mode \
                                              selection_type \
                                          RBRACE
        """
        p[0] = P4ActionSelector(self.get_filename(), p.lineno(1),
                                p[2], p[4], p[5], p[6])

    def p_selection_algo_1(self, p):
        """ selection_key : SELECTION_KEY COLON ID SEMI
        """
        p[0] = P4RefExpression(self.get_filename(), p.lineno(3), p[3])

    def p_selection_mode_1(self, p):
        """ selection_mode : empty
        """
        p[0] = None

    def p_selection_mode_2(self, p):
        """ selection_mode : SELECTION_MODE COLON ID SEMI
        """
        p[0] = p[3]

    def p_selection_type_1(self, p):
        """ selection_type : empty
        """
        p[0] = None

    def p_selection_type_2(self, p):
        """ selection_type : SELECTION_TYPE COLON ID SEMI
        """
        p[0] = p[3]


    def p_error(self, p):
        if p is None:
            self.print_error(self.lexer.get_lineno(),
                             "Unexpected end-of-file (missing brace?)")
        else:
            self.print_error(
                p.lineno,
                "Syntax error while parsing at token %s (%s)" % (p.value, p.type)
            )
