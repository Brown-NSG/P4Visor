/*
 *  Created on: 14/09/2015 by Bruno
 *     A framework for the independent set problem
 * 
 *  Modified on: 08/09/2017 by Peng
 *     Add implementation of simulated annealing and naive greedy algorithm
 *     Add implementation of Bron-Kerbosch algorithm
 */

#ifndef GRAPH_H_
#define GRAPH_H_

#include <vector>
#include <string>
#include <assert.h>
#include <algorithm>

namespace opt {

class Graph
{

public:

	// return the number of edges

	int m() const { return m_; }

	// return the number of vertices

	int n() const { return n_; }

	// return the weight of vertice v

	int weight(const int v) const { return weights_[v]; }

	// return the adjency list of vertex i

	const std::vector<int>& adj_l(const int i) const
	{
		assert(i < n_);

		return adj_l_[i];
	}

	Graph(const int n, const int m);

	void setWeight(const int i, const int wi);

	void addEdge(const int i, const int j);

	void removeEdge(const int i, const int j);

	// sort the adjacency lists

	void sort();

private:

	std::vector<int> weights_; // vertices weight

	int n_; // number of vertices

	int m_; // number of edges

	// int adjMatrix[n_][n_];

	std::vector< std::vector<int> > adj_l_; // adjaceny list

	void setWeight_(const int i, const int wi) {
		weights_[i] = wi;
	}

	void addNeighbor(const int i, const int j)
	{
		adj_l_[i].push_back(j);
	}

	void removeNeighbor(const int i, const int j) 
	{		
		adj_l_[i].erase(std::remove(adj_l_[i].begin(), adj_l_[i].end(), j), adj_l_[i].end());
	}

}; // class Graph

} // namespace opt

#endif // #ifndef GRAPH_H_