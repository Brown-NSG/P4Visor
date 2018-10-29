#!/bin/bash

python ShadowP4c-bmv2.py --real_source   cases/merge-DiffTesting/router_prod.p4 \
                        --shadow_source       cases/merge-DiffTesting/router_test.p4 \
                        --json                cases/merge-DiffTesting/router_prod.json \
                        --json_s              cases/merge-DiffTesting/router_test.json \
                        --json_mg             cases/merge-DiffTesting/router_merged.json \
                        --gen_dir             cases/merge-DiffTesting \
                        --Diff-testing


sudo python tools/create_1sw_mininet.py --behavioral-exe /usr/local/bin/simple_switch --num-host 4 --json cases/merge-DiffTesting/router_merged.json


