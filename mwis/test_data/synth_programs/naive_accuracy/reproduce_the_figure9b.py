
# This file reproduce the figure 9a after runing the two algorithms:
#   1) ./test_synth_p4_naive.sh
#   2) ./test_synth_p4_sa.sh

import numpy as np
import matplotlib.pyplot as plt
from matplotlib import ticker
from matplotlib.ticker import FuncFormatter, MultipleLocator
import os
import matplotlib.pylab as pylab

from matplotlib.ticker import FormatStrFormatter



def plot(): 

	# file recorded the results

	file_name_naive = 'sum_res-naive.txt'
	file_name_sa = 'sum_res-sa.txt'


	# extract datas

	best_weight_na = []
	best_weight_sa = []
	fna = open('sum_res-naive.txt', 'r')
	for line in fna: 
		sl =  line.split() 
		if len(sl) == 4:
			if (sl[2] == 'weight:'):
					best_weight_na.append(float(sl[3]))

	fsa = open('sum_res-sa.txt', 'r')
	for line in fsa:
		sl =  line.split()
		if len(sl) == 4:
			if (sl[2] == 'weight:'):
				best_weight_sa.append(float(sl[3]))

	na_sa_ratio = []

	for i in range(0, len(best_weight_sa)):
		ratio_i = best_weight_na[i] / best_weight_sa[i]
		na_sa_ratio.append(ratio_i)
		# print best_weight_na[i], best_weight_sa[i], ratio_i


	# plot paramaters

	params = {
		'axes.labelsize' : '10',
		'xtick.labelsize' : '8',
		'ytick.labelsize' : '8',
		'legend.fontsize' : '10',
	}

	overlap = xrange(0,5)


	nodes_greedy_accu_30 = [1] + na_sa_ratio[0:4]
	nodes_greedy_accu_50 = [1] + na_sa_ratio[4:8]
	nodes_greedy_accu_80 = [1] + na_sa_ratio[8:12]

	fig, ax = plt.subplots()

	error_config = {'ecolor': '0.3'}

	ax.plot(overlap, nodes_greedy_accu_30,  color='r', marker='>', ls=':', label='Nodes=30')
	ax.plot(overlap, nodes_greedy_accu_50, color='b', marker='d', ls='--', label='Nodes=50')
	ax.plot(overlap, nodes_greedy_accu_80,  color='cyan', marker='h', ls='-', label='Nodes=80')

	ax.yaxis.set_major_formatter(FuncFormatter(lambda y, _: '{:.0%}'.format(y))) 

	plt.xlabel('Overlap Rates')
	plt.ylabel('Accuracy of the solutions')

	plt.xlim([-0.2, 4.3])
	plt.ylim([0,1])

	plt.xticks(overlap, ('1', '0.9', '0.8', '0.7', '0.6' ) )
	xticks = overlap

	plt.legend(loc='best')

	# save figure

	fig.savefig('fig9a_naive_accuracy' + '.png')

	plt.show()

plot()

