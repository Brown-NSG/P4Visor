#
# P4Visor managment (PVM) and agent (PVA)
# 
# Translate add_flow enties commands of the P4 programs before
# merging to the new commands for the merged P4 program
#


import argparse


def get_parser():    
    parser = argparse.ArgumentParser('P4Visor management (PVM)')

    parser.add_argument('--shadow-config-file', '-cfg', dest='shadow_config_file', type=str,
                         help='The generated shadow config file by PVC', required=True)
    parser.add_argument('--commands', '-c', dest='commands_old', type=str,
                         help='The commands for programs before merging', required=True)
    parser.add_argument('--commands-new', '-n', dest='commands_new', type=str,
                         help='The new commands for the merged program', required=True)

    return parser


def translate_all(cmd, dic):
    for i, j in dic.iteritems():
        cmd = cmd.replace(i, j)
    return cmd


def main():

    parser = get_parser()
    args, unparsed_args = parser.parse_known_args()


    shadow_config_file = args.shadow_config_file
    commands_old = args.commands_old
    commands_new = args.commands_new

    shadow_table_map = {}

    with open(shadow_config_file,'r') as file:
        for line in file:
            tb_raw, tb_merged = line.split()
            shadow_table_map[tb_raw] = tb_merged


    print shadow_table_map


    with open(commands_new, 'w') as new_file:
        with open(commands_old,'r') as file:
            for cmd in file:
                new_cmd = translate_all(cmd, shadow_table_map)
                new_file.write(new_cmd)


if __name__ == '__main__':
    main()