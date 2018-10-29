/*
 *  Created on: 14/09/2015 by Bruno
 *     A framework for the independent set problem
 * 
 *  Modified on: 08/09/2017 by Peng
 *     Add implementation of simulated annealing and naive greedy algorithm
 *     Add implementation of Bron-Kerbosch algorithm
 */

#include "Graph.h"
#include "ArgPack.h"
#include "InitError.h"
#include "Solution.h"
#include "bossa_timer.h"

#include <fstream>
#include <iostream>
#include <random>
#include <string>
#include <cstring>

using namespace std;
using namespace opt;

namespace opt
{

// Mersenne Twister 19937 generator
mt19937 generator;


/************************************************************
 *
 * Creates a graph based on the given specification. Returns
 * a pointer to the allocated graph; the graph must be 
 * deallocated elsewhere.
 *
 ************************************************************/

Graph *readInstance (const string &filename, bool complement)
{
	int m = -1; // number of vertices and edges announced
	int m_count = 0; // number of edges actually counted
	int linenum = 0; // number of read lines
	char buffer[256];
	ifstream input(filename.c_str());
	Graph *graph = NULL;
	int n_num = 0;
	int e_num = 0;

	if (!input) {
		throw InitError("error opening the input file: " + filename + "\n");
	}


	while (input.getline(buffer, 256)) {
		linenum++;

		int v1, v2;

		if (linenum == 1) {
			if (sscanf(buffer, "p edge %d %d", &n_num, &e_num) != 2) {
				input.close();
				throw InitError("syntax error in line " + std::to_string(linenum) + "\n");
			}
		}
		else if (linenum <= (n_num + 1) ) {
			if (sscanf(buffer, "n %d %d", &v1, &v2) != 2) {
				input.close();
				throw InitError("syntax error in line " + std::to_string(linenum) + "\n");
			}
		}
		else if (linenum <= (n_num + e_num + 1) ) {
			if (sscanf(buffer, "e %d %d", &v1, &v2) != 2) {
				input.close();
				throw InitError("syntax error in line " + std::to_string(linenum) + "\n");
			}
		}

		if (linenum == 1) { // read the number of vertices and edges
			if (n_num < 0 || e_num < 0) {
				input.close();
				throw InitError("syntax error in line " + std::to_string(linenum) +
				                ". The number of edges and vertices must not be negative.\n");
			}
			m = e_num;
			graph = new Graph(n_num, e_num);
			if (complement) {
				for (int idx1 = 0; idx1 < n_num; idx1++) {
					for (int idx2 = idx1 + 1; idx2 < n_num; idx2++) {
						graph->addEdge(idx1, idx2);
					}
				}
			}
		}
		else if (linenum <= (n_num+1) ) { // read the vertex
			graph->setWeight(v1-1, v2);
		}
		else if (linenum <= (n_num+e_num+1) ) { // read an edge
			if (v1 < 0 || v2 < 0) {
				input.close();
				throw InitError("syntax error in line " + std::to_string(linenum) +
				                ". Vertices label must not be negative.\n");
			}
			if (!complement) {
				graph->addEdge(v1 - 1, v2 - 1);
			} else {
				graph->removeEdge(v1 - 1, v2 - 1);
			}
			m_count++;
		}
	}

	input.close();

	if (m_count != m) {
		printf("m_count = %d, m = %d \n", m_count, m);
		throw InitError("the number of edges announced is not equal to the number of edges read.\n");
	}

	return graph;
} // Graph *readInstance (const string &filename)

} // namespace opt

void intersection(std::vector<int> *va,
				  const std::vector<int> *vb,
				  std::vector<int> *res) {
	for (int i : *va) {
		for (int j : *vb) {
			if (i == j)
			{
				res->push_back(j);
			}
		}
	}
	return;
}



// DBG flags
int flag1 = 0;


void BronKerbosch(Graph *graph,
				  int* best_weight,
				  std::vector<int> *best_set,
				  std::vector<int> R,
				  std::vector<int> P,
				  std::vector<int> X) 
{

	if (P.empty() && X.empty()) {
		int cur_weight = 0;
		for (int vi : R) {
			cur_weight += graph->weight(vi);
		}

		if (cur_weight > *best_weight) { 
			best_set->clear();
			for(int each : R) {
				best_set->push_back(each);
			}
			*best_weight = cur_weight;
		}

		return;
	}

	std::vector<int> P_new(P);
	for(int n : P_new) {

		int cur_weight = 0;
		for (int vi : R) {
			cur_weight += graph->weight(vi);

			//DBG
			if (flag1 == 10) {
				cout << "==== n:" << n <<endl;
				cout << "graph->n():" << graph->n() <<endl;
				for (int i = 0; i < graph->n(); ++i)
				{
					cout << i <<':' <<graph->weight(i) << '|';
				}
				cout <<endl;
				flag1 = 1;
			}

		}

		if (cur_weight >= *best_weight) { 
			best_set->clear();
			for(int each : R) {
				best_set->push_back(each);
			}
			*best_weight = cur_weight;
			if (cur_weight > 80)
			{
				cout << " BEST{";
				for(int i:*best_set) cout << i <<",";
				cout << "}=" << *best_weight << endl ;
		}
		}

		std::vector<int> R2(R);
		std::vector<int> P2={};
		std::vector<int> X2={};
		std::vector<int> neighber_n;

		R2.push_back(n);
		intersection(&P, &(graph->adj_l(n)), &P2);
		intersection(&X, &(graph->adj_l(n)), &X2);

		BronKerbosch(graph, best_weight, best_set, R2, P2, X2);
		
		for (auto it = P.begin(); it != P.end(); ) {
			if (*it == n) {
				P.erase(it);
			} else {
				++it;
			}
		}
		X.push_back(n);
	}

	return;
}

#define MAX_PARA 1000000
int main(int argc, char *argv[])
{
	try {

		BossaTimer input_timer, proc_timer;
		double target_time = -1;
		int target_iterations = -1;
		input_timer.start();

		// read input parameters
		ArgPack single_ap(argc, argv);

		// set the random seed
		generator.seed(ArgPack::ap().rand_seed);

		// read instance
		Graph *graph_instance = readInstance(ArgPack::ap().input_name, ArgPack::ap().complement);
		input_timer.pause();

		proc_timer.start();
		graph_instance->sort();

		Solution s(graph_instance);
	
	// naive greedy algorithm
		if (ArgPack::ap().naive_greedy) {
			cout << "Running naive greedy algorithm." << endl;
			// greedy strategy: each time we chose the nodes with lowest degree
			while (!s.isMaximal()) {
				s.addVertexDegreeLowest();
				assert(s.integrityCheck());
			}

			Solution best_s(s);

			cout << "- best weight: " << best_s.weight() <<endl;
			cout << "- size: " << best_s.size() << "\n";
			cout << "- solution: ";
			for(int v : best_s.i_set()) {
				cout << v << " ";
			}
			cout << endl;
			// we add a fixed compiler merging time to the merging algorithm
			// It is about 0.1 seconds in average when turn off all the logs and DBGs
			// In this way we can compare the algorithm time more clearly
			double fixed_compiler_merge_time = 0.1;
			cout << "- total processing time (s): " << proc_timer.getTime() + fixed_compiler_merge_time << "\n\n\n";
				
			return 0;
		}

	// Bron-Kerbosch algorithm
		if (ArgPack::ap().bronkerbosch) {
			cout << "Running Bron-Kerbosch optimal algorithm." << endl;

			std::vector<int> R = {};
			std::vector<int> P = {};
			std::vector<int> X = {};

			std::vector<int> best_set = {};
			int best_weight = 0;

			int v_num = graph_instance->n();
			for (int i = 0; i < v_num; ++i) {
				P.push_back(i);
			}

			BronKerbosch(graph_instance, &best_weight, &best_set, R, P, X);

			cout << "- best weight: " << best_weight <<"\n";
			cout << "- size: " << best_set.size() << "\n";
			cout << "- solution: ";
			for(int v : best_set) {
				cout << v << " ";
			} 
			// we add a fixed compiler merging time to the merging algorithm
			// It is about 0.1 seconds in average when turn off all the logs and DBGs
			// In this way we can compare the algorithm time more clearly
			double fixed_compiler_merge_time = 0.1;
			cout << "\n- total processing time (s): " << proc_timer.getTime() + fixed_compiler_merge_time << "\n\n\n";
			// cout << "End of BronKerbosch.\n";
			return 0;
		} // BK

		// initialize a solution: we can do either randomly or greedy 
		cout << "Running simulated annealing algorithm." << endl;
		while (!s.isMaximal()) {
			// s.addRandomVertex();
			s.addVertexDegreeLowest();
			assert(s.integrityCheck());
		}

		Solution best_s(s);

	// run simulated annealing iterations

		int k = 1;
		int local_best = s.weight();
		int iter = 0;
		int out_iter = 0;
		int out_iter_best = 0;

		int outer_no_improve_round = 0;
		int no_improve_time = 0;
		int energy_change = 0;

		int p1 = 1;
		int p2 = 2;
		int p = p1;

		double INIT_T    = 200; // 100
		double FINAL_T   = 0.1; // 1
		double COOLING   = 0.999;

		int NO_CHANGE_TIME = 250000;
		int OUT_ITER_TIME  = 200;

		int neighber_round = 2;
		int no_edge_flag   = 0;

		if (graph_instance->m() == 0) no_edge_flag = 1;

		for (int i = 0; i < OUT_ITER_TIME; ++i)
		{
			if (no_edge_flag == 1) break;
			
			// cout << "SA|out iter = " << i << endl;
			out_iter++;
			COOLING = COOLING + (1.0 - COOLING)/(double)(OUT_ITER_TIME - i);
			int improve_flag = 0;


		for (double t = INIT_T; t > FINAL_T; t *= COOLING) { //

			Solution next_s(s);

			// shake
			// p[0]: larger->more diversity search
			if (k % neighber_round == 0) {
				p = p1;
			}
			else if (k % neighber_round == 1) {
				p = p2;
			}
			else {
				p = p2;
			}
			next_s.force(p);

			assert(next_s.integrityCheck());

			do {
				while (!next_s.isMaximal()) {
					next_s.addRandomVertex();
				}
			} while (next_s.omegaImprovement() || next_s.twoImprovement());
			iter ++;

			assert(best_s.integrityCheck());

			// if a better solution is found, set k=1
			if (next_s.weight() > s.weight()) { 
				k = 0;
				//update s
				s = next_s;

				if (local_best < next_s.weight()) {
					// k -= s.size() / 4; //ArgPack::ap().p[1];
					k = 1;
					local_best = next_s.weight();
					no_improve_time = 0;
					improve_flag = 1;
				}

				//update best_s, record the time+iter of best_s
				if (best_s.weight() < s.weight()) {
					best_s = s;
					// k -= s.size() * 4; //ArgPack::ap().p[2];
					// k++;

					target_time = proc_timer.getTime();
					target_iterations = iter;

					out_iter_best = out_iter;
					no_improve_time = 0;
					improve_flag = 1;

					//exit if a target weight is found
					if (ArgPack::ap().target != 0 && best_s.weight() >= ArgPack::ap().target) {
						goto exit;
					}

					//print if verbose is set
					if (ArgPack::ap().verbose)
						cout << "new best weight: " << best_s.weight() << " / iteration: "<<  iter
					         <<" / time (s): " << proc_timer.getTime() << "\n";
				}
			}
			else {
				no_improve_time ++;
				if (no_improve_time > NO_CHANGE_TIME) {
					if (ArgPack::ap().verbose)
						printf("-- [IN] Exit early.--\n");
					break;
				}

				uniform_int_distribution<int> distribution(0, MAX_PARA/500);
				int rand_num = distribution(generator);				
				double ACCEPT_PARA = (double)rand_num / (double)MAX_PARA ;

				energy_change = next_s.weight() - s.weight();
				if ( ACCEPT_PARA < exp(-energy_change/t)) {
					s = next_s;
					// Skip out of local optimal
				} 
				k = 1;
			}
		}

			if (no_improve_time > NO_CHANGE_TIME) {
				if (ArgPack::ap().verbose)
					printf("-- Exit early.--\n");
				break;
			}
			if (improve_flag == 0) outer_no_improve_round++;
			if (outer_no_improve_round == 4)
			{
				if (ArgPack::ap().verbose)
					printf("-- Exit early.--\n");
				break;
			}
		}

exit:
		proc_timer.pause();
		assert(best_s.integrityCheck());

		int show_detail_res = 1;
		if (show_detail_res) {
			cout << "- best weight: " << best_s.weight() <<"\n";
			cout << "- size: " << best_s.size() << "\n";
			cout << "- solution: ";
			for(int v : best_s.i_set()) {
				cout << v << " ";
			}
			cout << "\n";
			// we add a fixed compiler merging time to the merging algorithm
			// It is average about 0.1 seconds when turn off all the logs and DBGs
			// In this way we can compare the algorithm time more clearly
			double fixed_compiler_merge_time = 0.1;
			cout << "- total processing time (s): " << proc_timer.getTime() + fixed_compiler_merge_time << "\n\n\n";
			if (ArgPack::ap().verbose)
				cout << "- time to find the best (s): " << target_time + fixed_compiler_merge_time<< "\n"; 
		} else {
			cout << best_s.weight() << " " << target_time << " " << proc_timer.getTime() << "\n";
		}

		ofstream ofs;
		ofs.open (ArgPack::ap().outfile, std::ofstream::out | std::ofstream::app);
		for(int v : best_s.i_set()){
			ofs << v << endl;
		}
		ofs.close();

		delete(graph_instance);

	} catch (std::exception &e) {
		cerr << e.what();
	}

	return 0;
}