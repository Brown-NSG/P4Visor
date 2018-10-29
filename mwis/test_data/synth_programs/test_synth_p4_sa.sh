#!/bin/bash

casefolder_s="small"
casefolder_l="large"

function run_mwis_sa ()
{
  for file in `ls -Sr $1`
  do
    if [ -d $1"/"$file ]
    then
      run_mwis_sa $1"/"$file
    else
      echo $1"/"$file >>  detail_res-sa.txt
      ../../bin/mwis $1"/"$file -o tmp >>  detail_res-sa.txt

   echo $1"/"$file
   fi
  done
}

rm detail_res-sa.txt
rm sum_res-sa.txt



# small graphs

run_mwis_sa $casefolder_s



# large graphs

run_mwis_sa $casefolder_l


# collect results

sed -n '/.\/n/p'  detail_res-sa.txt > sum_res-sa.txt

sed -n '/- best weight:/p'  detail_res-sa.txt >> sum_res-sa.txt
cat sum_res-sa.txt
cat sum_res-sa.txt | awk '{sum+=$4; if($4>0) cnt++ } END {print "Average solution = ", sum/cnt;}'
cat sum_res-sa.txt | awk '{sum+=$4; if($4>0) cnt++ } END {print "Average solution = ", sum/cnt;}' >> sum_res-sa.txt

sed -n '/- total processing time (s):/p'  detail_res-sa.txt >> sum_res-sa.txt
cat sum_res-sa.txt | awk '{sum+=$6; if($6>0) cnt++ } END {print "Average total time = ", sum/cnt;}'
cat sum_res-sa.txt | awk '{sum+=$6; if($6>0) cnt++ } END {print "Average total time = ", sum/cnt;}' >> sum_res-sa.txt

