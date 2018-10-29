#!/bin/bash


echo ' '
echo "======BK optimal algorithm======="
echo ' '


# clean file

rm detail_res-opt.txt
rm sum_res-opt.txt



# Run egress graphs
# cases v1+v3, v1+v4 and v3+v4 may take long time to rum; be patient

echo ./v1+v2/egress_table_graph >> detail_res-opt.txt
../../bin/mwis v1+v2/egress_table_graph.csv -B -W -o tmp >> detail_res-opt.txt

echo ./v1+v3/egress_table_graph >> detail_res-opt.txt
../../bin/mwis v1+v3/egress_table_graph.csv -B -W -o tmp >> detail_res-opt.txt

echo ./v1+v4/egress_table_graph >> detail_res-opt.txt
../../bin/mwis v1+v4/egress_table_graph.csv -B -W -o tmp >> detail_res-opt.txt

echo ./v2+v3/egress_table_graph >> detail_res-opt.txt
../../bin/mwis v2+v3/egress_table_graph.csv -B -W -o tmp >> detail_res-opt.txt

echo ./v2+v4/egress_table_graph >> detail_res-opt.txt
../../bin/mwis v2+v4/egress_table_graph.csv -B -W -o tmp >> detail_res-opt.txt

echo ./v3+v4/egress_table_graph >> detail_res-opt.txt
../../bin/mwis v3+v4/egress_table_graph.csv -B -W -o tmp >> detail_res-opt.txt



# Run ingress graphs for the optimal algorithm
# are too large graph for the optimal algorithm - days to run

# ../../bin/mwis v1+v2/ingress_table_graph.csv -B -W -o tmp >> detail_res-opt.txt
# ../../bin/mwis v1+v3/ingress_table_graph.csv -B -W -o tmp >> detail_res-opt.txt
# ../../bin/mwis v1+v4/ingress_table_graph.csv -B -W -o tmp >> detail_res-opt.txt
# ../../bin/mwis v2+v3/ingress_table_graph.csv -B -W -o tmp >> detail_res-opt.txt
# ../../bin/mwis v2+v4/ingress_table_graph.csv -B -W -o tmp >> detail_res-opt.txt
# ../../bin/mwis v3+v4/ingress_table_graph.csv -B -W -o tmp >> detail_res-opt.txt



# collect results

sed -n '/.\/v/p'  detail_res-opt.txt > sum_res-opt.txt

sed -n '/- best weight:/p'  detail_res-opt.txt >> sum_res-opt.txt

cat sum_res-opt.txt
cat sum_res-opt.txt | awk '{sum+=$4; if($4>0) cnt++ } END {print "Average solution = ", sum/cnt;}'
cat sum_res-opt.txt | awk '{sum+=$4; if($4>0) cnt++ } END {print "Average solution = ", sum/cnt;}' >> sum_res-opt.txt

sed -n '/- total processing time (s):/p'  detail_res-opt.txt >> sum_res-opt.txt
cat sum_res-opt.txt | awk '{sum+=$6; if($6>0) cnt++ } END {print "Average total time = ", sum/cnt;}'
cat sum_res-opt.txt | awk '{sum+=$6; if($6>0) cnt++ } END {print "Average total time = ", sum/cnt;}' >> sum_res-opt.txt

