#!/bin/bash

python SPM/SPM_translate_cmd.py -cfg cases/merge-DiffTesting/ShadowP4Configure -c cases/merge-DiffTesting/commands_test.txt -n cases/merge-DiffTesting/commands_test_new.txt


sudo python tools/runtime_CLI.py < cases/merge-DiffTesting/commands_STC.txt 
sudo python tools/runtime_CLI.py < cases/merge-DiffTesting/commands_test_new.txt
sudo python tools/runtime_CLI.py < cases/merge-DiffTesting/commands_prod.txt