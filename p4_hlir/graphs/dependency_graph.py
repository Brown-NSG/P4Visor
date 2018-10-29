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

import p4_hlir.hlir
import sys
import copy
import pprint
from collections import defaultdict
from p4_hlir.hlir.dependencies import *
import hlir_info as info
import p4_hlir.hlir.p4_imperatives as p4_imperatives


def munge_condition_str(s):
    """if conditions can be quite long.  In practice the graphs can be a
    bit less unwieldy if conditions containing and/or are split
    across multiple lines.
    """
    return s.replace(' and ', ' and\n').replace(' or ', ' or\n')


class Dependency:
    CONTROL_FLOW = 0
    REVERSE_READ = 1
    SUCCESSOR = 2
    ACTION = 3
    MATCH = 4

    _types = {REVERSE_READ: "REVERSE_READ",
              SUCCESSOR: "SUCCESSOR",
              ACTION: "ACTION",
              MATCH: "MATCH"}

    @staticmethod
    def get(type_):
        return Dependency._types[type_]

class Node:
    CONDITION = 0
    TABLE = 1
    TABLE_ACTION = 2
    def __init__(self, name, type_, p4_node):
        self.type_ = type_
        self.name = name
        self.edges = {}
        self.p4_node = p4_node

    def add_edge(self, node, edge):
        if node in self.edges:
            print('Trying to add second edge from node %s name %s'
                  ' to node %s name %s'
                  ' existing edge %s type %s'
                  ' new edge %s type %s'
                  '' % (self, self.name,
                        node, node.name,
                        self.edges[node], self.edges[node].type_,
                        edge, edge.type_))
        assert(node not in self.edges)
        self.edges[node] = edge

class Edge:
    def __init__(self, dep = None):
        self.attributes = {}
        if not dep:
            self.type_ = Dependency.CONTROL_FLOW
            self.dep = None
            return

        if isinstance(dep, ReverseReadDep):
            self.type_ = Dependency.REVERSE_READ
        elif isinstance(dep, SuccessorDep):
            self.type_ = Dependency.SUCCESSOR
        elif isinstance(dep, ActionDep):
            self.type_ = Dependency.ACTION
        elif isinstance(dep, MatchDep):
            self.type_ = Dependency.MATCH
        else:
            assert(False)
        self.dep = dep
        
class Graph:
    def __init__(self, name):
        self.name = name
        self.nodes = {}
        self.root = None

    def get_node(self, node_name):
        return self.nodes.get(node_name, None)

    def add_node(self, node):
        self.nodes[node.name] = node

    def set_root(self, node):
        self.root = node

    def topo_sorting(self):
        if not self.root: return False

        # slightly annoying because the graph is directed, we use a topological
        # sorting algo
        # see http://en.wikipedia.org/wiki/Topological_sorting#Algorithms
        # (second algo)
        def visit(cur, sorted_list):
            if cur.mark == 1:
                return False
            if cur.mark != 2:
                cur.mark = 1
                for node_to, edge in cur.edges.items():
                    if not visit(node_to, sorted_list):
                        return False
                cur.mark = 2
                sorted_list.insert(0, cur)
            return True

        has_cycle = False
        sorted_list = []
        for n in self.nodes.values():
            # 0 is unmarked, 1 is temp, 2 is permanent
            n.mark = 0
        for n in self.nodes.values():
            if n.mark == 0:
                if not visit(n, sorted_list):
                    has_cycle = True
                    break
        for n in self.nodes.values():
            del n.mark

        return has_cycle, sorted_list

    def critical_path(self, direction, show_conds = False,
                      debug = False,
                      debug_key_result_widths = False,
                      crit_path_edge_attr_name = None,
                      almost_crit_path_edge_attr_name = None,
                      almost_crit_path_delta = 20):

        # If direction == 'forward', calculate the longest paths from
        # the beginning (nodes with no in-edges) to the end (nodes
        # with on out-edges).  This gives the earliest time that each
        # node can be scheduled, subject to the constraints specified
        # by the edges.

        # If direction == 'backward', calculate the longest paths from
        # the end back to the beginning, following edges in the
        # reverse direction.  If we take those path lengths x and
        # replace them with (max_path_length - x), that should give
        # the latest time that each node can be scheduled, subject to
        # the constraints specified by the edges.

        has_cycle, forward_sorted_list = self.topo_sorting()
        assert(not has_cycle)
        dir_edges = {}
        
        if direction == 'forward':
            sorted_list = copy.copy(forward_sorted_list)
            for node_from in forward_sorted_list:
                dir_edges[node_from] = node_from.edges
        else:
            # Calculate set of edges into each node, from the forward
            # edges.
            sorted_list = copy.copy(forward_sorted_list)
            sorted_list.reverse()
            for node_to in sorted_list:
                dir_edges[node_to] = {}
            # In this for loop 'node_from' and 'node_to' are the
            # direction of the edge in the original dependencies.  In
            # dir_edges we are intentionally reversing that direction.
            for node_from in sorted_list:
                for node_to, edge in node_from.edges.items():
                    dir_edges[node_to][node_from] = edge

        max_path = {}
        crit_path_edges_into = defaultdict(dict)
        for table in sorted_list:
            if table not in max_path:
                max_path[table] = 0
            for node_to, edge in dir_edges[table].items():
                if edge.type_ > 0 and 'min_latency' in edge.attributes:
                    this_path_len = (max_path[table] +
                                     edge.attributes['min_latency'])
                    table_on_a_crit_path = False
                    if node_to in max_path:
                        if this_path_len > max_path[node_to]:
                            max_path[node_to] = this_path_len
                            table_on_a_crit_path = True
                            # Found new path longer than any
                            # previously known, so clear out the
                            # critical path edges remembered so far,
                            # since they are definitely not any more.
                            crit_path_edges_into[node_to] = {}
                        elif this_path_len == max_path[node_to]:
                            table_on_a_crit_path = True
                    else:
                        max_path[node_to] = this_path_len
                        table_on_a_crit_path = True
                    if table_on_a_crit_path:
                        # Update list of tables/edges into node_to
                        # that are on a critical path.
                        crit_path_edges_into[node_to][table] = edge
                else:
                    assert(edge.type_ <= 0)
                    assert('min_latency' not in edge.attributes)
                   # print('dbg critical_path found an edge with no min_latency'
                   #       ' attributes: from %s to %s type_ %s'
                   #       '' % (table.name, node_to.name, edge.type_))

        max_path_length = 0
        for table in sorted_list:
            if max_path[table] > max_path_length:
                max_path_length = max_path[table]

        if direction == 'backward':
            # Replace maximum paths x with (max_path_length - x)
            for table in sorted_list:
                max_path[table] = (max_path_length - max_path[table])

        if debug:
            print('')
            print('')
            print('direction %s' % (direction))
            print('')
        # Including table names in sort keys helps make the order
        # repeatable across multiple runs.
        tables_by_max_path = sorted(sorted_list,
                                    key=lambda t: [max_path[t], t.name])
        for table in tables_by_max_path:
            if table in crit_path_edges_into:
                # Again, this sorting makes the output repeatable
                # across runs.
                crit_path_edges_by_table_name = sorted(
                    crit_path_edges_into[table].keys(),
                    key=lambda x: x.name)
                for from_table in crit_path_edges_by_table_name:
                    edge = crit_path_edges_into[table][from_table]
                    dname = Dependency._types.get(edge.type_, 'unknown')
                    x = max_path[from_table]
                    y = edge.attributes['min_latency']
                    z = max_path[table]
                    if direction == 'forward':
                        print_op = '+'
                    if direction == 'backward':
                        print_op = '-'
                        y = -y
                    if x + y != z:
                        print('dbg assert direction %s'
                              ' from_table.name %s max_path %s'
                              ' table.name %s max_path %s'
                              ' edge.type_ %s dname %s min_latency %s'
                              '' % (direction,
                                    from_table.name, x,
                                    table.name, z,
                                    edge.type_, dname, y))
                    assert (x + y == z)
                    if debug:
                        print("%-35s %-3s  %3d%s%2d = %3d  %s"
                              "" % (from_table.name, dname[0:3],
                                    max_path[from_table],
                                    print_op,
                                    edge.attributes['min_latency'],
                                    max_path[table],
                                    table.name))
                    if crit_path_edge_attr_name is not None:
                        edge.attributes[crit_path_edge_attr_name] = True
            else:
                if direction == 'forward':
                    assert (max_path[table] == 0)
                elif direction == 'backward':
                    assert (max_path[table] == max_path_length)
                print("%-35s %-3s  %8s %3d  %s"
                      "" % ("(no predecessor)", "-", "",
                            max_path[table], table.name))

        if almost_crit_path_edge_attr_name is not None:
            for table in sorted_list:
                for node_to, edge in table.edges.items():
                    y = edge.attributes.get('min_latency', None)
                    if y is None:
                        continue
                    x = max_path[from_table]
                    z = max_path[table]
                    if (x + y < z) and (x + y > z - almost_crit_path_delta):
                        edge.attributes[almost_crit_path_edge_attr_name] = True

        return max_path_length, max_path

        
    def count_min_stages(self, show_conds = False,
                         debug = False,
                         debug_key_result_widths = False):
        has_cycle, sorted_list = self.topo_sorting()
        assert(not has_cycle)
        nb_stages = 0
        stage_list = []
        stage_dependencies_list = []
        stage_dependencies_table_list = []
        if debug:
            print('------------------------------')
            print('Debug count_min_stages')
            print("from table/condition       dependency type stage to table/condition")
            print("-------------------------- --------------- ----- ------------------")
        for table in sorted_list:
            d_type_ = 0
            d_table_from_ = '(none)'
            i = nb_stages - 1
            while i >= 0:
                stage = stage_list[i]
                stage_dependencies = stage_dependencies_list[i]
                if table in stage_dependencies:
                    d_type_ = stage_dependencies[table]
                    d_table_from_ = stage_dependencies_table_list[i][table].name
                    assert(d_type_ > 0)
                    break
                else:
                    i -= 1
            orig_i = i
            if d_type_ == 0:
                i += 1
            elif d_type_ >= Dependency.ACTION:
                i += 1
            if debug:
                if d_type_ in Dependency._types:
                    dname = Dependency._types[d_type_]
                else:
                    dname = 'unknown'
                print("%-26s %d %-12s  %2d+%d  %s"
                      "" % (d_table_from_, d_type_, dname,
                            orig_i, i - orig_i, table.name))
            if i == nb_stages:
                stage_list.append(set())
                stage_dependencies_list.append(defaultdict(int))
                stage_dependencies_table_list.append({})
                nb_stages += 1
                
            stage = stage_list[i]
            stage_dependencies = stage_dependencies_list[i]
            stage.add(table)
            for node_to, edge in table.edges.items():
                type_ = edge.type_
                if type_ > 0 and type_ > stage_dependencies[node_to]:
                    stage_dependencies[node_to] = type_                
                    stage_dependencies_table_list[i][node_to] = table
        if debug:
            print('------------------------------')
        if debug_key_result_widths:
            print('------------------------------')
            print('Debug table search key and table result widths')
            print('------------------------------')
            for stage in stage_list:
                for table in sorted(stage, key=lambda t: t.name):
                    if not show_conds and table.type_ is Node.CONDITION:
                        continue
                    pprint.pprint(info.match_field_info(table.p4_node))
                    pprint.pprint(info.result_info(table.p4_node))
            print('------------------------------')
        
        lines = []
        lines.append("      search")
        lines.append("      key    result")
        lines.append("stage width  width  table/condition name")
        lines.append("----- ------ ------ --------------------")
        stage_num = 0
        total_key_width = 0
        total_result_width = 0
        for stage in stage_list:
            stage_num += 1
            stage_key_width = 0
            stage_result_width = 0
            lines2 = []
            # Sorting here is simply to try to get a more consistent
            # output from one run of the program to the next.
            for table in sorted(stage, key=lambda t: t.name):
                if not show_conds and table.type_ is Node.CONDITION:
                    continue
                key_width = info.match_field_info(table.p4_node)['total_field_width']
                result_width = info.result_info(table.p4_node)['result_width']
                lines2.append("%5d %6d %6d %s" % (stage_num, key_width,
                                                  result_width, table.name))
                stage_key_width += key_width
                stage_result_width += result_width
            lines.append("--- stage %d of %d total search key width %d"
                         " result width %d"
                         "" % (stage_num, nb_stages, stage_key_width,
                               stage_result_width))
            lines += lines2
            total_key_width += stage_key_width
            total_result_width += stage_result_width
        for line in lines:
            print(line)
        print("For all stages, total search key width %d result width %d"
              "" % (total_key_width, total_result_width))

        max_path = {}
        path_length = 0
        for stage in stage_list:
            for table in stage:
                max_path[table] = path_length
            path_length += 1
        return nb_stages, max_path


    def generate_dot(self, out = sys.stdout,
                     show_control_flow = True,
                     show_condition_str = True,
                     show_fields = True,
                     earliest_time = None,
                     latest_time = None,
                     show_min_max_scheduled_times = False,
                     show_only_critical_dependencies = False,
                     forward_crit_path_edge_attr_name = None,
                     backward_crit_path_edge_attr_name = None):
        styles = {Dependency.CONTROL_FLOW: "style=dotted",
                  Dependency.REVERSE_READ: "color=orange",
                  Dependency.SUCCESSOR: "color=green",
                  Dependency.ACTION: "color=blue",
                  Dependency.MATCH: "color=red"}
        on_crit_path_style = "style=bold"
        off_crit_path_style = "style=dashed"
        out.write("digraph " + self.name + " {\n")

        # The uses of the 'sorted' function below are not necessary
        # for correct behavior, but are done to try to make the
        # contents of the dot output file in a more consistent order
        # from one run of this program to the next.  By default,
        # Python dicts and sets can have their iteration order change
        # from one run of a program to the next because the hash
        # function changes from one run to the next.
        nodes_by_name = list(sorted(self.nodes.values(),
                                    key=lambda node: node.name))

        # set conditional tables to be represented as boxes
        for node in nodes_by_name:
            node_attrs = ""
            node_label = node.name
            if node.type_ == Node.CONDITION:
                node_attrs = " shape=box"
                if show_condition_str:
                    node_label += (
                        "\\n" +
                        munge_condition_str(str(node.p4_node.condition)))
            if show_min_max_scheduled_times:
                early = "-"
                if earliest_time and node in earliest_time:
                    early = "%s" % (earliest_time[node])
                late = "-"
                if latest_time and node in latest_time:
                    late = "%s" % (latest_time[node])
                node_label += "\\n" + early + "," + late
            node_attrs += " label=\"" + node_label + "\""
            if show_min_max_scheduled_times:
                if early == late and early != "-":
                    node_attrs += " style=bold"
                else:
                    node_attrs += " style=dashed"
            out.write(node.name + " [" + node_attrs + "];\n")

        for node in nodes_by_name:
            node_tos_by_name = sorted(list(node.edges.keys()),
                                      key=lambda node: node.name)
            for node_to in node_tos_by_name:
                edge = node.edges[node_to]
                if not show_control_flow and edge.type_ == Dependency.CONTROL_FLOW:
                    continue
                if show_only_critical_dependencies:
                    fwd = edge.attributes.get(forward_crit_path_edge_attr_name,
                                              False)
                    bkwd = edge.attributes.get(backward_crit_path_edge_attr_name,
                                               False)
                    if not (fwd or bkwd):
                        continue
                
                edge_label = ""
                edge_attrs = ""
                if edge.type_ != Dependency.CONTROL_FLOW and show_fields:
                    dep_fields = []
                    # edge.dep can be None with my recent changes to
                    # split tables into a separate match and action node,
                    # because the edge between them has edge.dep of None.
                    if edge.dep is not None:
                        for field in edge.dep.fields:
                            dep_fields.append(str(field))
                    dep_fields = sorted(dep_fields)
                    edge_label = ",\n".join(dep_fields)
                    
                if edge.type_ == Dependency.SUCCESSOR:
                    if isinstance(edge.dep.value, bool):
                        if edge_label != "":
                            edge_label += "\n"
                        if edge.dep.value == False:
                            edge_label += "False"
                            edge_attrs += " arrowhead = diamond"
                        else:
                            edge_label += "True"
                            #edge_attrs += " arrowhead = dot"
                    elif isinstance(edge.dep.value, p4_imperatives.p4_action):
                        edge_label += edge.dep.value.name
                    elif isinstance(edge.dep.value, tuple):
                        tmp_names = map(lambda v: v.name, edge.dep.value)
                        edge_label += ',\n'.join(tmp_names)
                    else:
                        print("dbg successor type(edge.dep.value) %s"
                              " edge.dep.value=%s"
                              "" % (type(edge.dep.value), edge.dep.value))
                        assert False
                if show_only_critical_dependencies:
                    if fwd and bkwd:
                        edge_attrs += " " + on_crit_path_style
                    elif fwd:
                       # if edge_label != "":
                       #     edge_label = "\n" + edge_label
                       # edge_label = "f" + edge_label
                        pass
                    elif bkwd:
                       # if edge_label != "":
                       #     edge_label = "\n" + edge_label
                       # edge_label = "b" + edge_label
                        pass
                    else:
                        edge_attrs += " " + off_crit_path_style
                if edge_label != "":
                    edge_attrs = ("label=\"" + edge_label + "\"" +
                                  " decorate=true " + edge_attrs)
                out.write(node.name + " -> " + node_to.name +\
                          " [" + styles[edge.type_] + \
                          " " + edge_attrs + "]" + ";\n")
        out.write("}\n")

def _graph_get_or_add_node(graph, p4_node):
    node = graph.get_node(p4_node.name)
    if not node:
        if isinstance(p4_node, p4_hlir.hlir.p4_conditional_node):
            type_ = Node.CONDITION
        else:
            type_ = Node.TABLE
        node = Node(p4_node.name, type_, p4_node)
        graph.add_node(node)
    return node

def generate_graph(p4_root, name):
    graph = Graph(name)
    next_tables = {p4_root}
    visited = set()

    root_set = False

    while next_tables:
        nt = next_tables.pop()
        if nt in visited: continue
        if not nt: continue

        visited.add(nt)

        node = _graph_get_or_add_node(graph, nt)
        if not root_set:
            graph.set_root(node)
            root_set = True

        for table, dep in nt.dependencies_for.items():
            node_to = _graph_get_or_add_node(graph, table)
            edge = Edge(dep)
            node.add_edge(node_to, edge)

        next_ = set(nt.next_.values())
        for table in next_:
            if table and table not in nt.dependencies_for:
                node_to = _graph_get_or_add_node(graph, table)
                edge = Edge()
                node.add_edge(node_to, edge)

        next_tables.update(next_)
        
    return graph

def _graph_add_new_node_pair(graph, p4_node, min_match_latency):
    """Like _graph_get_or_add_node, except the caller wants an exception
    to be raised if they mistakenly try to add the same node more than
    once.
    """
    node = graph.get_node(p4_node.name)
    if node:
        msg = ("graph %s already has a node with name %s"
               "" % (graph, p4_node.name))
        raise ValueError(msg)
    if isinstance(p4_node, p4_hlir.hlir.p4_conditional_node):
        node = Node(p4_node.name, Node.CONDITION, p4_node)
        graph.add_node(node)
        return {'match': node, 'action': node, 'edge': None}
    else:
        match_node = Node(p4_node.name + "_MATCH", Node.TABLE, p4_node)
        action_node = Node(p4_node.name + "_ACTION", Node.TABLE_ACTION, p4_node)
        graph.add_node(match_node)
        graph.add_node(action_node)
        edge = Edge()
        # Probably a new dependency type might be reasonable here, but
        # for now just use Dependency.MATCH
        edge.type_ = Dependency.MATCH
        assert(min_match_latency is not None)
        edge.attributes['min_latency'] = min_match_latency
        edge.attributes['dep_type'] = 'new_match_to_action'
        match_node.add_edge(action_node, edge)
        return {'match': match_node, 'action': action_node, 'edge': edge}

def generate_graph2(p4_root, name, min_match_latency, min_action_latency):

    """This function is similar to generate_graph in some ways, but here
    the intent is to represent table match events and table action
    events as separate nodes, each with their own dependencies and
    their own time that they can be scheduled relative to one another.

       table match event - create and launch a search key.  A
       processor could do nothing until the result returns, but more
       interestingly it could do other things before the result comes
       back, such as launching other search keys or doing actions that
       do not depend upon the result.

       table action event - use the result of an earlier table match
       event, plus perhaps some local packet header fields.  Determine
       which, if any, local packet fields to modify, and what their
       new values should be.  Then write them.

    There are also nodes for conditions, of which there is still only
    one for each condition, which reads the fields involved in the
    condition and calculates the boolean result.

    """

    graph = Graph(name)
    name_to_nodes = {}
    root_set = False

    # Create all nodes first.  This allows us to ensure that
    # name_to_nodes is defined for all nodes, before trying to add the
    # edges.
    next_tables = {p4_root}
    visited = set()
    while next_tables:
        nt = next_tables.pop()
        if nt in visited: continue
        if not nt: continue
        visited.add(nt)
        nodes = _graph_add_new_node_pair(graph, nt, min_match_latency)
        name_to_nodes[nt.name] = nodes
        if not root_set:
            graph.set_root(nodes['match'])
            root_set = True
        next_ = set(nt.next_.values())
        next_tables.update(next_)

    # Now do another pass to add all edges
    next_tables = {p4_root}
    visited = set()
    while next_tables:
        nt = next_tables.pop()
        if nt in visited: continue
        if not nt: continue
        visited.add(nt)

        # Add edges for dependencies other than CONTROL_FLOW
        nodes = name_to_nodes[nt.name]
        for table, dep in nt.dependencies_for.items():
            nodes_to = name_to_nodes[table.name]
            edge = Edge(dep)
            # TBD: Different cases here depending upon the type of
            # dependency.
            if edge.type_ == Dependency.MATCH:
                edge.attributes['min_latency'] = min_action_latency
                edge.attributes['dep_type'] = 'rmt_match'
                nodes['action'].add_edge(nodes_to['match'], edge)
            elif edge.type_ == Dependency.ACTION:
                # TBD: ACTION dependencies are currently created even
                # if the 'from' table's action writes, and the 'to'
                # table's action writes.  It seems most precise in
                # that case to let the two actions to be scheduled
                # simultaneously, or with the 'from' actions earlier.
                # The only thing that should be disallowed is to
                # schedule the 'from' actions later than the 'to'
                # actions.
                #
                # For action write -> action read dependency, they
                # should not be allowed to be scheduled
                # simultaneously, e.g. second action should be at
                # least 1 cycle later than the first (or whatever the
                # minimum action to action latency is configured to
                # be).
                #
                # For now, make these two cases the same by using the
                # second kind of dependency, the more restrictive one
                # for scheduling.
                edge.attributes['min_latency'] = min_action_latency
                edge.attributes['dep_type'] = 'rmt_action'
                nodes['action'].add_edge(nodes_to['action'], edge)
            elif edge.type_ == Dependency.SUCCESSOR:
                # TBD: Where should an edge be added for this kind of
                # dependency?
                #
                # If 'from' is a table and 'to' is a table, maybe the
                # most accurate way to do it is to make a dependency
                # from the 'from' table's match event to the 'to'
                # table's action event.  This would allow the 'to'
                # table's match event to happen before the 'from'
                # table's action event.  The 'to' table's action must
                # be after the 'from' table's match event, but there
                # would be no dependence between their action events,
                # so they could be scheduled simultaneously.
                #
                # If either or both were a condition instead of a
                # table, then that still seems reasonable.
                if isinstance(nt, p4_hlir.hlir.p4_conditional_node):
                    edge.attributes['min_latency'] = 0
                    edge.attributes['dep_type'] = 'rmt_successor'
                else:
                    edge.attributes['min_latency'] = min_match_latency
                    edge.attributes['dep_type'] = 'new_successor_conditional_on_table_result_action_type'
                nodes['match'].add_edge(nodes_to['action'], edge)
            elif edge.type_ == Dependency.REVERSE_READ:

                # TBD: Most accurate way to do this would be an edge
                # from the 'from' table's action event to the 'to'
                # table's action event, if there is a common field
                # read by 'from's action written by 'to's action, with
                # 0 clock cycles of latency required.

                # Or else, if there is no such common field, but there
                # is one between the 'from' table's match event to
                # 'to's action, then make the edge only between those
                # events, again with 0 clock cycles of latency
                # required.  They can be scheduled in the same clock
                # cycle without a problem, I believe.

                # For now, always do the first kind, the more
                # restrictive one, to be safe.
                edge.attributes['min_latency'] = 0
                edge.attributes['dep_type'] = 'rmt_reverse_read'
                nodes['action'].add_edge(nodes_to['action'], edge)
            else:
                assert(False)

        # Add edges for CONTROL_FLOW dependencies
        next_ = set(nt.next_.values())
        for table in next_:
            if table and table not in nt.dependencies_for:
                nodes_to = name_to_nodes[table.name]
                edge = Edge()
                edge.attributes['dep_type'] = 'rmt_control_flow'
                nodes['action'].add_edge(nodes_to['match'], edge)

        next_tables.update(next_)
        
    return graph

# returns a rmt_table_graph object for ingress
def build_table_graph_ingress(hlir, split_match_action_events=False,
                              min_match_latency=None,
                              min_action_latency=None):
    if split_match_action_events:
        assert min_match_latency
        assert min_action_latency
        return generate_graph2(hlir.p4_ingress_ptr.keys()[0], "ingress",
                               min_match_latency, min_action_latency)
    else:
        return generate_graph(hlir.p4_ingress_ptr.keys()[0], "ingress")

# returns a rmt_table_graph object for egress
def build_table_graph_egress(hlir, split_match_action_events=False,
                             min_match_latency=None,
                             min_action_latency=None):
    if split_match_action_events:
        assert min_match_latency
        assert min_action_latency
        return generate_graph2(hlir.p4_egress_ptr, "egress",
                               min_match_latency, min_action_latency)
    else:
        return generate_graph(hlir.p4_egress_ptr, "egress")
