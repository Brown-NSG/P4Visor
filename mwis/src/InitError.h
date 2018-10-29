/*
 *  Created on: 14/09/2015 by Bruno
 *     A framework for the independent set problem
 * 
 *  Modified on: 08/09/2017 by Peng
 *     Add implementation of simulated annealing and naive greedy algorithm
 *     Add implementation of Bron-Kerbosch algorithm
 */

namespace opt
{

class InitError : public std::exception
{

public:

	InitError(const std::string & err) : what_(ArgPack::ap().program_name + ": " + err) {}

	virtual ~InitError() throw () {}

	virtual const char * what() const throw () { return what_.c_str(); }

private:

	std::string what_;

};

} // namespace opt