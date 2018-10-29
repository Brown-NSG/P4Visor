
# ShadowP4 managment (SPM) and agent (SPA) mudules
 
Translate the commands/messages of the P4 programs before merging to the new commands/messages for the merged P4 program

## Usage

You can get the following usage by `python SPM_translate_cmd.py --help`. 

```
usage: ShadowP4 management (SPM) [-h] --shadow-config-file SHADOW_CONFIG_FILE
                                 --commands COMMANDS_OLD --commands-new
                                 COMMANDS_NEW

optional arguments:
  -h, --help            show this help message and exit
  --shadow-config-file SHADOW_CONFIG_FILE, -cfg SHADOW_CONFIG_FILE
                        The generated shadow config file by SPC
  --commands COMMANDS_OLD, -c COMMANDS_OLD
                        The commands for programs before merging
  --commands-new COMMANDS_NEW, -n COMMANDS_NEW
                        The new commands for the merged program

```

## Example

A simple example:

```
python SPM_translate_cmd.py -cfg table_config.txt -c add_flow_s.cmd.txt -n transltated_add_flow_s.cmd.txt
```