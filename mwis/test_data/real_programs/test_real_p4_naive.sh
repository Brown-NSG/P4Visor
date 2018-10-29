#!/bin/bash

echo ' '
echo "=====naive greedy algorithm===="
echo ' '

# clean file

rm detail_res-naive.txt
rm sum_res-naive.txt



# run egress graphs

echo './v1+v2/egress_table_graph' >> detail_res-naive.txt
../../bin/mwis v1+v2/egress_table_graph.csv -N -o tmp >> detail_res-naive.txt
echo './v1+v3/egress_table_graph' >> detail_res-naive.txt
../../bin/mwis v1+v3/egress_table_graph.csv -N -o tmp >> detail_res-naive.txt
echo './v1+v4/egress_table_graph' >> detail_res-naive.txt
../../bin/mwis v1+v4/egress_table_graph.csv -N -o tmp >> detail_res-naive.txt
echo './v2+v3/egress_table_graph' >> detail_res-naive.txt
../../bin/mwis v2+v3/egress_table_graph.csv -N -o tmp >> detail_res-naive.txt
echo './v2+v4/egress_table_graph' >> detail_res-naive.txt
../../bin/mwis v2+v4/egress_table_graph.csv -N -o tmp >> detail_res-naive.txt
echo './v3+v4/egress_table_graph' >> detail_res-naive.txt
../../bin/mwis v3+v4/egress_table_graph.csv -N -o tmp >> detail_res-naive.txt


# run ingress graphs 

echo './v1+v2/ingress_table_graph' >> detail_res-naive.txt
../../bin/mwis v1+v2/ingress_table_graph.csv -N -o tmp >> detail_res-naive.txt
echo './v1+v3/ingress_table_graph' >> detail_res-naive.txt
../../bin/mwis v1+v3/ingress_table_graph.csv -N -o tmp >> detail_res-naive.txt
echo './v1+v4/ingress_table_graph' >> detail_res-naive.txt
../../bin/mwis v1+v4/ingress_table_graph.csv -N -o tmp >> detail_res-naive.txt
echo './v2+v3/ingress_table_graph' >> detail_res-naive.txt
../../bin/mwis v2+v3/ingress_table_graph.csv -N -o tmp >> detail_res-naive.txt
echo './v2+v4/ingress_table_graph' >> detail_res-naive.txt
../../bin/mwis v2+v4/ingress_table_graph.csv -N -o tmp >> detail_res-naive.txt
echo './v3+v4/ingress_table_graph' >> detail_res-naive.txt
../../bin/mwis v3+v4/ingress_table_graph.csv -N -o tmp >> detail_res-naive.txt



# collect results

sed -n '/.\/v/p'  detail_res-naive.txt >> sum_res-naive.txt

sed -n '/- best weight:/p'  detail_res-naive.txt >> sum_res-naive.txt
cat sum_res-naive.txt
cat sum_res-naive.txt | awk '{sum+=$4; if($4>0) cnt++ } END {print "Average solution = ", sum/cnt;}'
cat sum_res-naive.txt | awk '{sum+=$4; if($4>0) cnt++ } END {print "Average solution = ", sum/cnt;}' >> sum_res-naive.txt

sed -n '/- total processing time (s):/p'  detail_res-naive.txt >> sum_res-naive.txt
cat sum_res-naive.txt | awk '{sum+=$6; if($6>0) cnt++ } END {print "Average total time = ", sum/cnt;}'
cat sum_res-naive.txt | awk '{sum+=$6; if($6>0) cnt++ } END {print "Average total time = ", sum/cnt;}' >> sum_res-naive.txt
