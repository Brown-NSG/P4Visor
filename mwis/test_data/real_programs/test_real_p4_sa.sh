#!/bin/bash

rm detail_res-sa.txt
rm sum_res-sa.txt

# run egress graphs
echo './v1+v2/egress_table_graph' >> detail_res-sa.txt
../../bin/mwis v1+v2/egress_table_graph.csv -o tmp >> detail_res-sa.txt
echo './v1+v3/egress_table_graph' >> detail_res-sa.txt
../../bin/mwis v1+v3/egress_table_graph.csv -o tmp >> detail_res-sa.txt
echo './v1+v4/egress_table_graph' >> detail_res-sa.txt
../../bin/mwis v1+v4/egress_table_graph.csv -o tmp >> detail_res-sa.txt
echo './v2+v3/egress_table_graph' >> detail_res-sa.txt
../../bin/mwis v2+v3/egress_table_graph.csv -o tmp >> detail_res-sa.txt
echo './v2+v4/egress_table_graph' >> detail_res-sa.txt
../../bin/mwis v2+v4/egress_table_graph.csv -o tmp >> detail_res-sa.txt
echo './v3+v4/egress_table_graph' >> detail_res-sa.txt
../../bin/mwis v3+v4/egress_table_graph.csv -o tmp >> detail_res-sa.txt

# run ingress graphs
echo './v1+v2/ingress_table_graph' >> detail_res-sa.txt
../../bin/mwis v1+v2/ingress_table_graph.csv -o tmp >> detail_res-sa.txt
echo './v1+v3/ingress_table_graph' >> detail_res-sa.txt
../../bin/mwis v1+v3/ingress_table_graph.csv -o tmp >> detail_res-sa.txt
echo './v1+v4/ingress_table_graph' >> detail_res-sa.txt
../../bin/mwis v1+v4/ingress_table_graph.csv -o tmp >> detail_res-sa.txt
echo './v2+v3/ingress_table_graph' >> detail_res-sa.txt
../../bin/mwis v2+v3/ingress_table_graph.csv -o tmp >> detail_res-sa.txt
echo './v2+v4/ingress_table_graph' >> detail_res-sa.txt
../../bin/mwis v2+v4/ingress_table_graph.csv -o tmp >> detail_res-sa.txt
echo './v3+v4/ingress_table_graph' >> detail_res-sa.txt
../../bin/mwis v3+v4/ingress_table_graph.csv -o tmp >> detail_res-sa.txt


# collect results

sed -n '/.\/v/p'  detail_res-sa.txt > sum_res-sa.txt

sed -n '/- best weight:/p'  detail_res-sa.txt >> sum_res-sa.txt
cat sum_res-sa.txt
cat sum_res-sa.txt | awk '{sum+=$4; if($4>0) cnt++ } END {print "Average solution = ", sum/cnt;}'
cat sum_res-sa.txt | awk '{sum+=$4; if($4>0) cnt++ } END {print "Average solution = ", sum/cnt;}' >> sum_res-sa.txt

sed -n '/- total processing time (s):/p'  detail_res-sa.txt >> sum_res-sa.txt
cat sum_res-sa.txt | awk '{sum+=$6; if($6>0) cnt++ } END {print "Average total time = ", sum/cnt;}'
cat sum_res-sa.txt | awk '{sum+=$6; if($6>0) cnt++ } END {print "Average total time = ", sum/cnt;}' >> sum_res-sa.txt

