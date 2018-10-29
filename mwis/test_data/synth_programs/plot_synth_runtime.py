import numpy as np
import matplotlib.pyplot as plt
from matplotlib import ticker
from matplotlib.ticker import FuncFormatter, MultipleLocator
import os
import matplotlib.pylab as pylab

from matplotlib.ticker import FormatStrFormatter



def plot(): 

	# extract datas

	runtime_na = []
	runtime_sa = []
	fna = open('sum_res-naive.txt', 'r')
	for line in fna: 
		sl =  line.split() 
		if len(sl) == 6:
			if (sl[3] == 'time'):
					runtime_na.append(float(sl[5]))

	fsa = open('sum_res-sa.txt', 'r')
	for line in fsa:
		sl =  line.split()
		if len(sl) == 6:
			if (sl[3] == 'time'):
				runtime_sa.append(float(sl[5]))



	# plot paramaters

	params = {
		'axes.labelsize' : '10',
		'xtick.labelsize' : '8',
		'ytick.labelsize' : '8',
		'legend.fontsize' : '10',
	}

	MAX = 10000000

	# nodes get from lines 1-22 of files 'sum_res*.txt'
	sp_nodes = [20,20,30,30,40,40,50,50,60,70,60,80,70,80,120,120,240,240,480,480,1000,1000]

	optimal = [ 0.407141, 0.167333, 18.6797, 11.0554, 32985.7,
				1176.93, MAX, MAX, MAX, MAX, MAX, MAX, MAX, MAX, MAX,
				MAX, MAX, MAX ,MAX, MAX, MAX, MAX, ]

	sp4 = runtime_sa
	naive = runtime_na

	fig, ax = plt.subplots()

	error_config = {'ecolor': '0.3'}

	ax.plot(sp_nodes, optimal,  color='r', marker='o', ls=':', label='Optimal')
	
	ax.plot(sp_nodes, sp4, color='b', marker='s', ls='--', label='P4Visor')

	ax.plot(sp_nodes, naive,  color='cyan', marker='^', ls='-', label='Naive merge')

	formatter = ticker.ScalarFormatter(useMathText=True)
	formatter.set_scientific(True)
	ax.yaxis.set_major_formatter(formatter)
	ax.xaxis.set_major_formatter(formatter)


	formatter = ticker.ScalarFormatter(useMathText=True) 
	formatter.set_powerlimits((0,2))

	plt.yscale('log')
	plt.xscale('log')

	plt.xlabel('Node numbers')
	plt.ylabel('Solution time(s)')

	min_x = 0.01
	max_x = 5000000 
	plt.xlim([15,1344])
	plt.ylim([min_x,max_x])

	xticks = (  40, 50,  60, 80,  120,  240,  480,  1000 )
	xticks = sp_nodes

	ax.set_xscale('log') 

	plt.legend(loc='upper right')

	plt.show()


plot()
