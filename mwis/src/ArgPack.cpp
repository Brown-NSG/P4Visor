/*
 *  Created on: 14/09/2015 by Bruno
 *     A framework for the independent set problem
 * 
 *  Modified on: 08/09/2017 by Peng
 *     Add implementation of simulated annealing and naive greedy algorithm
 *     Add implementation of Bron-Kerbosch algorithm
 */

#include "ArgPack.h"
#include "InitError.h"

#include <string>
#include <cstring>
#include <unistd.h> // for getopt
#include <iostream>

extern int optind;

using namespace std;

namespace opt
{

ArgPack *ArgPack::def_ap_ = 0;

ArgPack::ArgPack(int argc, char * const argv []) :
	bronkerbosch(false),
	naive_greedy(false),
	verbose(false),
	outfile("tmp"),
	rand_seed(1),
	target(0),
	complement(0),
	iterations(2000),
	p{2,4,4,1}
{

	assert(!def_ap_);
	def_ap_ = this;
	program_name = argv[0];

	string usage = string("Usage: ") + program_name + " [options] <input file>\n" +
	               "	[default] : use Simulated annealing algorithm\n" +
				   "	-B -W     : use Bron-Kerbosch algorithm \n" +
				   "	-N        : use Naive greedy algorithm \n" +
			       "	-h        : show this help\n" +
			       "	-v        : show more log\n" +
	            //    "	-W        : run the algorithm on the graph's complement\n" + 
	               "	-o        : output filename\n";
	string help = "Use -h for more information\n";

	const char *opt_str = "hs:vt:Wp:io:BN";

	long ch;

	while ((ch = getopt(argc, argv, opt_str)) != -1)
	{
		switch (ch)
		{
		case 'h':
			throw InitError(usage);
		case 'W':
			complement = 1;
			break;
		case 't':
			target = strtoul(optarg, NULL, 10);
			break;
		case 'i':
			iterations = strtoul(optarg, NULL, 10);
			break;
		case 's':
			rand_seed = strtoul(optarg, NULL, 10);
			break;
		case 'v':
			verbose = true;
			break;
		case 'B':
			bronkerbosch = true;
			break;
		case 'N':
			naive_greedy = true;
			break;
		case 'o':
			outfile = strdup(optarg);
			break;
		case 'p':
		{
			char* token = NULL;
			int i = 0;
			token = strtok(optarg, ":");
			while (token) {
				p[i] = strtoul(token, NULL, 10);
				token = strtok(NULL, ":");
				i++;
			}

			if(i != 4)
				throw InitError("wrong input format for -p option\n");
			break;
		}
		case '?':
			throw InitError(help);
		}
	}
	argc -= optind;
	argv += optind;

	if (argc > 1)
	{
		throw InitError("Too many arguments\n" + help);
	}
	else if (argc < 1)
	{
		throw InitError("Too few arguments\n" + help );
	}
	else
	{
		input_name = argv[0];
	}
}

} // namespace opt