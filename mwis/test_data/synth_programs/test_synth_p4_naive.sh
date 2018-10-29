#!/bin/bash

casefolder_s="small"
casefolder_l="large"

echo ' '
echo "======naive greedy algorithm======="
echo ' '

function run_mwis_ng ()
{
  for file in `ls $1 -Sr`
  do
    if [ -d $1"/"$file ]
    then
      run_mwis_ng $1"/"$file
    else
      echo $1"/"$file >>  detail_res-naive.txt
      ../../bin/mwis $1"/"$file -N -o tmp>>  detail_res-naive.txt

   echo $1"/"$file
   fi
  done
}


rm detail_res-naive.txt
rm sum_res-naive.txt


# small graphs
run_mwis_ng $casefolder_s


# large graphs
run_mwis_ng $casefolder_l


# collect results
sed -n '/.\/n/p'  detail_res-naive.txt > sum_res-naive.txt

sed -n '/- best weight:/p'  detail_res-naive.txt >> sum_res-naive.txt
cat sum_res-naive.txt
cat sum_res-naive.txt | awk '{sum+=$4; if($4>0) cnt++ } END {print "Average solution = ", sum/cnt;}'
cat sum_res-naive.txt | awk '{sum+=$4; if($4>0) cnt++ } END {print "Average solution = ", sum/cnt;}' >> sum_res-naive.txt

sed -n '/- total processing time (s):/p'  detail_res-naive.txt >> sum_res-naive.txt
cat sum_res-naive.txt | awk '{sum+=$6; if($6>0) cnt++ } END {print "Average total time = ", sum/cnt;}'
cat sum_res-naive.txt | awk '{sum+=$6; if($6>0) cnt++ } END {print "Average total time = ", sum/cnt;}' >> sum_res-naive.txt

