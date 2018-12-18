# Copyright Brown University & Xi'an Jiaotong University
# 
# Licensed under the Apache License, Version 2.0 (the "License");
#
# Author: Peng Zheng
# Email:  zeepean@gmail.com
#


import os
from frontend.tokenizer import *
from frontend.parser import *
from frontend.preprocessor import Preprocessor, PreprocessorException
from frontend.semantic_check import P4SemanticChecker
from frontend.dumper import P4HlirDumper
from frontend.ast import P4Program
from collections import OrderedDict
import hlir.p4 as p4
import itertools
import logging
import json
import pkg_resources
from pprint import pprint

from hlir.table_dependency import rmt_build_table_graph

logger = logging.getLogger(__name__)

class HLIR():
    def __init__(self, *args):
        self.source_files = [] + list(args)
        self.source_txt = []
        self.preprocessor_args = [] 
        self.analysis_args = {}
        self.primitives = []

        self.p4_objects = []

        self.p4_primitives_ = OrderedDict()
        self.p4_actions = OrderedDict()
        self.p4_control_flows = OrderedDict()
        self.p4_headers = OrderedDict()
        self.p4_header_instances = OrderedDict()
        self.p4_fields = OrderedDict()
        self.p4_field_lists = OrderedDict()
        self.p4_field_list_calculations = OrderedDict()
        self.p4_parser_exceptions = OrderedDict()
        self.p4_parse_value_sets = OrderedDict()
        self.p4_parse_states = OrderedDict()
        self.p4_counters = OrderedDict()
        self.p4_meters = OrderedDict()
        self.p4_registers = OrderedDict()
        self.p4_nodes = OrderedDict()
        self.p4_tables = OrderedDict()
        self.p4_action_profiles = OrderedDict()
        self.p4_action_selectors = OrderedDict()
        self.p4_conditional_nodes = OrderedDict()

        self.calculated_fields = []

        self.p4_ingress_ptr = {}
        self.p4_egress_ptr = None

        self.primitives = json.loads(pkg_resources.resource_string('p4_hlir.frontend', 'primitives.json'))


    def version(self):
        return pkg_resources.require("p4-hlir")[0].version
        
    def add_src_files(self, *args):
        self.source_files += args

    def add_preprocessor_args (self, *args):
        self.preprocessor_args += args

    def set_analysis_args (self, args):
        self.analysis_args = args

    def add_src_txt(self, *args):
        self.source_txt += args

    def add_primitives (self, primitives_dict):
        self.primitives.update(primitives_dict)

    # program_version = 0: metadata
    #                   10000: production program
    #                   20000: testing/shadow program
    def build(self, optimize=True, analyze=True, dump_preprocessed=False, program_version=0, config_dir=None):
        if len(self.source_files) == 0:
            print "no source file to process"
            return False

        # 00. Pre-process all program text
        preprocessed_sources = []
        try:
            preprocessor = Preprocessor() # ZP: to use gcc pre-process souce code
            preprocessor.args += self.preprocessor_args

            # ZP: self.source_file is the fine name of P4 program
            # print 'ZP: main-003', self.source_files 
            # print 'ZP: main-004', self.source_txt
            for p4_source in self.source_files:

                absolute_source = os.path.join(os.getcwd(), p4_source)

                if not self._check_source_path(absolute_source):
                    print "Source file '" + p4_source + "' could not be opened or does not exist."
                    return False
                print 'INFO|p4_hlir|HLIR build:', absolute_source

                preprocessed_sources.append(preprocessor.preprocess_file(
                    absolute_source,
                    dest='%s.i'%p4_source if dump_preprocessed else None
                ))

            for p4_txt in self.source_txt:
                preprocessed_sources.append(preprocessor.preprocess_str(
                    p4_txt,
                    dest=None
                ))
            # ZP: preprocessed_sources is the P4.s source code
            # print 'ZP: main-006', preprocessed_sources

        except PreprocessorException as e:
            print str(e)
            return False

        # 01. Parse preprocessed text to AST
        #     Use 'yacc' and 'P4LSexer' to parse the abstract syntax tree
        #     defined in frontend/parser.py.
        all_p4_objects = []
        for preprocessed_source in preprocessed_sources:
            # ZP: (1) The parser() first build the P4Lexer in tokenizer.py
            #         P4lexer is the Lexical Analyzar of P4 language
            #     (2) Then it inits the yacc tool. Yacc is yet another compiler compiler
            p4_objects, errors_cnt = P4Parser().parse(preprocessed_source)
            if errors_cnt > 0:
                print errors_cnt, "errors during parsing"
                print "Interrupting compilation"
                return False
            all_p4_objects += p4_objects

            # ZP: the 'p4_objects' contains each object in P4 programs,
            #     including each header, each table ...
            # for each_obj in p4_objects:
            #     print 'ZP: main-0010 all_p4_objects:', pprint(vars(each_obj))

        print "LOG|Build HLIR|parsing successful"
        p4_program = P4Program("", -1, all_p4_objects)

        # ZP: Almost the same as previous p4_objects.
        # print 'ZP: main-008', pprint(vars(p4_program))
        # for each_obj in p4_program.objects:
        #     print 'ZP: main-0012 all_p4_objects:', pprint(vars(each_obj))


        # 02. Semantic checking, round 1
        sc = P4SemanticChecker()
        errors_cnt = sc.semantic_check(p4_program, self.primitives)
        if errors_cnt > 0:
            print errors_cnt, "errors during semantic checking"
            print "Interrupting compilation"
            return False
        else:
            print "LOG|Build HLIR|1st round semantic checking successful"

        # print'ZP: main-015 self:', pprint(vars(self))

        # 03. Dump AST to HLIR objects
        d = P4HlirDumper()
        d.dump_to_p4(self, p4_program, self.primitives, program_version=program_version, config_dir=config_dir)
        # print 'ZP: main-013', d, pprint(vars(d))

        # print'ZP: main-016 self:', pprint(vars(self))


        # 04. Semantic checking, round 2
        # TODO: merge these two rounds and try to separate name resolution from
        #       higher level semantic checks
        try:
            p4.p4_validate(self, program_version=program_version)
        except p4.p4_compiler_msg as e:
            print e
            return False

        # print'ZP: main-016-XX self:', pprint(vars(self))
        # return
        # Perform target-agnostic optimizations
        if optimize:
            p4.optimize_table_graph(self)

        # Analyze program and annotate objects with derived information
        if analyze:
            p4.p4_dependencies(self)
            p4.p4_field_access(self)

        return True



    def build_shadow_metadata_AB(self, optimize=True, analyze=True, dump_preprocessed=False):
        '''Build shadow metadata: compile the shadow meta code to HLIR object
        '''
        if len(self.source_files) == 0:
            print "no source file to process"
            return False

        # 00. Pre-process all program text
        preprocessed_sources = []
        try:
            preprocessor = Preprocessor() # ZP: to use gcc pre-process souce code
            preprocessor.args += self.preprocessor_args

            # ZP: self.source_file is the fine name of P4 program
            # print 'ZP: main-003', self.source_files 
            # print 'ZP: main-004', self.source_txt
            for p4_source in self.source_files:

                absolute_source = os.path.join(os.getcwd(), p4_source)

                if not self._check_source_path(absolute_source):
                    print "Source file '" + p4_source + "' could not be opened or does not exist."
                    return False
                print 'INFO|p4_hlir|HLIR build:', absolute_source

                preprocessed_sources.append(preprocessor.preprocess_file(
                    absolute_source,
                    dest='%s.i'%p4_source if dump_preprocessed else None
                ))

            for p4_txt in self.source_txt:
                preprocessed_sources.append(preprocessor.preprocess_str(
                    p4_txt,
                    dest=None
                ))
            # ZP: preprocessed_sources is the P4.s source code
            # print 'ZP: main-006', preprocessed_sources

        except PreprocessorException as e:
            print str(e)
            return False

        # 01. Parse preprocessed text to AST
        #     Use 'yacc' and 'P4LSexer' to parse the abstract syntax tree
        #     defined in frontend/parser.py.
        all_p4_objects = []
        for preprocessed_source in preprocessed_sources:
            # ZP: (1) The parser() first build the P4Lexer in tokenizer.py
            #         P4lexer is the Lexical Analyzar of P4 language
            #     (2) Then it inits the yacc tool. Yacc is yet another compiler compiler
            p4_objects, errors_cnt = P4Parser().parse(preprocessed_source)
            if errors_cnt > 0:
                print errors_cnt, "errors during parsing"
                print "Interrupting compilation"
                return False
            all_p4_objects += p4_objects

            # ZP: the 'p4_objects' contains each object in P4 programs,
            #     including each header, each table ...
            # for each_obj in p4_objects:
            #     print 'ZP: main-0010 all_p4_objects:', pprint(vars(each_obj))

        print "LOG|Build HLIR|metadata parsing successful"
        p4_program = P4Program("", -1, all_p4_objects)

        # ZP: Almost the same as previous p4_objects.
        # print 'ZP: main-008', pprint(vars(p4_program))
        # for each_obj in p4_program.objects:
        #     print 'ZP: main-0012 all_p4_objects:', pprint(vars(each_obj))


        # 02. Semantic checking, round 1
        if 0:
            sc = P4SemanticChecker()
            errors_cnt = sc.semantic_check(p4_program, self.primitives)
            if errors_cnt > 0:
                print errors_cnt, "errors during semantic checking"
                print "Interrupting compilation"
                return False
            else:
                print "LOG|Build HLIR|1st round semantic checking successful"

        # print 'ZP: main-015 self:', pprint(vars(self))

        # 03. Dump AST to HLIR objects
        d = P4HlirDumper()
        d.dump_to_p4(self, p4_program, self.primitives)
        # print 'ZP: main-013', d, pprint(vars(d))

        # print 'ZP: main-016 self:', pprint(vars(self))


        # 04. Semantic checking, round 2
        # TODO: merge these two rounds and try to separate name resolution from
        #       higher level semantic checks

        # AB testing
        try:
            p4.p4_validate_shadow_metadata_AB(self)
        except p4.p4_compiler_msg as e:
            print e
            return False
  
        return True


    def build_shadow_metadata_DF(self, optimize=True, analyze=True, dump_preprocessed=False):
        if len(self.source_files) == 0:
            print "no source file to process"
            return False

        # 00. Pre-process all program text
        preprocessed_sources = []
        try:
            preprocessor = Preprocessor() # ZP: to use gcc pre-process source code
            preprocessor.args += self.preprocessor_args

            # ZP: self.source_file is the fine name of P4 program
            # print 'ZP: main-003', self.source_files 
            # print 'ZP: main-004', self.source_txt
            for p4_source in self.source_files:

                absolute_source = os.path.join(os.getcwd(), p4_source)

                if not self._check_source_path(absolute_source):
                    print "Source file '" + p4_source + "' could not be opened or does not exist."
                    return False
                print 'INFO|p4_hlir|HLIR build:', absolute_source

                preprocessed_sources.append(preprocessor.preprocess_file(
                    absolute_source,
                    dest='%s.i'%p4_source if dump_preprocessed else None
                ))

            for p4_txt in self.source_txt:
                preprocessed_sources.append(preprocessor.preprocess_str(
                    p4_txt,
                    dest=None
                ))
            # ZP: preprocessed_sources is the P4.s source code
            # print 'ZP: main-006', preprocessed_sources

        except PreprocessorException as e:
            print str(e)
            return False

        # 01. Parse preprocessed text to AST
        #     Use 'yacc' and 'P4LSexer' to parse the abstract syntax tree
        #     defined in frontend/parser.py.
        all_p4_objects = []
        for preprocessed_source in preprocessed_sources:
            # ZP: (1) The parser() first build the P4Lexer in tokenizer.py
            #         P4lexer is the Lexical Analyzar of P4 language
            #     (2) Then it inits the yacc tool. Yacc is yet another compiler compiler
            p4_objects, errors_cnt = P4Parser().parse(preprocessed_source)
            if errors_cnt > 0:
                print errors_cnt, "errors during parsing"
                print "Interrupting compilation"
                return False
            all_p4_objects += p4_objects

            # ZP: the 'p4_objects' contains each object in P4 programs,
            #     including each header, each table ...
            # for each_obj in p4_objects:
            #     print 'ZP: main-0010 all_p4_objects:', pprint(vars(each_obj))

        print "LOG|Build HLIR|parsing successful"
        p4_program = P4Program("", -1, all_p4_objects)

        # ZP: Almost the same as previous p4_objects.
        # print 'ZP: main-008', pprint(vars(p4_program))
        # for each_obj in p4_program.objects:
        #     print 'ZP: main-0012 all_p4_objects:', pprint(vars(each_obj))


        # 02. Semantic checking, round 1
        sc = P4SemanticChecker()
        errors_cnt = sc.semantic_check(p4_program, self.primitives)
        if errors_cnt > 0:
            print errors_cnt, "errors during semantic checking"
            print "Interrupting compilation"
            return False
        else:
            print "LOG|Build HLIR|1st round semantic checking successful"

        # print'ZP: main-015 self:', pprint(vars(self))

        # 03. Dump AST to HLIR objects
        d = P4HlirDumper()
        d.dump_to_p4(self, p4_program, self.primitives)
        # print 'ZP: main-013', d, pprint(vars(d))

        # print'ZP: main-016 self:', pprint(vars(self))


        # 04. Semantic checking, round 2
        # TODO: merge these two rounds and try to separate name resolution from
        #       higher level semantic checks
        try:
            p4.p4_validate(self)
        except p4.p4_compiler_msg as e:
            print e
            return False

        # Perform target-agnostic optimizations
        if optimize:
            p4.optimize_table_graph(self)

        # Analyze program and annotate objects with derived information
        if analyze:
            p4.p4_dependencies(self)
            p4.p4_field_access(self)

        return True



    def _check_source_path(self, source):
        return os.path.isfile(source)

def HLIR_from_txt (program_str, **kwargs):
    h = HLIR()
    h.add_src_txt(program_str)
    print 'ZP mian-009'
    if h.build(**kwargs):
        return h
    else:
        return None
