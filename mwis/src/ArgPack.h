/*
 *  Created on: 14/09/2015 by Bruno
 *     A framework for the independent set problem
 * 
 *  Modified on: 08/09/2017 by Peng
 *     Add implementation of simulated annealing and naive greedy algorithm
 *     Add implementation of Bron-Kerbosch algorithm
 */

#ifndef ARGPACK_H_
#define ARGPACK_H_

#include <string>
#include <assert.h>

namespace opt {

class ArgPack {

public:

	//------------
	// program parameters
	//------------

	bool verbose;

	bool bronkerbosch;

	bool naive_greedy;

	long rand_seed;

	int target;

	int complement;

	std::string input_name, program_name;

	char* outfile;

	int iterations; // maximum iteration number

	double p[4]; // intensification/exploration parameters

	//------------
	// singleton functions
	//------------

	static const ArgPack &ap() { assert(def_ap_); return *def_ap_; }

//	static ArgPack &write_ap() { assert(def_ap_); return *def_ap_; }

	ArgPack(int argc, char * const argv []);

	~ArgPack() { assert(def_ap_); def_ap_ = 0; }

private:

	//------------
	// singleton instance
	//------------

	static ArgPack *def_ap_;

};

}

#endif /* ARGPACK_H_ */