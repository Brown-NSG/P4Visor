#!/bin/bash

# cd ..
# make
# cd test_data

casefolder="small"

echo ' '
echo "======BK algorithm======="
echo ' '

function run_mwis_bk ()
{
  for file in `ls $1 -Sr`
  do
    if [ -d $1"/"$file ]
    then
      run_mwis_bk $1"/"$file
    else
      echo $1"/"$file >>  detail_res-opt.txt
      ../../bin/mwis $1"/"$file -B -W -o tmp >>  detail_res-opt.txt

   echo $1"/"$file
   fi
  done
}


# clean file 

rm detail_res-opt.txt
rm sum_res-opt.txt




# only run small graphs for the optimal algorithm

run_mwis_bk $casefolder



# collect results

sed -n '/.\/n/p'  detail_res-opt.txt > sum_res-opt.txt

sed -n '/- best weight:/p'  detail_res-opt.txt >> sum_res-opt.txt

cat sum_res-opt.txt
cat sum_res-opt.txt | awk '{sum+=$4; if($4>0) cnt++ } END {print "Average solution = ", sum/cnt;}'
cat sum_res-opt.txt | awk '{sum+=$4; if($4>0) cnt++ } END {print "Average solution = ", sum/cnt;}' >> sum_res-opt.txt

sed -n '/- total processing time (s):/p'  detail_res-opt.txt >> sum_res-opt.txt
cat sum_res-opt.txt | awk '{sum+=$6; if($6>0) cnt++ } END {print "Average total time = ", sum/cnt;}'
cat sum_res-opt.txt | awk '{sum+=$6; if($6>0) cnt++ } END {print "Average total time = ", sum/cnt;}' >> sum_res-opt.txt


