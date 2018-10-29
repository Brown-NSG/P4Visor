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

"""
Extract control flow and parse graphs to DOT graph descriptions and generate
PNGs of them
"""
import collections
import os
import subprocess
import pprint as pp
import dependency_graph
import hlir_info as info
import p4_hlir.hlir.p4 as p4
import p4_hlir.hlir.p4_tables as p4_tables
import p4_hlir.hlir.p4_imperatives as p4_imperatives

def get_call_name (node, exit_node=None):
    if node:
        return node.name
    else:
        return exit_node

def dump_table(node, exit_node, visited=None):
    # TODO: careful about tables with names with reserved DOT keywords

    p = ""
    if visited==None:
        visited = set([node])
    else:
        visited.add(node)

    if isinstance(node, p4.p4_table):
        p += "   %s [shape=ellipse];\n" % node.name
    elif isinstance(node, p4.p4_conditional_node):
        p += "   %s [shape=box label=\"%s\"];\n" % (get_call_name(node), str(node.condition))

    for label, next_node in node.next_.items():
        if isinstance(node, p4.p4_table):
            arrowhead = "normal"
            if isinstance(label, str):
                label_str = " label=\"%s\"" % label
            else:
                label_str = " label=\"%s\"" % label.name
        elif isinstance(node, p4.p4_conditional_node):
            label_str = ""
            if label:
                arrowhead = "dot"
            else:
                arrowhead = "odot"
        p += "   %s -> %s [arrowhead=%s%s];\n" % (get_call_name(node),
                                                get_call_name(next_node, exit_node),
                                                arrowhead, label_str)
        if next_node and next_node not in visited:
            p += dump_table(next_node, exit_node, visited)

    if len(node.next_) == 0:
        p += "   %s -> %s;\n" % (node.name, exit_node)

    return p

def dump_parser(node, visited=None):
    if not visited:
        visited = set()
    visited.add(node.name)

    p = ""
    p += "   %s [shape=record label=\"{" % node.name
    p += node.name
    if node.branch_on:
        p += " | {"
        for elem in node.branch_on:
            elem_name = str(elem).replace("instances.","")
            if isinstance(elem, tuple):
                elem_name = "current"+elem_name
            p += elem_name + " | "
        p = p[0:-3]
        p+="}"
    p += "}\"];\n"

    for case, target in node.branch_to.items():
        label = ""
        if not isinstance(case, list):
            case = [case]
        for caseval in case:
            if isinstance(caseval, int) or isinstance(caseval, long):
                label += hex(caseval) + ", "
            elif caseval == p4.P4_DEFAULT:
                label += "default, "
            elif isinstance(caseval, p4.p4_parse_value_set):
                label += "set("+caseval.name+"), "
        label = label[0:-2]

        dst_name = target.name
        if isinstance(target, p4.p4_table):
            dst_name = "__table_"+dst_name

        p += "   %s -> %s [label=\"%s\"];\n" % (node.name, dst_name, label)

        for _, target in node.branch_to.items():
            if isinstance(target, p4.p4_parse_state) and target.name not in visited:
                p += dump_parser(target, visited)

    return p

def generate_graph_png(dot, out):
    with open(out, 'w') as pngf:
        subprocess.check_call(["dot", "-Tpng", dot], stdout = pngf)

def generate_graph_eps(dot, out):
    with open(out, 'w') as epsf:
        subprocess.check_call(["dot", "-Teps", dot], stdout = epsf)

def generate_graph_try_format(dot_fname, out_fname, dot_format):
    with open(out_fname, 'w') as outf:
        subprocess.check_call(["dot", "-T" + dot_format, dot_fname],
                              stdout = outf)

def generate_graph(dot_fname, base_fname, dot_formats):
    for dot_format in dot_formats:
        if dot_format == 'none':
            break
        out_fname = base_fname + "." + dot_format
        success = False
        try:
            generate_graph_try_format(dot_fname, out_fname, dot_format)
            success = True
        except:
            print('Generating dot format %s for dot file %s returned error.'
                  '  Trying another.'
                  '' % (dot_format, dot_fname))
        if success:
            break


def export_parse_graph(hlir, filebase, gen_dir,
                       dot_formats = ['png', 'eps'], no_dot=False):
    program_str = "digraph g {\n"
    program_str += "   wire [shape=doublecircle];\n"
    for entry_point in hlir.p4_ingress_ptr:
        program_str += "   %s [label=%s shape=doublecircle];\n" % ("__table_"+entry_point.name, entry_point.name)

    sub_str = dump_parser(hlir.p4_parse_states["start"])
    program_str += "   wire -> start\n"
    program_str += sub_str
    program_str += "}\n"

    filename_dot = os.path.join(gen_dir, filebase + ".parser.dot")
    with open(filename_dot, "w") as dotf:
        dotf.write(program_str)

    generate_graph(filename_dot,
                   os.path.join(gen_dir, filebase + ".parser"),
                   dot_formats)
    if no_dot:
        os.remove(filename_dot)


def export_table_graph(hlir, filebase, gen_dir, predecessors=False,
                       dot_formats = ['png', 'eps'], no_dot=False):
    program_str = "digraph g {\n"
    program_str += "   buffer [shape=doublecircle];\n"
    program_str += "   egress [shape=doublecircle];\n"

    for entry_point, invokers in hlir.p4_ingress_ptr.items():
        if predecessors:
            for invoker in invokers:
                program_str += "   %s [label=%s shape=doublecircle];\n" % ("__parser_"+invoker.name, invoker.name)
                program_str += "   %s -> %s\n" % ("__parser_"+invoker.name, get_call_name(entry_point))
        program_str += dump_table(entry_point, "buffer")

    if hlir.p4_egress_ptr:
        program_str += "   buffer -> %s\n" % get_call_name(hlir.p4_egress_ptr)
        program_str += dump_table(hlir.p4_egress_ptr, "egress")
    else:
        program_str += "   buffer -> egress [arrowhead=normal]\n"
    program_str += "}\n"

    filename_dot = os.path.join(gen_dir, filebase + ".tables.dot")
    with open(filename_dot, "w") as dotf:
        dotf.write(program_str)

    generate_graph(filename_dot,
                   os.path.join(gen_dir, filebase + ".tables"),
                   dot_formats)
    if no_dot:
        os.remove(filename_dot)

def export_table_dependency_graph(hlir, filebase, gen_dir, show_conds = False,
                                  show_control_flow = True,
                                  show_condition_str = True,
                                  show_fields = True,
                                  debug_count_min_stages = False,
                                  debug_key_result_widths = False,
                                  dot_formats = ['png', 'eps'],
                                  split_match_action_events = False,
                                  show_only_critical_dependencies = False,
                                  no_dot = False):
    # TBD: Make these command line options
    min_match_latency = 9
    min_action_latency = 1

    print
    print "TABLE DEPENDENCIES..."

    tally_prim_acts_total = [collections.defaultdict(int),
                             collections.defaultdict(int)]
    for pipeline in ['ingress', 'egress']:
        print
        print "%s PIPELINE" % (pipeline.upper())

        if pipeline == 'egress' and not hlir.p4_egress_ptr:
            print "Egress pipeline is empty"
            continue

        filename_dot = os.path.join(gen_dir, (filebase + "." + pipeline +
                                              ".tables_dep.dot"))
        if pipeline == 'ingress':
            graph = dependency_graph.build_table_graph_ingress(
                hlir,
                split_match_action_events=split_match_action_events,
                min_match_latency=min_match_latency,
                min_action_latency=min_action_latency)
        else:
            graph = dependency_graph.build_table_graph_egress(
                hlir,
                split_match_action_events=split_match_action_events,
                min_match_latency=min_match_latency,
                min_action_latency=min_action_latency)
        if split_match_action_events:
            forward_crit_path_len, earliest_time = graph.critical_path(
                'forward',
                show_conds = show_conds,
                debug = debug_count_min_stages,
                debug_key_result_widths = debug_key_result_widths,
                crit_path_edge_attr_name = 'on_forward_crit_path')
            backward_crit_path_len, latest_time = graph.critical_path(
                'backward',
                show_conds = show_conds,
                debug = debug_count_min_stages,
                debug_key_result_widths = debug_key_result_widths,
                crit_path_edge_attr_name = 'on_backward_crit_path')
            if forward_crit_path_len != backward_crit_path_len:
                print("forward and backward critical path length calculations"
                      " give different answers -- possible bug: %d vs. %d"
                      "" % (forward_crit_path_len, backward_crit_path_len))
            min_stages = forward_crit_path_len
        else:
            min_stages, earliest_time = graph.count_min_stages(
                show_conds = show_conds,
                debug = debug_count_min_stages,
                debug_key_result_widths = debug_key_result_widths)
            latest_time = None
        print "pipeline", pipeline, "requires at least", min_stages, "stages"

        # Create output data that can be used for an external
        # scheduler/optimizer.
        # TBD: Make this controlled by new command line option
        create_dependency_data = True
        if create_dependency_data:
            sched_fname = os.path.join(gen_dir, (filebase + "." + pipeline +
                                                 ".sched_data.txt")),
            schedf = open(sched_fname[0], 'w')
        if create_dependency_data and split_match_action_events:
            tables_by_earliest_time = sorted(earliest_time.keys(),
                                             key=lambda t: [earliest_time[t],
                                                            t.name])
            node_data = {}
            edge_data = {}
            for table in tables_by_earliest_time:
                if isinstance(table.p4_node, p4_tables.p4_conditional_node):
                    # Condition nodes probably best treated as 'free'
                    # action nodes, i.e. num_fields == 0, at least
                    # until we figure out something more precise.
                    node_info = {'type': 'condition',
                                 'num_fields': 0,
                                 'condition': str(table.p4_node.condition)}
                else:
                    p4table = table.p4_node
                    if table.name[-6:] == '_MATCH':
                        if info.pure_action_table(p4table):
                            # Then do not generate a match node for
                            # this table.  It is likely a table
                            # created solely for the side effect of
                            # its action.
                            node_info = None
                        else:
                            match_info = info.match_field_info(p4table)
                            key_width = match_info['total_field_width']
                            # There are at least a few tables that
                            # have actions that actually cause side
                            # effects, but they have 0 search key
                            # bits.  Treat them as having 1 search key
                            # bit, since if in the hardware they are
                            # implemented as sending out a 'read
                            # request' for the 1 entry that is
                            # effectively in the table, it will
                            # consume a little bit of match key
                            # bandwidth out of the processor.
                            if key_width == 0:
                                key_width = 1
                            node_info = {'type': 'match',
                                         'key_width': key_width}
                    elif table.name[-7:] == '_ACTION':
                        act_info = info.action_info(p4table)
                        node_info = {
                            'type': 'action',
                            'num_fields': act_info['max_primitive_actions']}
                    else:
                        # some internal error.  Should not happen
                        assert(False)
                if node_info is not None:
                    node_data[table.name] = node_info
            debug_edge_min_latency = False
            for node_from in tables_by_earliest_time:
                if debug_edge_min_latency:
                    print('dbg node_from.name=%s' % (node_from.name))
                if node_from.name not in node_data:
                    if debug_edge_min_latency:
                        print('    dbg node_from.name not in node_data')
                    continue
                for node_to, edge in node_from.edges.items():
                    if debug_edge_min_latency:
                        print('    dbg node_to.name=%s' % (node_to.name))
                    if node_to.name not in node_data:
                        if debug_edge_min_latency:
                            print('        dbg node_to.name not in node_data')
                        continue
                    if edge.type_ <= 0:
                        if debug_edge_min_latency:
                            print('        dbg edge.type_ %d <= 0' % (edge.type_))
                        continue
                    
                    edge_condition = None
                    if edge.type_ == dependency_graph.Dependency.SUCCESSOR:
                        if isinstance(edge.dep.value, bool):
                            edge_condition = edge.dep.value
                           # print("----------------------------------------------------------------------")
                           # print("dbg edge.__dict__=")
                           # pp.pprint(edge.__dict__)
                           # print("dbg edge.dep.__dict__=")
                           # pp.pprint(edge.dep.__dict__)
                           # print("dbg edge.dep.from_.__dict__=")
                           # pp.pprint(edge.dep.from_.__dict__)
                           # print("dbg edge.dep.from_.condition=%s"
                           #       % (edge.dep.from_.condition))
                           # print("dbg edge.dep.from_.condition.__dict__=")
                           # pp.pprint(edge.dep.from_.condition.__dict__)
                        elif isinstance(edge.dep.value, p4_imperatives.p4_action):
                            # I believe this case is just like the
                            # next one, except it is for the special
                            # case of a single action being the
                            # condition, whereas the tuple case is
                            # when there are multiple possible actions
                            # ORed together.
                           # print("dbg successor type(edge.dep.value) %s"
                           #       " edge.dep.value=%s"
                           #       "" % (type(edge.dep.value), edge.dep.value))
                            tmp_actions = [edge.dep.value]
                            edge_condition = list(map(lambda v: v.name,
                                                      tmp_actions))
                        elif isinstance(edge.dep.value, tuple):
                            edge_condition = list(map(lambda v: v.name,
                                                      edge.dep.value))
                           # print("dbg successor type(edge.dep.value) %s"
                           #       " edge.dep.value=%s edge_condition=%s"
                           #       "" % (type(edge.dep.value), edge.dep.value,
                           #             edge_condition))
                        else:
                            print("dbg successor type(edge.dep.value) %s"
                                  " edge.dep.value=%s"
                                  "" % (type(edge.dep.value), edge.dep.value))
                            assert False
                    assert('dep_type' in edge.attributes)
                    edge_attrs = {'delay': edge.attributes['min_latency'],
                                  'dep_type': edge.attributes['dep_type']}
                    if edge_condition is not None:
                        edge_attrs['condition'] = edge_condition
                    edge_data[(node_from.name, node_to.name)] = edge_attrs
            print >>schedf, 'nodes = \\'
            pp.pprint(node_data, stream=schedf)
            print >>schedf, '\nedges = \\'
            pp.pprint(edge_data, stream=schedf)

        if create_dependency_data and not split_match_action_events:
            # TBD
            pass

        if create_dependency_data:
            schedf.close()

        # Show extra details about tables and/or their actions
        print('')
        print "%s action details" % (pipeline)
        print('')
        tables_by_earliest_time = sorted(earliest_time.keys(),
                                         key=lambda t: [earliest_time[t],
                                                        t.name])
        tally_prim_act_kinds = [collections.defaultdict(int),
                                collections.defaultdict(int)]
        tables_by_max_prim_acts = [collections.defaultdict(list),
                                   collections.defaultdict(list)]
        table_num = 0
        for table in tables_by_earliest_time:
            if isinstance(table.p4_node, p4_tables.p4_conditional_node):
                continue
            if split_match_action_events and table.name[-6:] == '_MATCH':
                # Only show the details about actions for the
                # '_ACTION' node in the graph, not the '_MATCH' node,
                # otherwise we will show all details twice.
                continue
           # print('dbg type(table)=%s' % (type(table.p4_node)))
           # print('    table.__dict__=%s' % (table.p4_node.__dict__))
            p4table = table.p4_node
            match_info = info.match_field_info(p4table)
            result_info = info.result_info(p4table)
            # Keep separate tallies of primitive action kinds used,
            # depending on whether they are in 'pure action' tables or
            # not.
            if info.pure_action_table(p4table, match=match_info,
                                      result=result_info):
                tmp_idx = 0
            else:
                tmp_idx = 1
            act_info = info.action_info(p4table,
                                        tally=tally_prim_act_kinds[tmp_idx],
                                        debug=False)
           # print('%d %s' % (table_num, table.name))
            num_actions = len(act_info['action_descriptions'])
            max_primitive_actions = act_info['max_primitive_actions']
            print('table %s search_bits %d res_bits %d'
                  ' num_act %d max_prim_acts %d' % (
                      act_info['table_name'],
                      match_info['total_field_width'],
                      result_info['result_width'],
                      num_actions,
                      max_primitive_actions))
            tables_by_max_prim_acts[tmp_idx][max_primitive_actions].append(table)
            for i in range(0, num_actions):
                print('  %d: %d %s' % (
                    i,
                    len(act_info['action_descriptions'][i]),
                    ' '.join(act_info['action_descriptions'][i])))
            table_num += 1
        for tmp_idx in [1, 0]:
            if tmp_idx == 0:
                tmp_desc = 'pure action'
            else:
                tmp_desc = 'regular'
            print
            print("%s action count for %s tables"
                  "" % (pipeline, tmp_desc))
            info.print_tally_of_primitive_actions(tally_prim_act_kinds[tmp_idx])
            for k in tally_prim_act_kinds[tmp_idx]:
                tally_prim_acts_total[tmp_idx][k] += tally_prim_act_kinds[tmp_idx][k]

            print
            print("Number of %s %s tables with given max number"
                  " of primitive actions for any of its actions:"
                  "" % (pipeline, tmp_desc))
            print "max  # of   cum. # cum."
            print "acts tables tables fract"
            print "---- ------ ------ -----"
            sorted_list = sorted(tables_by_max_prim_acts[tmp_idx].keys())
            n = 0
            for max_primitive_actions in sorted_list:
                n += len(tables_by_max_prim_acts[tmp_idx][max_primitive_actions])
            cum_n = 0
            for max_primitive_actions in sorted_list:
                x = len(tables_by_max_prim_acts[tmp_idx][max_primitive_actions])
                cum_n += x
                print("%4d %6d %6d %5.1f%%" % (
                    max_primitive_actions,
                    x, cum_n, (100.0 * cum_n) / n))

        show_min_max_scheduled_times = split_match_action_events
        with open(filename_dot, 'w') as dotf:
            graph.generate_dot(
                out = dotf,
                show_control_flow = show_control_flow,
                show_condition_str = show_condition_str,
                show_fields = show_fields,
                earliest_time = earliest_time,
                latest_time = latest_time,
                show_min_max_scheduled_times = show_min_max_scheduled_times,
                show_only_critical_dependencies = show_only_critical_dependencies,
                forward_crit_path_edge_attr_name = 'on_forward_crit_path',
                backward_crit_path_edge_attr_name = 'on_backward_crit_path')

        generate_graph(filename_dot,
                       os.path.join(gen_dir, (filebase + "." + pipeline +
                                              ".tables_dep")),
                       dot_formats)
        if no_dot:
            os.remove(filename_dot)

    overall_total = collections.defaultdict(int)
    for tmp_idx in [1, 0]:
        if tmp_idx == 0:
            tmp_desc = 'pure action'
        else:
            tmp_desc = 'regular'
        print
        print("ingress plus egress action count for %s tables"
              "" % (tmp_desc))
        info.print_tally_of_primitive_actions(tally_prim_acts_total[tmp_idx])
        for k in tally_prim_acts_total[tmp_idx]:
            overall_total[k] += tally_prim_acts_total[tmp_idx][k]

    print
    print "ingress plus egress action count"
    info.print_tally_of_primitive_actions(overall_total)

    print
