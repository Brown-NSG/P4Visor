## Overview
Here are the implementation and evaluation of the three algorithms for the maximum weighted independent set (MWIS) problem:
- Simulated annealing (SA) heuristic: good balance between accuracy and efficiency
- Bron-Kerbosch (BK) optimal algorithm: always return the optimal solutions
- Naive greedy algorithm: very fast but can not find the optimal solutions

More details on implementation can be found in `src/main.c` file.

## Build
```
make
```

## Usage
Run the simulated annealing algorithm:
```
./mwis input/graph.mwis
```

Run the Bron-Kerbosch optimal algorithm:
```
./mwis input/graph.mwis -B -W
```

Run the naive greedy algorithm:
```
./mwis input/graph.mwis -N
```

## Input weighted graph format

See the example in the directory `test_data`. There is an example. The first line gives the node number and edge number of the graph, followed by node weight pairs and edges each line.
```
p edge n_num e_num
n 1 1
n 2 1
...
e 13 12
e 26 23
e 28 24
...
```

## Output example 
The output is the detail of the maximum weighted graph found. Here is an example:
```
- best weight: 1100469
- size: 16
- solution: 3 4 6 11 13 14 22 24 26 27 28 50 58 65 93 97
- total processing time (s): 0.164381
```
That information can make table merging in ShadowP4/P4Visor more efficiency.


## Evaluation on accuracy and efficiency

### 1. Dataset

We have both real and synthetic P4 program graphs for evaluation.

- (1) Real P4 Programs graphs

The real P4 programs graphs are based on the switch.p4 program, as shown in the folder `test_data/real_programs/p4src/`. We merge each of two real P4 programs and thus produces 6 merging results, as shown in the `vi+vj` folder, each contains one ingress graph ( see file `ingress_table_graph.csv`) and one egress graph (see file `egress_table_graph.csv`). Specifically, we provide the script `gen_wmis_from_real_p4switch.sh` under the root directory to produce all the real P4 programs graphs. 
```
./gen_wmis_from_real_p4switch.sh
```
Please first change to the root directory where the script located before running.


- (2) Synthetic program graphs

The synthetic program graphs have randomly generated edges and weights (some node weights also come from real P4 programs, i.e. 1024, 2048). As shown in the folder `test_data/synth_programs/`, the `small` dataset can evaluate the accuracy of the SA heuristic, and the `large` dataset can evaluate the efficiency of the SA heuristic. We provide the python script `gen_graph.py` under each sub-folder to generate the graphs:
```
python gen_graph.py
```
We can generate the graphs of different patterns by setting the nodes number, maximum weight or density in `gen_graph.py` (the function interface is `def gen_graph(n, dens, max_w):`). So we are able to generate various synthetic graphs to test the three algorithms.

We have pushed the running results of the two scripts above to the repository for reference.



### 2. How to evaluate

We provide well-organized scripts to run the evaluation experiments and collect the results. Two key metrics are recorded: (1) the best weight of the solution and the (2) running time of the algorithm. Those results will be collected in a single output file for each algorithm.

For the real programs, we provide the following shell scripts to evaluate the three algorithms:
```
cd test_data/real_programs
./test_real_p4_naive.sh
./test_real_p4_sa.sh
./test_real_p4_opt.sh
```

  
For the synthetic programs, we provide the following shell scripts to evaluate the three algorithms:
```
cd test_data/synth_programs
./test_synth_p4_naive.sh
./test_synth_p4_sa.sh
./test_synth_p4_opt.sh
```

Please run those scripts in the path where they are located one by one. Each script produces two output files, named `detail_res-*.txt` and `sum_res-*.txt`. The first one records the detailed outputs of the algorithm. The later one gives a summary of the evaluation, which contains the two key metrics for the tested graphs. Note that it may take days to get the summary file `sum_res-opt.txt` for the optimal algorithm. However, we can see the real-time results for some cases in the detailed output file `detail_res-opt.txt`.

The format of output files are easy to read. Take the file `test_data/synth_programs/sum_res-sa.txt` as an example, the lines 1-22 give the case names in order; the lines 23-44 give the best weight of each case (listed in lines 1-22) with the same order; the lines 46-67 list the total running time of the cases in the same order, respectively. The lines 45 and 68 are the average best weight and average running time.


### 3. How to produce the results

After running the shell scripts aforementioned, we can get the following output files in their directories. In both the `test_data/real_programs` and `test_data/synth_programs`, three outputs summary files are generated:
- `sum_res-naive.txt`
- `sum_res-sa.txt`
- `sum_res-opt.txt`

We can get the running time and accuracy of SA heuristic by comparing the results of the three different algorithms. 

- (1) Running time

The running times of the three algorithms lie in `sum_res-*.txt` files. By comparing the running times of the three algorithms, we can find that SA heuristic has good efficiency for large graphs with even 1000 nodes: both SA heuristic and naive greedy can merge P4 programs graphs within seconds. However, BK optimal algorithm is not scalable with graph size: usually, it can not return results for large graphs with more than 80 nodes within 7 days.

Figure 8 "The runtimes of three merging approaches" can be generated from the outputs. Specifically, results in Figure 8a 'real program runtime' can be generated from the data in files 1) `real_programs/sum_res-sa.txt` line 26-31; 2) `real_programs/sum_res-naive.txt` line 26-31; 3) `real_programs/sum_res-opt.txt` where lines marked with 'total processing time' (it may take 1-2 days to produce this file). 

Similarly, results in Figure 8b 'synthetic program runtime' can be generated from the three files under the folder `synth_programs`. 1) `synth_programs/sum_res-sa.txt` lines 46-67; 2) `synth_programs/sum_res-naive.txt` lines 46-67; 3) `synth_programs/sum_res-opt.txt`, which may also take days to produce. 

We can use the following script to produce the runtime figure on synthetic like Figure 8b:
```
python plot_synth_runtime.py
```

- (2) Accuracy

To evaluate the accuracy of SA heuristic, we show that SA heuristic can find all the optimal solution for graphs less than 60 nodes (we can check larger graphs which takes more time). We can compare the outputs of SA heuristic with the optimal algorithm (Bron-Kerbosch) using the small graph size in both real programs (ingress graphs) and synthetic program graphs. 

First, we can find that our heuristic can get all the optimal solutions produced by the BK optimal algorithm, as shown in Figure 9a: see the 'best weight' lines in file `synth_programs/sum_res-opt.txt`, which should be the same as the 'best weight' lines produced by heuristic in file `synth_programs/sum_res-sa.txt`. At the same time, naive greedy cannot find the best solution for most of the cases as shown in files `synth_programs/sum_res-naive.txt` and the accuracy (see lines 23-44 of `sum_res-naive.txt` and `sum_res-sa.txt`) decrease dramatically with the increase of the graph node number.

Besides, we can find the accuracy of the naive greedy decrease with the increase in the graph density. With the increase of the program graph density (from 0.1 to 0.4), the accuracy of naive greedy keep decreasing. This can be observed by the following commands, as shown in Figure 9b: 
```
cd test_data/synth_programs/naive_accuracy
source test_greedy_accuracy.sh
``` 
Here we can see the results in `naive_accuracy` folder: the lines 13-24 of files `synth_programs/naive_accuracy/sum_res-sa.txt` and `synth_programs/naive_accuracy/sum_res-naive.txt`. 

Next, we can run the following command to extract results files and reproduce the figure 9a:
```
python reproduce_the_figure9b.py
```

Please note that each time we run the script `python gen_graph.py`, we will generate a different set of random graphs under the same parameters, such as density and size. A different set of the graphs may lead to slightly different runtime and accuracy, however, the conclusion always holds.



**Footnote**: The codes are tested on VM: Ubuntu 16.04 LTS, 5GB, Intel® Core™ i5-7360U CPU @ 2.30GHz × 2. The host is MacBook Pro (13-inch, 2017, Two Thunderbolt 3 ports), 8 GB 2133 MHz LPDDR3, 2.3 GHz Intel Core i5.
