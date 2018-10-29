/*
 *  Created on: 14/09/2015 by Bruno
 *     A framework for the independent set problem
 * 
 *  Modified on: 08/09/2017 by Peng
 *     Add implementation of simulated annealing and naive greedy algorithm
 *     Add implementation of Bron-Kerbosch algorithm
 */

#include "Solution.h"
#include "ArgPack.h"

#include <algorithm>
#include <random>
#include <iostream>

using namespace std;

namespace opt
{

extern mt19937 generator; // Mersenne Twister 19937 generator

Solution::Solution(const Graph *g) :
	g_(g),
	solution_(g_->n()),
	solution_size_(0),
	free_size_(g_->n()),
	tightness_(g_->n(), 0),
	position_(g_->n()),
	mu_(g_->n()),
	weight_(0)
{
	for (int idx = 0; idx < g_->n(); idx++) {
		position_[idx] = idx;
		solution_[idx] = idx;
		mu_[idx] = g_->weight(idx);
	}
} // Solution::Solution(const Graph *g)

void Solution::moveFreeToSolutionPartition(const int v)
{
	assert(v < g_->n());

	// current position of v in the solution_ vector
	int pos_v = position_[v];

	// new position of v in the solution_ vector
	int new_pos_v = solution_size_;

	// first vertex of the second partition
	int j = solution_[solution_size_];

	// ensures v is in the free partition of the solution vector
	assert((solution_size_ <= pos_v) && (solution_size_ + free_size_ > pos_v));

	// swap v with the first vertex of the second partition
	swap(solution_[pos_v], solution_[new_pos_v]);
	position_[v] = new_pos_v;
	position_[j] = pos_v;

	// change the boundary between the blocks to make v the last vertex of the
	// first partition
	solution_size_++;
	free_size_--;
} // void Solution::moveFreeToSolutionPartition(const int v)

void Solution::moveFreeToNonFreePartition(const int v)
{
	assert(v < g_->n());

	// current position of v in the solution vector
	int pos_v = position_[v];

	// new position of v in the solution vector
	int new_pos_v = solution_size_ + free_size_ - 1;

	// last vertex of the second partition
	int j = solution_[solution_size_ + free_size_ - 1];

	// ensures v is in the free partition of the solution vector
	assert((solution_size_ <= pos_v) && (solution_size_ + free_size_ > pos_v));

	// swap v with the last vertex of the second partition
	swap(solution_[pos_v], solution_[new_pos_v]);
	position_[v] = new_pos_v;
	position_[j] = pos_v;

	// change the boundary between the blocks to make v the last vertex of the
	// second partition
	free_size_--;
} // void Solution::moveFreeToNonFreePartition(const int v)

void Solution::moveSolutionToFreePartition(const int v)
{
	assert(v < g_->n());

	// current position of v in the solution vector
	int pos_v = position_[v];

	// new position of v in the solution vector
	int new_pos_v = solution_size_ - 1;

	// last vertex of the first partition
	int j = solution_[solution_size_ - 1];

	// ensures v is in the solution partition of the solution vector
	assert(pos_v < solution_size_);

	// swap v with the last vertex of the second partition
	swap(solution_[pos_v], solution_[new_pos_v]);
	position_[v] = new_pos_v;
	position_[j] = pos_v;

	// change the boundary between the blocks to make v the first vertex of the
	// second partition
	solution_size_--;
	free_size_++;
} // void Solution::moveSolutionToFreePartition(const int v)

void Solution::moveNonFreeToFreePartition(const int v)
{
	assert(v < g_->n());

	// current position of v in the solution vector
	int pos_v = position_[v];

	// new position of v in the solution vector
	int new_pos_v = solution_size_ + free_size_;

	// first vertex of the third partition
	int j = solution_[solution_size_ + free_size_];

	// ensures v is in the non free partition of the solution vector
	assert(pos_v >= solution_size_ + free_size_);

	// swap v with the last vertex of the second partition
	swap(solution_[pos_v], solution_[new_pos_v]);
	position_[v] = new_pos_v;
	position_[j] = pos_v;

	// change the boundary between the blocks to make v the last vertex of the
	// second partition
	free_size_++;
} // void Solution::moveNonFreeToFreePartition(const int v)

void Solution::addVertex(const int v)
{
	int weight_v = g_->weight(v);
	weight_ += weight_v;

	moveFreeToSolutionPartition(v);

	const vector<int> &adj_l = g_->adj_l(v);

	for (int neighbor : adj_l) {
		// increase the tighness of each neighbor by one
		tightness_[neighbor]++;

		mu_[neighbor] -= weight_v;

		// if the neighbor is in the free partition, move to non free partition
		int neighbor_pos = position_[neighbor];
		if ((solution_size_ <= neighbor_pos) && (solution_size_ + free_size_ > neighbor_pos)) {
			moveFreeToNonFreePartition(neighbor);
		}
	}
} // void Solution::addVertex(const int v)

void Solution::removeVertex(const int v)
{
	int weight_v = g_->weight(v);
	weight_ -= weight_v;

	moveSolutionToFreePartition(v);

	const vector<int> &adj_l = g_->adj_l(v);

	for (int neighbor : adj_l) {
		tightness_[neighbor]--;

		mu_[neighbor] += weight_v;

		// if the neighbor becomes free
		if (tightness_[neighbor] == 0) {
			moveNonFreeToFreePartition(neighbor);
		}
	}
} // void Solution::removeVertex(const int v)

bool Solution::integrityCheck() const
{
	for (int idx = 0; idx < solution_size_; idx++) {
		int vertex = solution_[idx];

		if (tightness_[vertex] > 0) {
			return false;
		}

		for (int neighbor : g_->adj_l(vertex)) {
			if (find(solution_.begin(), solution_.begin() + solution_size_, neighbor)
			        != solution_.begin() + solution_size_) {
				return false;
			}
		}
	}

	for (int idx = solution_size_; idx < solution_size_ + free_size_; idx++) {
		int vertex = solution_[idx];
		if (tightness_[vertex] > 0) {
			return false;
		}
	}

	for (int idx = solution_size_ + free_size_; idx < g_->n(); idx++) {
		int vertex = solution_[idx];
		if (tightness_[vertex] == 0) {
			return false;
		}
	}

	return true;
} // bool Solution::integrityCheck() const

void Solution::addRandomVertex()
{
	assert(!isMaximal());

	// generate a random number between [0, free_size_ - 1]
	uniform_int_distribution<int> distribution(0, free_size_ - 1);
	int free_pos = distribution(generator);

	int vertex = solution_[solution_size_ + free_pos];

	addVertex(vertex);
} // void Solution::addRandomVertex()


void Solution::addVertexDegreeLowest()
{
	assert(!isMaximal());

	int lowest_pos = solution_size_;
	int lowest_degree = g_->adj_l(solution_[lowest_pos]).size();

	for (int i = 0; i < free_size_; ++i)
	{
		int current_pos = solution_size_ + i;
		int current_degree = g_->adj_l(solution_[current_pos]).size();
		if (current_degree < lowest_degree)
		{
			lowest_degree = current_degree;
			lowest_pos = current_pos;
		}
		
	}

	int vertex = solution_[lowest_pos];

	addVertex(vertex);
}


bool Solution::omegaImprovement()
{
	for (int idx = g_->n() - 1; idx >= solution_size_; idx--) {
		int v = solution_[idx];
		if (mu_[v] > 0) {
			for (int neighbor : g_->adj_l(v)) {
				if (position_[neighbor] < solution_size_) {
					removeVertex(neighbor);
				}
			}
			addVertex(v);
			return true;
		}
	}

	return false;
} // bool Solution::swapImprovement()

bool Solution::twoImprovement()
{
	assert(isMaximal());

	for (int idx = 0; idx < solution_size_; idx++) {
		// the candidate for removal
		int x = solution_[idx];

		// sorted list of 1-tight nighbors of x
		vector<int> onetight_list;

		// build the list of 1-tight nighbors of x
		for (int neighbor : g_->adj_l(x)) {
			if (tightness_[neighbor] == 1) {
				onetight_list.push_back(neighbor);
			}
		}
		assert(is_sorted(onetight_list.begin(), onetight_list.end()));

		// if x has fewer than two 1-tight neighors we are done with x
		if (onetight_list.size() < 2) continue;

		int x_weight = g_->weight(x);

		// attempt to find in onetight_list a pair {v, w} such that there
		// is no edge between v and w
		for (int v : onetight_list) {

			// stores the sorted list of v nighbors
			vector<int> v_neighbors(g_->adj_l(v));
			assert(is_sorted(v_neighbors.begin(), v_neighbors.end()));

			// check if there is a vertex w in onetight_list (besides v) that
			// does not belong to v_neighbors. since both onetight_list and v_neighbors
			// are sorted, this can be done by traversing both lists in tandem.
			size_t i_idx = 0, j_idx = 0;
			while ( i_idx < v_neighbors.size() && j_idx < onetight_list.size() ) {
				if (onetight_list[j_idx] == v) {
					j_idx++;
					continue;
				} else if (v_neighbors[i_idx] < onetight_list[j_idx]) {
					i_idx++;
					continue;
				}  else if (v_neighbors[i_idx] == onetight_list[j_idx]) {
					i_idx++;
					j_idx++;
					continue;
				}

				// if this point is reached, this means we found the pair {v, w}
				// we were looking for !!
				int w = onetight_list[j_idx];

				int weight_v = g_->weight(v);
				int weight_w = g_->weight(w);

				if (x_weight >= weight_v + weight_w) {
					i_idx++;
					continue;
				}

				removeVertex(x);
				addVertex(v);
				addVertex(w);
				return true;
			}
		} // for(int v : onetight_list) {
	} // for(int x : cadidate_list) {

	return false;
} // bool Solution::twoImprovment()

bool Solution::threeImprovement()
{
	assert(isMaximal());

	// for each 2-tight vertex u..
	for (int idx = solution_size_; idx < g_->n(); idx++) {
		int u = solution_[idx];
		if (tightness_[u] != 2) continue;

		// temporarly remove neighbors vertices x and y from the solution
		vector<int> xy;
		for (int j : g_->adj_l(u)) {
			if (position_[j] < solution_size_) {
				xy.push_back(j);
			}
		}
		removeVertex(xy[0]);
		removeVertex(xy[1]);

		int weight_xy = g_->weight(xy[0]) + g_->weight(xy[1]);

		// temporarly add vertex u (which now is free)
		addVertex(u);

		// if there are less than two free vertices, we are done with u
		if (free_size_ >= 2) {
			// temporarly add each free vertex that is neighbor of x
			for (int v : g_->adj_l(xy[0])) {
				if (position_[v] >= solution_size_ && position_[v] < solution_size_ + free_size_) {
					addVertex(v);
					// if the solution is not maximal, adding any free vertex w will
					// create a valid solution (thus leading to a 3-improvement)
					if (!isMaximal()) {
						int weight_uvz = g_->weight(u) + g_->weight(v) +
						                 g_->weight(solution_[solution_size_]);
						if (weight_uvz > weight_xy) {
							addVertex(solution_[solution_size_]);
							return true;
						}
					}
					// remove back v
					removeVertex(v);
				}
			}
		}

		// add back x, and y, and remove u
		removeVertex(u);
		addVertex(xy[0]);
		addVertex(xy[1]);
	} // for (size_t idx = solution_size_; idx < g_->n(); idx++)

	return false;
} // bool Solution::threeImprovement()

void Solution::force(int k)
{
	for(int i = 0; i < k; i++) {
		// select a non solution vertex to add
		int nonsolution_size = g_->n() - (solution_size_ + free_size_);
		uniform_int_distribution<int> discrete_distribution(0, nonsolution_size - 1);
		int nonsolution_pos = discrete_distribution(generator);
		int vertex = solution_[solution_size_ + free_size_ + nonsolution_pos];

		// remove the neighboring vertices as necessary
		for (int neighbor : g_->adj_l(vertex))	{
			if (position_[neighbor] < solution_size_) {
				removeVertex(neighbor);
			}
		}
		addVertex(vertex);
	}
} // void Solution::force()

} // namespace opt