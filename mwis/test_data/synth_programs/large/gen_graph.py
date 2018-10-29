
import random



def gen_graph(n, dens, max_w):
	e_num = 0
	adj = [[0 for i in range(n)] for i in range(n)]
	for i in xrange(n):
		for j in xrange(i, n):
			if random.random() < dens:
				if i !=j :
					adj[i][j] = 1
					e_num = e_num + 1
			

	filename = "n"+str(n)+"_"+str(dens)+"_gen.wmis"
	# f = open("filename", "w+")
	with open(filename, 'a+') as f:
		f.truncate()
		f.write("p edge "+str(n)+" "+str(e_num)+"\n")
		for i in xrange(n):
			max_weight_here = max_w
			w_i = random.uniform(1, max_weight_here)
			# We set 1/4 table number the same size: 4028
			# Because this is also the very commom size in real programs 
			if i%1 == 0 and  i < n/4:
				w_i = 4096
			w_i = int(w_i)
			line = "n "+str(i+1)+" "+str(w_i)+"\n"
			f.write(line)

		for i in xrange(n):
			for j in xrange(i, n):

				if adj[i][j] == 1:
					line = "e "+str(i+1)+" "+str(j+1)+"\n"
					f.write(line)
	f.close()




for v_num in (60, 70, 80,   120,  240,  480,  1000):
	max_weight = v_num
	for x in xrange(1,3):
		density = x*0.1
		gen_graph(v_num, density, max_weight) 
