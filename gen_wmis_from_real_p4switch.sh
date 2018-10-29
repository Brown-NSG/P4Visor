#!/bin/bash
function getTiming(){
    start=$1
    end=$2
 
    start_s=`echo $start | cut -d '.' -f 1`
    start_ns=`echo $start | cut -d '.' -f 2`
    end_s=`echo $end | cut -d '.' -f 1`
    end_ns=`echo $end | cut -d '.' -f 2`
 
    time_micro=$(( (10#$end_s-10#$start_s)*1000000 + (10#$end_ns/1000 - 10#$start_ns/1000) ))
    time_ms=`expr $time_micro/1000  | bc `
 
    # echo "$time_micro microseconds"
    echo "$time_ms ms"
}


# 01
begin_time=`date +%s.%N`
python ShadowP4c-bmv2.py --real_source  mwis/test_data/real_programs/p4src/p4switch_v1/switch.p4 \
                  --shadow_source       mwis/test_data/real_programs/p4src/p4switch_v2/switch.p4 \
                  --json                mwis/test_data/real_programs/v1+v2/prod.json \
                  --json_s              mwis/test_data/real_programs/v1+v2/test.json \
                  --json_mg             mwis/test_data/real_programs/v1+v2/merged.json \
                  --gen_dir             mwis/test_data/real_programs/v1+v2 \
                  --Diff-testing                   
end_time=`date +%s.%N`
getTiming $begin_time $end_time

# 02
begin_time=`date +%s.%N`
python ShadowP4c-bmv2.py --real_source  mwis/test_data/real_programs/p4src/p4switch_v1/switch.p4 \
                  --shadow_source       mwis/test_data/real_programs/p4src/p4switch_v3/switch.p4 \
                  --json                mwis/test_data/real_programs/v1+v3/prod.json \
                  --json_s              mwis/test_data/real_programs/v1+v3/test.json \
                  --json_mg             mwis/test_data/real_programs/v1+v3/merged.json \
                  --gen_dir             mwis/test_data/real_programs/v1+v3 \
                  --Diff-testing                   
end_time=`date +%s.%N`
getTiming $begin_time $end_time

# 03
begin_time=`date +%s.%N`
python ShadowP4c-bmv2.py --real_source  mwis/test_data/real_programs/p4src/p4switch_v1/switch.p4 \
                  --shadow_source       mwis/test_data/real_programs/p4src/p4switch_v4/switch.p4 \
                  --json                mwis/test_data/real_programs/v1+v4/prod.json \
                  --json_s              mwis/test_data/real_programs/v1+v4/test.json \
                  --json_mg             mwis/test_data/real_programs/v1+v4/merged.json \
                  --gen_dir             mwis/test_data/real_programs/v1+v4 \
                  --Diff-testing                   
end_time=`date +%s.%N`
getTiming $begin_time $end_time
# exit 0


# 04
begin_time=`date +%s.%N`
python ShadowP4c-bmv2.py --real_source  mwis/test_data/real_programs/p4src/p4switch_v2/switch.p4 \
                  --shadow_source       mwis/test_data/real_programs/p4src/p4switch_v3/switch.p4 \
                  --json                mwis/test_data/real_programs/v2+v3/prod.json \
                  --json_s              mwis/test_data/real_programs/v2+v3/test.json \
                  --json_mg             mwis/test_data/real_programs/v2+v3/merged.json \
                  --gen_dir             mwis/test_data/real_programs/v2+v3 \
                  --Diff-testing                   
end_time=`date +%s.%N`
getTiming $begin_time $end_time
# exit 0

# 05
begin_time=`date +%s.%N`
python ShadowP4c-bmv2.py --real_source  mwis/test_data/real_programs/p4src/p4switch_v2/switch.p4 \
                  --shadow_source       mwis/test_data/real_programs/p4src/p4switch_v4/switch.p4 \
                  --json                mwis/test_data/real_programs/v2+v4/prod.json \
                  --json_s              mwis/test_data/real_programs/v2+v4/test.json \
                  --json_mg             mwis/test_data/real_programs/v2+v4/merged.json \
                  --gen_dir             mwis/test_data/real_programs/v2+v4 \
                  --Diff-testing                   
end_time=`date +%s.%N`
getTiming $begin_time $end_time

# exit 0

# 06
begin_time=`date +%s.%N`
python ShadowP4c-bmv2.py --real_source  mwis/test_data/real_programs/p4src/p4switch_v3/switch.p4 \
                  --shadow_source       mwis/test_data/real_programs/p4src/p4switch_v4/switch.p4 \
                  --json                mwis/test_data/real_programs/v3+v4/prod.json \
                  --json_s              mwis/test_data/real_programs/v3+v4/test.json \
                  --json_mg             mwis/test_data/real_programs/v3+v4/merged.json \
                  --gen_dir             mwis/test_data/real_programs/v3+v4 \
                  --Diff-testing                   
end_time=`date +%s.%N`
getTiming $begin_time $end_time
# exit 0