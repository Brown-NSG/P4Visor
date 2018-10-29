import p4_hlir.hlir
import sys
import copy
from pprint import pprint
import json
from collections import defaultdict
from p4_hlir.hlir.dependencies import *
import p4_hlir.graphs.hlir_info as info
import p4_hlir.hlir.p4_imperatives as p4_imperatives

from collections import OrderedDict

import os
from collections import defaultdict

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
        self.id = -1
        self.SP4_tb_width = -1
        self.SP4_tb_depth = 1

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

def munge_condition_str(s):
    """if conditions can be quite long.  In practice the graphs can be a
    bit less unwieldy if conditions containing and/or are split
    across multiple lines.
    """
    return s.replace(' and ', ' and\n').replace(' or ', ' or\n')


class Graph:
    def __init__(self, name):
        self.name = name
        self.nodes = {}
        self.root = None
        ## record map of table name and table id 
        self.SP4_id2name = {}
        self.SP4_name2id = {}
        self.SP4_edges = []
        self.SP4_reuse_id = []
        ## adjacency list
        self.SP4_adj_list = None
        self.SP4_merged_graph_edges = []
        self.SP4_merge_id = []
        self.SP4_table_info = {}
        self.tb_info = {}

        self.tbid2index = {}

    def get_node(self, node_name):
        return self.nodes.get(node_name, None)

    def add_node(self, node):
        self.nodes[node.name] = node

    def set_root(self, node):
        self.root = node

    def SP4_gen_real_graph_node_edges(self, h):
        SP4_nodes_by_name = list(sorted(self.nodes.values(),
                                    key=lambda node: node.name))

        ## record map of table name and table id 
        self.SP4_id2name = {}
        self.SP4_name2id = {}
        self.SP4_edges = []
        # set conditional tables to be represented as boxes
        n_id = 1
        for node in SP4_nodes_by_name:
            node.id = n_id
            if type(h.p4_nodes[node.name]) is p4_hlir.hlir.p4_tables.p4_table:
                if hasattr(h.p4_nodes[node.name], 'size'):
                    node.SP4_tb_depth = h.p4_tables[node.name].size
                node.SP4_tb_width = info.match_field_info(h.p4_tables[node.name])['total_field_width']
            self.SP4_id2name[n_id] = node.name
            self.SP4_name2id[node.name] = n_id
            # print 'id = ', node.id, 'name = ',node.name

            node_label = node.name
            n_id = n_id + 1

        for node in SP4_nodes_by_name:
            node_tos_by_name = sorted(list(node.edges.keys()),
                                      key=lambda node: node.name)
            for node_to in node_tos_by_name:
                self.SP4_edges.append((node.id, node_to.id))
                # print 'edge:', node.id, '->', node_to.id, node.name, '-->', node_to.name
                edge = node.edges[node_to]
                # print '------'
                # for each in list(node.edges.keys()):
                #     print each.name

    def SP4_get_table_info(self, h):
        self.SP4_table_info['P4_MATCH_LPM'] = []

        for each in self.SP4_name2id:
            if type(h.p4_nodes[each]) is p4_hlir.hlir.p4_tables.p4_conditional_node:                                     
                continue

            if len(h.p4_tables[each].match_fields) < 1:
                if 'no_match' in self.SP4_table_info:                
                    self.SP4_table_info['no_match'].append(each)
                else:
                    self.SP4_table_info['no_match'] = []
                    self.SP4_table_info['no_match'].append(each)
                continue

            match_type = h.p4_tables[each].match_fields[0][1]
            depth = self.nodes[each].SP4_tb_depth
            width = self.nodes[each].SP4_tb_width

            if str(match_type) in self.SP4_table_info:                
                self.SP4_table_info[str(match_type)].append((each, depth, width))
            else:
                self.SP4_table_info[str(match_type)] = []
                self.SP4_table_info[str(match_type)].append((each, depth, width))
            


    def SP4_get_table_info_summary(self, h):

        self.tb_info = {key: {} for key in self.SP4_table_info}
        for key in self.SP4_table_info:
            self.tb_info[key]['table_num'] = 0
            self.tb_info[key]['total_entries'] = 0
            self.tb_info[key]['total_resouce'] = 0

        for each in self.SP4_table_info:
            print each
            tb_num = 0
            total_depth = 0
            total_resouce = 0

            if each == 'no_match':
                for tb in self.SP4_table_info[each]:
                    # print tb
                    tb_num = tb_num + 1
                self.tb_info[each]['table_num'] = tb_num

            else:    
                for tbname, d, w in self.SP4_table_info[each]:
                    tb_num = tb_num + 1
                    total_depth = total_depth + d
                    total_resouce = total_resouce + d*w
                self.tb_info[each]['table_num'] = tb_num
                self.tb_info[each]['total_entries'] = total_depth
                self.tb_info[each]['total_resouce'] = total_resouce
        print '    Table info summary:', self.tb_info
        for key in self.SP4_table_info:
            print '    ', key, self.tb_info[key]['table_num'], \
                  self.tb_info[key]['total_entries'],\
                  self.tb_info[key]['total_resouce']



    def SP4_search_reuse_node(self, s_node, h_r, g_r):

        if type(s_node) is p4_hlir.hlir.p4_tables.p4_conditional_node:
            return -1
        
        if type(s_node) is p4_hlir.hlir.p4_tables.p4_table:
            # TODO: FIX the bug
            if len(s_node.match_fields) < 1:
                return -1
            s_match_type = s_node.match_fields[0][1]
            s_match_width = self.nodes[s_node.name].SP4_tb_width

            # print '   SP4-merge-001 snode,stype,width = ',s_node.name, s_match_type, s_match_width

            for r_node in g_r.nodes:
                if g_r.nodes[r_node].type_ == 0:
                    continue

                # TODO: FIX the bug
                # print '::zp::',type(h_r.p4_tables[r_node].match_fields[0])
                if len(h_r.p4_tables[r_node].match_fields) < 1:
                    # print '::bug-001::<2'
                    continue
                
                r_match_type = h_r.p4_tables[r_node].match_fields[0][1]

                if r_match_type != s_match_type:
                    continue

                r_match_width = g_r.nodes[r_node].SP4_tb_width
                if r_match_width != s_match_width:
                    continue

                reuse_id = g_r.SP4_name2id[r_node]
                if reuse_id in g_r.SP4_reuse_id:
                    continue
                print 'INFO|MERGE|SP4_search_reuse_node: snode,stype,width = ',s_node.name, s_match_type, s_match_width
                print 'INFO|MERGE|SP4_search_reuse_node: rnode,rtype,width = ',r_node, r_match_type, r_match_width
                print 'INFO|MERGE|SP4_search_reuse_node: reuse_id', reuse_id
                return reuse_id
                
        return -1

    def SP4_reduce_reuse_tables(self,h):
        '''reduce the resued tables from the current graph, calculate resource purpose.
        '''
        
        for each_id in self.SP4_merge_id:
            each = self.SP4_id2name[each_id]

            match_type = h.p4_tables[each].match_fields[0][1]
            depth = self.nodes[each].SP4_tb_depth
            width = self.nodes[each].SP4_tb_width

            self.tb_info[str(match_type)]['table_num'] = self.tb_info[str(match_type)]['table_num'] - 1
            self.tb_info[str(match_type)]['total_entries'] = self.tb_info[str(match_type)]['total_entries'] - depth
            self.tb_info[str(match_type)]['total_resouce'] = self.tb_info[str(match_type)]['total_resouce'] - depth*width

        DBG_print_table_summary = 0
        if DBG_print_table_summary:
            print '    AFTER MERGE::Table info summary:', self.tb_info
            print '    ', self.tb_info['P4_MATCH_TERNARY']['table_num'], \
                        self.tb_info['P4_MATCH_TERNARY']['total_entries'], \
                        self.tb_info['P4_MATCH_TERNARY']['total_resouce'], \
                        self.tb_info['P4_MATCH_EXACT']['table_num'], \
                        self.tb_info['P4_MATCH_EXACT']['total_entries'], \
                        self.tb_info['P4_MATCH_EXACT']['total_resouce'], \
                        self.tb_info['P4_MATCH_RANGE']['table_num'], \
                        self.tb_info['P4_MATCH_RANGE']['total_entries'], \
                        self.tb_info['P4_MATCH_RANGE']['total_resouce'], \
                        self.tb_info['P4_MATCH_VALID']['table_num'], \
                        self.tb_info['P4_MATCH_VALID']['total_entries'], \
                        self.tb_info['P4_MATCH_VALID']['total_resouce'], \
                        self.tb_info['P4_MATCH_LPM']['table_num'], \
                        self.tb_info['P4_MATCH_LPM']['total_entries'], \
                        self.tb_info['P4_MATCH_LPM']['total_resouce'], \
                        self.tb_info['no_match']['table_num']

    def SP4_gen_shadow_graph_node_edges(self, h_s, g_r, h_r):
        SP4_nodes_by_name = list(sorted(self.nodes.values(),
                                    key=lambda node: node.name))

        ## record map of table name and table id 
        self.SP4_id2name = {}
        self.SP4_name2id = {}
        self.SP4_edges = []

        # set conditional tables to be represented as boxes
        n_id = 1000
        for node in SP4_nodes_by_name:
            if type(h_s.p4_nodes[node.name]) is p4_hlir.hlir.p4_tables.p4_table:
                if hasattr(h_s.p4_nodes[node.name], 'size'):
                    node.SP4_tb_depth = h_s.p4_tables[node.name].size
                node.SP4_tb_width = info.match_field_info(h_s.p4_tables[node.name])['total_field_width']

            reuse_id = self.SP4_search_reuse_node(h_s.p4_nodes[node.name], h_r, g_r)
            # reuse_id = 0# g_r.SP4_name2id[reuse_node]
            if reuse_id > -1:
                node.id = reuse_id
                self.SP4_id2name[reuse_id] = node.name
                self.SP4_name2id[node.name] = reuse_id
                g_r.SP4_reuse_id.append(reuse_id)
            else:
                node.id = n_id
                self.SP4_id2name[n_id] = node.name
                self.SP4_name2id[node.name] = n_id
                
                node_label = node.name
                n_id = n_id + 1


        for node in SP4_nodes_by_name:
            node_tos_by_name = sorted(list(node.edges.keys()),
                                      key=lambda node: node.name)
            for node_to in node_tos_by_name:
                self.SP4_edges.append((node.id, node_to.id))
                # print 'edge:', node.id, '->', node_to.id, node.name, '-->', node_to.name
                edge = node.edges[node_to]
                # print '------'
                # for each in list(node.edges.keys()):
                #     print each.name

    def SP4_init_adj_list(self):
        # dbg info
        tmp_dbg = 0
        if tmp_dbg:                
            print ' sp4 merge: init adj list:'
            print self.SP4_id2name

        ## construct adj list
        self.SP4_adj_list = {key: [] for key in self.SP4_id2name}
        for u,v in self.SP4_edges:
            self.SP4_adj_list[u].append(v)

    def SP4_isReachable(self, s, d):
        # for test
        if d in self.SP4_adj_list[s]:
            return True
        else:
            return False

        # Mark all the vertices as not visited
        visited = {}
        for v in self.SP4_id2name:
            visited[v] = False
  
        # Create a queue for BFS
        queue=[]
        # Mark the source node as visited and enqueue it
        queue.append(s)
        visited[s] = True
  
        while queue:
            #Dequeue a vertex from queue 
            n = queue.pop(0)
             
            # If this adjacent node is the destination node,
            # then return true
            if n == d:
                return True
 
            #  Else, continue to do BFS
            for i in self.SP4_adj_list[n]:
                if visited[i] == False:
                    queue.append(i)
                    visited[i] = True
        # If BFS is complete without visited d
        return False

    def SP4_get_merged_graph(self, g_2):
        
        for u in self.SP4_reuse_id:
        
            for v in self.SP4_reuse_id:

                if v == u:
                    continue

                if self.SP4_isReachable(u, v) and g_2.SP4_isReachable(v, u):
                    if (u,v) in self.SP4_merged_graph_edges:
                        continue
                    self.SP4_merged_graph_edges.append((u,v))
                    
    def SP4_write_graph_to_file(self, gen_dir, filebase, g_2):

        filename_out = os.path.join(gen_dir, filebase + "_table_graph.csv")
        v_num = len(self.SP4_reuse_id)
        e_num = len(self.SP4_merged_graph_edges)

        for i in xrange(v_num):
            self.tbid2index[self.SP4_reuse_id[i]] = i + 1


        with open(filename_out, "w") as out:
            
            out.write('p edge '+str(v_num)+' '+str(e_num)+"\n")

            for v in self.SP4_reuse_id:
                name1 = self.SP4_id2name[v]
                depth1 = self.nodes[name1].SP4_tb_depth
                
                name2 = g_2.SP4_id2name[v]
                depth2 = g_2.nodes[name2].SP4_tb_depth

                w = max(depth1, depth2)
                ## TODO: fix it
                if w < 0:
                    w = 1
                out.write('n '+str(self.tbid2index[v])+ " " + str(w) + "\n")

            for u,v in self.SP4_merged_graph_edges:
                out.write('e '+str(self.tbid2index[u]) + " " + str(self.tbid2index[v]) + "\n")


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
        #
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
        #
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
                # print '------'
                # for each in list(node.edges.keys()):
                #     print each.name
                # pprint.pprint(vars(edge))
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


def printOrderedDict(obj):
    print 'DBG|INFO|OD:', obj.keys()
    cnt = 0
    for a, b in obj.items():
        print '     type:', type(b)
        print '      key:', a
        print '    value:', pprint(vars(b))
        cnt = cnt + 1
    print '    count = ', cnt

def print_table_names(p4_tables):
    print p4_tables.keys()

def merge_headers(h_mg, h_r, h_meta):
    print 'LOG|MERGE|p4_headers'
    h_mg.p4_headers.update(h_r.p4_headers)
    h_mg.p4_headers.update(h_meta.p4_headers)


def merge_header_instances(h_mg, h_r, h_meta):
    print 'LOG|MERGE|p4_header instances'
    h_mg.p4_header_instances.update(h_r.p4_header_instances)
    h_mg.p4_header_instances.update(h_meta.p4_header_instances)


# for both AB and Diff merging
def merge_header_actions(h_mg, h_r, h_meta):
    ## TODO-low: reduce the duplicated actions 
    print 'LOG|MERGE|actions'
    h_mg.p4_actions.update(h_r.p4_actions)
    h_mg.p4_actions.update(h_meta.p4_actions)

def AB_merge_p4_tables(h_mg, h_r, h_meta):
    print 'LOG|MERGE|8 p4 tables:'
    print 'LOG|MERGE|  Shadow  tables:', h_mg.p4_tables.keys()
    print 'LOG|MERGE|  Product tables:', h_r.p4_tables.keys()

    h_mg.p4_tables.update(h_r.p4_tables)
    h_mg.p4_tables.update(h_meta.p4_tables)
    print 'LOG|MERGE|  Merged  tables', h_mg.p4_tables.keys()

    assert(len(h_mg.p4_ingress_ptr) == 1)
    ingress_ptr_s = h_mg.p4_ingress_ptr.keys()[0]
    ingress_ptr_r = h_r.p4_ingress_ptr.keys()[0]
    print '    DBG in-/egress_ptr_r:', ingress_ptr_r.name, h_r.p4_egress_ptr
    print '    DBG in-/egress_ptr_s:', ingress_ptr_s.name, h_mg.p4_egress_ptr
    # pprint( vars( h_meta.p4_tables['shadow_traffic_control'] ))
    for e in h_mg.p4_tables["shadow_traffic_control"].next_:
        if e.name == 'SP4_add_shadow_tag' or e.name == 'goto_testing_pipe':
            h_mg.p4_tables["shadow_traffic_control"].next_[e] = h_mg.p4_nodes[ingress_ptr_s.name]    
        if e.name == 'SP4_remove_shadow_tag' or e.name == 'goto_production_pipe':
            h_mg.p4_tables["shadow_traffic_control"].next_[e] = h_mg.p4_nodes[ingress_ptr_r.name]
        print 'LOG|MERGE|add STC nexts:', h_mg.p4_tables["shadow_traffic_control"].next_[e]
        pass

    # TODO: remove the duplicate nodes in set
    # key = h_mg.p4_ingress_ptr.keys()[0]
    ingress_ptr_key   = h_mg.p4_tables['shadow_traffic_control']
    ingress_ptr_value = h_mg.p4_ingress_ptr[ingress_ptr_s].union(h_r.p4_ingress_ptr[ingress_ptr_r])
    h_mg.p4_ingress_ptr.clear()
    h_mg.p4_ingress_ptr[ingress_ptr_key] = ingress_ptr_value

def set_parser_default_table_STC(p4_parse_states, h_mg):

    for _, parser_state in p4_parse_states.items():
        print 'DBG|SP4_merge|new parser names:', parser_state.name
        for branch_case, next_state in parser_state.branch_to.items():
            if branch_case == p4_hlir.hlir.p4_parser.P4_DEFAULT:
                if isinstance(next_state, p4_hlir.hlir.p4_tables.p4_conditional_node) or \
                   isinstance(next_state, p4_hlir.hlir.p4_tables.p4_table):
                    # TODO: check it
                    new_branch = "P4_DEFAULT", h_mg.p4_tables['shadow_traffic_control']
                    parser_state.branch_to[branch_case] = h_mg.p4_tables['shadow_traffic_control']


def rename_parser_states(p4_parse_states, h_mg):
    '''
    Add preffix 'shadow_' to the name of all parser states;
    also update the default branch to table to 'shadow_traffic_control'
    '''
    start_states = p4_parse_states['start']

    accessible_parse_states = set()
    accessible_parse_states_ordered_name = []
    new_parser_name = {}

    def find_accessible_parse_states(parse_state):
        if parse_state in accessible_parse_states:
            return
        accessible_parse_states.add(parse_state)
        accessible_parse_states_ordered_name.append(parse_state.name)
        for _, next_state in parse_state.branch_to.items():
            if isinstance(next_state, p4_hlir.hlir.p4.p4_parse_state):
                find_accessible_parse_states(next_state)
    
    find_accessible_parse_states(start_states)
    print '    DBG|SP4_merge|parser names:', accessible_parse_states_ordered_name
    
    ## 01 rename all the parser state's name
    for parser_name in accessible_parse_states_ordered_name:
        if parser_name == 'start':
            continue
        new_parser_name[parser_name] = 'shadow_' + parser_name
        p4_parse_states[new_parser_name[parser_name]] = p4_parse_states.pop(parser_name)
        p4_parse_states[new_parser_name[parser_name]].name = new_parser_name[parser_name]

    ## 02 modify all the default tables which the parser branch to
    set_parser_default_table_STC(p4_parse_states, h_mg)


    return
    ## todo: check the return_statement
    for _, parser_state in p4_parse_states.items():
        return_type = parser_state.return_statement[0]
        print 'return_type = ', return_type, type(parser_state.return_statement)
        if return_type == "immediate":   
            state = parser_state.return_statement[1]
            if state in accessible_parse_states_ordered_name:
                del parser_state.return_statement
                parser_state.return_statement = ('immediate', new_parser_name[state])
                print 'DBG|004 parser_state.return_statement=', parser_state.return_statement
        elif return_type == "select":
            select_fields = parser_state.return_statement[1]
            select_cases = parser_state.return_statement[2] # a list of cases
            print 'DBG|005: select fields', select_fields
            print 'DBG|006: select cases', select_cases, type(select_cases)

            old_case_list = []
            new_case_list = []

            for case in select_cases:
                print 'DBG|007: case', case, type(case)
                value_list = case[0]
                if case[1] in accessible_parse_states_ordered_name:
                    print 'DBG|SP4_merge|parser rename select:', case[1]
                    old_case_list.append(case)
                    new_case = case[0], new_parser_name[case[1]]
                    new_case_list.append(new_case)
                else:
                    print 'DBG|SP4_merge|parser rename sekect err:', case[1]

            for case in old_case_list:
                select_cases.remove(case)
            for case in new_case_list:
                select_cases.append(case)

            print 'DBG|007: select cases', select_cases, type(select_cases)

    
def merge_parser_states(h_mg, h_r, h_meta):

    ## 01 check the two P4 program start from the same parser state
    if 'start' not in h_mg.p4_parse_states.keys() or \
       'parse_ethernet' not in h_mg.p4_parse_states.keys():
        print 'ERR|p4c_bm|SP4_merge: missing parse_ethernet in shadow P4 program'
        raise(False)
    if 'start' not in h_r.p4_parse_states.keys() or \
       'parse_ethernet' not in h_mg.p4_parse_states.keys():
        print 'ERR|p4c_bm|SP4_merge: missing parse_ethernet in real P4 program'
        raise(False)        

    ## 02 modify name of tables in shadow parser states: add '_shadow' suffix
    ## todo(low-priority): check if there are repeated parser state name
    rename_parser_states(h_mg.p4_parse_states, h_mg)

    ## 03 add meta parser state
    h_mg.p4_parse_states['parse_shadow_tag'] = h_meta.p4_parse_states['parse_shadow_tag']
    
    # copy parse_eth's branch_to to parse_shadow_tag
    parse_state_eth = h_mg.p4_parse_states['shadow_parse_ethernet']
    eth_branch_to = parse_state_eth.branch_to
    h_mg.p4_parse_states['parse_shadow_tag'].branch_to.clear()
    h_mg.p4_parse_states['parse_shadow_tag'].branch_to.update(eth_branch_to)

    # clear parse_eth's branch_to then add shadow tag state(0x8100)
    parse_state_eth.branch_to.clear()
    branch_case = 0x8100
    next_state = h_mg.p4_parse_states['parse_shadow_tag']
    parse_state_eth.branch_to[branch_case] = next_state

    branch_case_default = p4_hlir.hlir.p4_parser.P4_DEFAULT
    next_state_default = h_mg.p4_tables['shadow_traffic_control']
    parse_state_eth.branch_to[branch_case_default] = next_state_default

    # fix the call sequence of parse_shadow_tag 
    # TO improve 
    parse_state = h_mg.p4_parse_states['parse_shadow_tag']
    op_type = p4_hlir.hlir.p4_parser.parse_call.extract
    op_header = h_mg.p4_header_instances['shadow_tag']
    call = op_type, op_header
    parse_state.call_sequence = []
    parse_state.call_sequence.append(call)

    ## 04 add real parser states in, used shadow_start as the merged start state
    set_parser_default_table_STC(h_r.p4_parse_states, h_mg)
    for parser_name, parser_state in h_r.p4_parse_states.items():
        OPT_PRINT_NEW_PARSER = 0
        if OPT_PRINT_NEW_PARSER:
            print '    OPT_PRINT_NEW_PARSER|:'
            print pprint(vars(parser_state))
        if parser_name == 'start':
            continue
        elif parser_name == 'parse_ethernet':
            print "    pass parser state parse_ethernet"
            r_eth_branch_to = parser_state.branch_to
            h_mg.p4_parse_states['shadow_parse_ethernet'].branch_to.update(r_eth_branch_to)
            print r_eth_branch_to
            continue
        h_mg.p4_parse_states[parser_name] = parser_state
    

    OPT_PRINT_MERGED_PARSER = 0
    if OPT_PRINT_MERGED_PARSER:
        print '\n\n\nDBG|merge parser|print merged parser|:'
        printOrderedDict(h_mg.p4_parse_states)

def SP4_AB_merge_p4_objects(p4_v1_1, h_r, h_s, h_meta):
    ### The following is the merged HLIR

  ## 1. init hlir
    if p4_v1_1:
        from p4_hlir_v1_1.main import HLIR
        primitives_res = 'primitives_v1_1.json'
    else:
        from p4_hlir.main import HLIR
        primitives_res = 'primitives.json'
    h_mg = HLIR()

  ## 2. add objects of shadow program
    h_mg.p4_actions.update(h_s.p4_actions)       
    h_mg.p4_control_flows.update(h_s.p4_control_flows)
    h_mg.p4_headers.update(h_s.p4_headers )
    h_mg.p4_header_instances.update(h_s.p4_header_instances )
    h_mg.p4_fields.update(h_s.p4_fields )
    h_mg.p4_field_lists.update(h_s.p4_field_lists )
    h_mg.p4_field_list_calculations.update(h_s.p4_field_list_calculations )
    h_mg.p4_parser_exceptions.update(h_s.p4_parser_exceptions )
    h_mg.p4_parse_value_sets.update(h_s.p4_parse_value_sets)
    h_mg.p4_parse_states.update(h_s.p4_parse_states )
    h_mg.p4_counters.update(h_s.p4_counters)
    h_mg.p4_meters.update(h_s.p4_meters)
    h_mg.p4_registers.update(h_s.p4_registers )
    h_mg.p4_nodes.update(h_s.p4_nodes )
    h_mg.p4_tables.update(h_s.p4_tables )
    h_mg.p4_action_profiles.update(h_s.p4_action_profiles  )
    h_mg.p4_action_selectors.update(h_s.p4_action_selectors )
    h_mg.p4_conditional_nodes.update(h_s.p4_conditional_nodes)

    h_mg.calculated_fields = h_s.calculated_fields

    h_mg.p4_ingress_ptr = h_s.p4_ingress_ptr
    h_mg.p4_egress_ptr = h_s.p4_egress_ptr


  ## 3. Merging each object of real program and h_meta
    ## TODO(low-priority): seperate each merge to single function 

    ### 3.X1 merge p4 fields
    '''All the header and metadata fields'''
    print 'LOG|MERGE|X1 p4 feilds:'
    h_mg.p4_fields.update(h_r.p4_fields)
    h_mg.p4_fields.update(h_meta.p4_fields)

    # 3.X2 merge p4 nodes
    print 'LOG|MERGE|X2 p4 nodes:'
    h_mg.p4_nodes.update(h_r.p4_nodes)
    h_mg.p4_nodes.update(h_meta.p4_nodes)

    # 3.X3 merge conditional nodes
    print 'LOG|MERGE|X3 p4_conditional_nodes:'
    h_mg.p4_conditional_nodes.update(h_r.p4_conditional_nodes)
    h_mg.p4_conditional_nodes.update(h_meta.p4_conditional_nodes)


    # 3.X4 merge calculated fields
    print 'LOG|MERGE|X4 calculated_fields'
    h_mg.calculated_fields.extend(h_meta.calculated_fields)
    h_mg.calculated_fields.extend(h_r.calculated_fields)
    print '            |Merged:', h_mg.calculated_fields

    # 3.X5 merge ingress ptr: moved to tables merging

    # 3.X6 merge egress ptr
    # ZP : this ptr should be the goto table of ShadowP4
    #      used to identify weather the traffic is of real or shadow
    print 'LOG|MERGE| X5 p4_egress_ptr'
    print h_mg.p4_egress_ptr
    print h_r.p4_egress_ptr


    ### 3.1 merge headers
    merge_headers(h_mg, h_r, h_meta)

    ### 3.2 merge header instances
    merge_header_instances(h_mg, h_r, h_meta)

    # 3.3 merge fields lists
    print 'LOG|MERGE|3 p4 feilds lists:'
    # ZP: this contains only one: ipv4_checksum_list
    h_mg.p4_field_lists.update(h_r.p4_field_lists)

    # 3.4 merge fields lists calculations
    print 'LOG|MERGE|4 p4_field_list_calculations:'
    h_mg.p4_field_list_calculations.update(h_r.p4_field_list_calculations)


    ### 3.5 merge action 
    merge_header_actions(h_mg, h_r, h_meta)

    # 3.6 merge p4 action selectors
    # ZP: null
    print 'LOG|MERGE|6 p4_action_selectors:'
    h_mg.p4_action_selectors.update(h_r.p4_action_selectors)

    # 3.7 merge action profiles
    print 'LOG|MERGE|7 action profiles:'
    # ZP: null
    h_mg.p4_action_profiles.update(h_mg.p4_action_profiles)


    # 3.8 merge p4 tables
    AB_merge_p4_tables(h_mg, h_r, h_meta)


    # 3.9 merge counters
    print 'LOG|MERGE|9 counters'
    h_mg.p4_counters.update(h_r.p4_counters)

    # 3.10 merge meter
    print 'LOG|MERGE|10 meters'
    h_mg.p4_meters.update(h_r.p4_meters)


    # 3.11 merge register
    print 'LOG|MERGE|11 register'
    h_mg.p4_registers.update(h_r.p4_registers)


    ### 3.12 merge control flows
    print 'LOG|MERGE|12 control flows'
    # TODO: double-check here: nothing to do
    print '    shadow control flow:', type(h_mg.p4_control_flows['egress'])
    pprint(vars(h_mg.p4_control_flows['ingress']))
    pprint(vars(h_mg.p4_control_flows['egress']))


    # 3.13 merge parse value sets
    # ZP: null
    print 'LOG|MERGE|13 p4_parse_value_sets:'
    h_mg.p4_parse_value_sets.update(h_r.p4_parse_value_sets)


    # 3.14 merge parse states
    print 'LOG|MERGE|14 p4_parse_states:'
    merge_parser_states(h_mg, h_r, h_meta)

    # 3.15 merge parser exceptions
    # ZP: null
    print 'LOG|MERGE|15 parser exceptions:'
    h_mg.p4_parser_exceptions.update(h_r.p4_parser_exceptions)

    return h_mg




#---------------------------------------------------------#
#---------------------- diff testing ---------------------#
#---------------------------------------------------------#

def DF_set_nodes_with_next_none(entry, visited, next_set_state):
    visited.add(entry)
    for e in entry.next_:
        if entry.next_[e] == None:
            entry.next_[e] = next_set_state
        elif type(entry.next_[e]) is p4_hlir.hlir.p4_tables.p4_table:
            if not entry.next_[e] in visited:
                DF_set_nodes_with_next_none(entry.next_[e], visited, next_set_state)
            pass
        elif type(entry.next_[e]) is p4_hlir.hlir.p4_tables.p4_conditional_node:
            if not entry.next_[e] in visited:
                DF_set_nodes_with_next_none(entry.next_[e], visited, next_set_state)
            pass
    return

def DF_merge_p4_tables(h_mg, h_r, h_s, h_meta):
    print 'LOG|MERGE|8 p4 tables:'
    print 'LOG|MERGE|  Shadow  tables:', h_s.p4_tables.keys()
    print 'LOG|MERGE|  Product tables:', h_r.p4_tables.keys()
    print 'LOG|MERGE|  Metadata tables:', h_meta.p4_tables.keys()

    h_mg.p4_tables.update(h_r.p4_tables)
    h_mg.p4_tables.update(h_meta.p4_tables)

    print 'LOG|MERGE|  Merged  tables', h_mg.p4_tables.keys()
    print 'LOG|MERGE|  Merged  conditions', h_mg.p4_conditional_nodes.keys()
    print 'LOG|MERGE|  Merged  conditions', printOrderedDict( h_mg.p4_conditional_nodes)
    print 'LOG|MERGE|  Merged  nodes', h_mg.p4_nodes.keys()

    assert(len(h_mg.p4_ingress_ptr) == 1)
    ingress_ptr_s = h_s.p4_ingress_ptr.keys()[0]
    ingress_ptr_r = h_r.p4_ingress_ptr.keys()[0]
    ingress_ptr_mg = h_mg.p4_ingress_ptr.keys()[0]
    
    print '    DBG in-/egress_ptr_r:', ingress_ptr_r.name, h_r.p4_egress_ptr
    print '    DBG in-/egress_ptr_s:', ingress_ptr_s.name, h_s.p4_egress_ptr
    print '    DBG in-/egress_ptr_m:', ingress_ptr_mg.name, h_mg.p4_egress_ptr

    # insert testing ingress pipeline
    print 'LOG|MERGE|8.1  Metadata conditions:', printOrderedDict(h_meta.p4_conditional_nodes)
    visited = set()
    DF_set_nodes_with_next_none(ingress_ptr_s, visited, h_mg.p4_nodes["record_shadow_result"])
    h_mg.p4_conditional_nodes["_condition_0"].next_[False] = h_mg.p4_nodes[ingress_ptr_s.name]

    # insert production ingress pipeline
    print 'LOG|MERGE|8.2  Metadata conditions:', printOrderedDict(h_r.p4_nodes)
    visited = set()
    DF_set_nodes_with_next_none(ingress_ptr_r, visited, h_mg.p4_nodes["_condition_1"])
    h_mg.p4_conditional_nodes["_condition_0"].next_[True] = h_mg.p4_nodes[ingress_ptr_r.name]

    # set shadow traffic control branch
    for e in h_mg.p4_tables["shadow_traffic_control"].next_:
        if e.name == 'SP4_remove_shadow_tag' or e.name == 'goto_production_pipe':
            h_mg.p4_tables["shadow_traffic_control"].next_[e] = h_mg.p4_nodes[ingress_ptr_r.name]
        print 'LOG|MERGE|add STC nexts:', h_mg.p4_tables["shadow_traffic_control"].next_[e]
        pass

    ## egress merge
    egress_ptr_mg = h_mg.p4_egress_ptr

    egress_ptr_mg.next_[True] = h_s.p4_egress_ptr
    egress_ptr_mg.next_[False] = h_r.p4_egress_ptr
    
    return


def SP4_DF_merge_p4_objects(p4_v1_1, h_r, h_s, h_meta):
    ### The following is the merged HLIR

  ## 1. init merged hlir
    if p4_v1_1:
        from p4_hlir_v1_1.main import HLIR
        primitives_res = 'primitives_v1_1.json'
    else:
        from p4_hlir.main import HLIR
        primitives_res = 'primitives.json'
    h_mg = HLIR()

  ## 2. add objects of shadow program
    h_mg.p4_actions.update(h_s.p4_actions)       
    h_mg.p4_control_flows.update(h_s.p4_control_flows)
    h_mg.p4_headers.update(h_s.p4_headers )
    h_mg.p4_header_instances.update(h_s.p4_header_instances )
    h_mg.p4_fields.update(h_s.p4_fields )
    h_mg.p4_field_lists.update(h_s.p4_field_lists )
    h_mg.p4_field_list_calculations.update(h_s.p4_field_list_calculations )
    h_mg.p4_parser_exceptions.update(h_s.p4_parser_exceptions )
    h_mg.p4_parse_value_sets.update(h_s.p4_parse_value_sets)
    h_mg.p4_parse_states.update(h_s.p4_parse_states )
    h_mg.p4_counters.update(h_s.p4_counters)
    h_mg.p4_meters.update(h_s.p4_meters)
    h_mg.p4_registers.update(h_s.p4_registers )
    h_mg.p4_nodes.update(h_s.p4_nodes )
    h_mg.p4_tables.update(h_s.p4_tables )
    h_mg.p4_action_profiles.update(h_s.p4_action_profiles  )
    h_mg.p4_action_selectors.update(h_s.p4_action_selectors )
    h_mg.p4_conditional_nodes.update(h_s.p4_conditional_nodes)

    h_mg.calculated_fields = h_s.calculated_fields

    h_mg.p4_ingress_ptr = h_meta.p4_ingress_ptr
    h_mg.p4_egress_ptr = h_meta.p4_egress_ptr


  ## 3. Merging each object of real program and h_meta
    ## TODO(low-priority): separate each merge to single function 

    ### 3.X1 merge p4 fields
    '''All the header and metadata fields'''
    # ZP: 5 fields added in the test case:
    # : ingress_metadata_SP4.test_packet_generate_rate
    # : ingress_metadata_SP4.real_packet_cnt_flag
    # : ingress_metadata_SP4.shadow_pkt_flag
    # : ingress_metadata_SP4._padding
    # : ipv4.flags_SP4 ipv4.flags_SP4
    print 'LOG|MERGE|X1 p4 fields:'
    h_mg.p4_fields.update(h_r.p4_fields)
    h_mg.p4_fields.update(h_meta.p4_fields)

    # 3.X2 merge p4 nodes
    print 'LOG|MERGE|X2 p4 nodes:'
    print 'LOG|MERGE|  Shadow nodes:', h_s.p4_nodes.keys()
    print 'LOG|MERGE|  Product nodes:', h_r.p4_nodes.keys()
    print 'LOG|MERGE|  Metadata nodes:', h_meta.p4_nodes.keys()

    h_mg.p4_nodes.update(h_r.p4_nodes)
    h_mg.p4_nodes.update(h_meta.p4_nodes)
    print 'LOG|MERGE|  Merged nodes:', h_mg.p4_nodes.keys()

    # 3.X3 merge conditional nodes
    print 'LOG|MERGE|X3 p4_conditional_nodes:'
    h_mg.p4_conditional_nodes.update(h_r.p4_conditional_nodes)
    h_mg.p4_conditional_nodes.update(h_meta.p4_conditional_nodes)

    # 3.X4 merge calculated fields
    print 'LOG|MERGE|X4 calculated_fields'
    h_mg.calculated_fields.extend(h_meta.calculated_fields)
    h_mg.calculated_fields.extend(h_r.calculated_fields)
    print '            |Merged:', h_mg.calculated_fields

    # 3.X5 merge ingress ptr: moved to tables merging

    # 3.X6 merge egress ptr done
    # ZP : this ptr should be the goto table of ShadowP4
    #      used to identify weather the traffic is of real or shadow
    print 'LOG|MERGE| X5 p4_egress_ptr'
    print h_mg.p4_egress_ptr
    print h_r.p4_egress_ptr


    ### 3.1 merge headers
    merge_headers(h_mg, h_r, h_meta)

    ### 3.2 merge header instances
    merge_header_instances(h_mg, h_r, h_meta)

    # 3.3 merge fields lists
    print 'LOG|MERGE|3 p4 fields lists:'
    # ZP: this contains only one: ipv4_checksum_list
    h_mg.p4_field_lists.update(h_r.p4_field_lists)

    # 3.4 merge fields lists calculations
    print 'LOG|MERGE|4 p4_field_list_calculations:'
    h_mg.p4_field_list_calculations.update(h_r.p4_field_list_calculations)


    ### 3.5 merge action 
    merge_header_actions(h_mg, h_r, h_meta)

    # 3.6 merge p4 action selectors
    # ZP: null
    print 'LOG|MERGE|6 p4_action_selectors:'
    h_mg.p4_action_selectors.update(h_r.p4_action_selectors)

    # 3.7 merge action profiles
    print 'LOG|MERGE|7 action profiles:'
    # ZP: null
    h_mg.p4_action_profiles.update(h_mg.p4_action_profiles)


    # 3.8 merge p4 tables
    DF_merge_p4_tables(h_mg, h_r, h_s, h_meta)


    # 3.9 merge counters-
    print 'LOG|MERGE|9 counters'
    h_mg.p4_counters.update(h_r.p4_counters)

    # 3.10 merge meter
    print 'LOG|MERGE|10 meters'
    h_mg.p4_meters.update(h_r.p4_meters)

    # 3.11 merge register
    print 'LOG|MERGE|11 register'
    h_mg.p4_registers.update(h_r.p4_registers)


    ### 3.12 merge control flows
    print 'LOG|MERGE|12 control flows'
    # TODO: double-check here: nothing to do
    print '    shadow control flow:', type(h_mg.p4_control_flows['egress'])
    pprint(vars(h_mg.p4_control_flows['ingress']))
    pprint(vars(h_mg.p4_control_flows['egress']))


    # 3.13 merge parse value sets
    # ZP: null
    print 'LOG|MERGE|13 p4_parse_value_sets:'
    h_mg.p4_parse_value_sets.update(h_r.p4_parse_value_sets)


    # 3.14 merge parse states
    print 'LOG|MERGE|14 p4_parse_states:'
    merge_parser_states(h_mg, h_r, h_meta)

    # 3.15 merge parser exceptions
    # ZP: null
    print 'LOG|MERGE|15 parser exceptions:'
    h_mg.p4_parser_exceptions.update(h_r.p4_parser_exceptions)

    return h_mg


class SP4_graph_nodes_edges(object):
    """docstring for SP4_get_graph_node_edges"""
    def __init__(self, arg):
        super(SP4_get_graph_node_edges, self).__init__()
        self.arg = arg
        
def SP4_get_graph_node_edges(graph):
    h_ingress_nodes_by_name = list(sorted(graph.nodes.values(),
                                key=lambda node: node.name))

    ## record map of table name and table id 
    h_ingress_id2name = {}
    h_ingress_ids = []
    h_ingress_edges = []
    # set conditional tables to be represented as boxes
    n_id = 1
    for node in h_ingress_nodes_by_name:
        node.id = n_id
        h_ingress_ids.append(n_id)
        h_ingress_id2name[node.name] = n_id
        print 'id = ', node.id, 'name = ',node.name

        node_label = node.name
        n_id = n_id + 1

    for node in h_ingress_nodes_by_name:
        node_tos_by_name = sorted(list(node.edges.keys()),
                                  key=lambda node: node.name)
        for node_to in node_tos_by_name:
            h_ingress_edges.append((node.id, node_to.id))
            print 'edge:', node.id, '->', node_to.id, node.name, '-->', node_to.name
            edge = node.edges[node_to]
            print '------'
            for each in list(node.edges.keys()):
                print each.name




# graph = dependency_graph.build_table_graph_ingress()
def generate_dot(graph, out = sys.stdout,
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
    out.write("digraph " + graph.name + " {\n")

    # The uses of the 'sorted' function below are not necessary
    # for correct behavior, but are done to try to make the
    # contents of the dot output file in a more consistent order
    # from one run of this program to the next.  By default,
    # Python dicts and sets can have their iteration order change
    # from one run of a program to the next because the hash
    # function changes from one run to the next.
    nodes_by_name = list(sorted(graph.nodes.values(),
                                key=lambda node: node.name))

    
    # set conditional tables to be represented as boxes
    # (i) get all the nodes
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
    
    # (ii) get all the edges
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



