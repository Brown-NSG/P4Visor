
## P4Visor Overview
P4Visor is a framework containing two primitives: building modular P4 programs by code merge and testing P4 programs with flexible operators. Specifically, the main features supported in the repository are shown below.

For merging P4 programs:
- P4Visor Compiler can merge two P4 programs to one fully automated. The merged P4 program allows the two P4 programs running side by side in single P4 target Bmv2. 
- P4Visor Management provides runtime messages translation between the control plane and the merged P4 Programs, and uses the ShadowConfiguration to determine how to appropriately modify the messages.

For testing operators:
- A-B testing operator. The traffic for A-B testing is configurable at runtime through flow entry in STC table. 
- Differential testing operator. Similar with A-B testing, traffic can be split across all versions and the output is compared, as described in the paper.

Besides, we will give a step-by-step guide to show the workflow of P4Visor and how to run real traffic on the it.

Note this is the preliminary prototype of P4Visor implementation. The code may changes in the future evolution.
The latest version of P4Visor can be found [https://github.com/Brown-NSG/P4Visor](https://github.com/Brown-NSG/P4Visor).

## 1. Merging P4 programs

### P4Visor merging interface
The following is the commands to merge two P4 program with notes to inputs:
```
usage: ShadowP4c-bmv2.py [-h] [--real_source source]
                         [--shadow_source SHADOW_SOURCE] [--json_s JSON_S]
                         [--json_mg JSON_MG] [--gen_dir GEN_DIR] [--json JSON]
                         [--gen-fig] [--version] [--primitives PRIMITIVES]

P4Visor compiler bmv2 (optional) arguments:
  -h, --help            show this help message and exit
  --real_source source  A source file to include in the P4 program.
  --shadow_source SHADOW_SOURCE
                        A shadow P4 program source file to merge.
  --json_s JSON_S       Dump the JSON representation to shadow P4 file.
  --json_mg JSON_MG     Dump the JSON representation to merged P4 file.
  --gen_dir GEN_DIR     The dir to store the generated graphs datas.
  --json JSON           Dump the JSON representation to production file.
  --gen-fig             The dir for the generated shadow configure files and graphs.
  --version, -v         show program's version number and exit
  --primitives PRIMITIVES
                        A JSON file which contains additional primitive
                        declarations
  --AB-testing           Merging for A-B Testing case
  --Diff-testing         Merging for Differential Testing case
```

The output is a JSON configuration for the P4 target bmv4 switch, as well as a configuration file `P4VisorConfigure` in the generated directory. 

PVM can translate the control messages, such as the flow entry add messages. More detail are in `PVM` directory.
<!-- 
For example, we can compile the A-B testing demo by the following command, the merged output json file for bmv2 is `switch_merged.json`:
```
python ShadowP4c-bmv2.py --real_source         cases/merge-simple-AB/switch_prod.p4 \
                         --shadow_source       cases/merge-simple-AB/switch_test.p4 \
                         --json_mg             cases/merge-simple-AB/switch_merged.json \
                         --gen_dir             cases/merge-simple-AB \
                         --AB-testing
```
#### Shadow configure management and agent
P4Visor compiler will generate a P4Visor configure file in the generated directory, name `P4VisorConfigure`. PVM can translate the control messages, such as the flow entry add messages. More detail are in `PVM` directory. -->


## 2. Supporting flexible testing operators
Operators can customize the testing configuration files to support flexible testing operations, which is described in section 6.2 of the submission. For A-B testing the file is `p4c_bm/SP4_metas_ab.p4` and for Differential testing the file is `p4c_bm/SP4_metas_diff.p4`. The following describes two key parts `Shadow Traffic Control` and `Comparator`.



### Shadow Traffic Control
The Shadow Traffic Control (STC) module is reconfigurable. We can set the match fields of the STC tables `shadow_traffic_control` for the shadow traffic classification. STC is used to manage the traffic for both both A-B testing and Differential testing. STC support four action current:

- Action `SP4_add_shadow_tag`: turn the production to testing traffic
- Action `SP4_remove_shadow_tag`: turn the testing traffic to production traffic
- Action `goto_testing_pipe`: send the packet to testing pipeline
- Action `goto_production_pipe`: send the packet to production pipeline

Each flow entry in STC table is associated with one action. All the traffic matched the flow will be processed by the action. The default match fields of the flow entry is dest mac address. Operators can custom the match fields in the file `SP_metas`, at line 104 `reads` fields, the following gives a example for the match fields:
```
    reads {
        ethernet.dstAddr : exact;
    }
```

By changing the flow entry in STC, operators can management the shadow traffic at run time. For example, the following command can guide all the packets matched to testing pipeline. 
```
table_add shadow_traffic_control goto_testing_pipe 00:04:00:00:00:01 =>
``` 

### Comparator

In Differential testing, at the end of the pipeline is the Comparator module, which can compare the output of testing version with the outputs of the production version. Operators can configure Comparator to report a message along with the packet with comparing outcomes to the controller if the values are not equal.

The comparator fields is reconfigurable through two actions in the meta file `p4c_bm/SP4_metas_diff.p4`. We can set any fields in packet header or metadata. The two actions to record the output of P4 programs are in the following.
```
/* record running result of production P4 program */
action _rcd_production_result() {
    modify_field(shadow_metadata.meta_p, standard_metadata.egress_spec);
}

/* record running result of shadow testing P4 program */
action _rcd_shadow_result() {
    modify_field(shadow_metadata.meta_t, standard_metadata.egress_spec);
}
```

<!-- ### Visualization merging
We can also generate the visible graph of merged parser and control flow using `--gen-fig` parameter. The figures will be generated in the specific directory. -->



## 3. Use case: a step-by-step guide to run Differential testing

In this section, we give a step-by-step guide to demonstrate how to perform Differential testing in mininet and bmv2. Note that the A-B testing operator has a similar workflow. We will also replay real traffic (in pcap file) on it to show the correctness of the merged programs.

- 3.0 Required dependencies

To fully evaluate the P4Visor building and testing primitives, several dependencies are required:
<!-- - [p4-hlir](https://github.com/p4lang/p4-hlir/blob/master/README.md) -->
    - [p4c-bm](https://github.com/p4lang/p4c-bm)
    - [bmv2](https://github.com/p4lang/behavioral-model)
    - [mininet](https://github.com/mininet/mininet)
    - tcpreply

Make sure that the bmv2 target are installed in the `/usr/local/bin/` so that mininet can find it. Note that all the scripts are tested with Ubuntu 16.04 LTS.


- 3.1 Merge two P4 programs

The following command example shows how to merge two P4 programs for Differential Testing:
```
python ShadowP4c-bmv2.py --real_source   cases/merge-DiffTesting/router_prod.p4 \
                        --shadow_source       cases/merge-DiffTesting/router_test.p4 \
                        --json                cases/merge-DiffTesting/router_prod.json \
                        --json_s              cases/merge-DiffTesting/router_test.json \
                        --json_mg             cases/merge-DiffTesting/router_merged.json \
                        --gen_dir             cases/merge-DiffTesting \
                        --gen-fig \
                        --Diff-testing
```
In this case, the production version is the simple router. The shadow traffic control and comparator use the default example configuration in `p4c_bm/SP4_metas_diff.p4` file.


- 3.2 Run the merged P4 program

We can get the merged json file for bmv2 in the `gen_dir`. We create a network topology with 1 switch and 4 connected hosts. Here is an example to run the merged program in mininet.
```
sudo python tools/create_1sw_mininet.py --behavioral-exe /usr/local/bin/simple_switch --num-host 4 --json cases/merge-DiffTesting/router_merged.json
```

- 3.3 Runtime populate production/testing tables

In the merged P4 program, there are three kinds of table can be configured through runtime CLI: 1) production program tables, 2) testing program tables and 3) shadow traffic control tables.

For the Differential testing case, we give three files in `cases/merge-DiffTesting` as the detailed examples of run-time configure commands.

`commands_prod.txt` : run-time example commands for production program

`commands_test.txt`: run-time example commands for testing program

`commands_STC.txt`: run-time example commands for shadow traffic control. 

Note that, as those entries are used for the single P4 programs before merging, operates should translate them into entries adapted for the merged P4 program before configuring them according to `P4VisorConfigure`. PVM can make it with:
```
python PVM/PVM_translate_cmd.py -cfg cases/merge-DiffTesting/P4VisorConfigure -c cases/merge-DiffTesting/commands_test.txt -n cases/merge-DiffTesting/commands_test_new.txt
```

Next we can install those new commands. 
```
sudo python tools/runtime_CLI.py < cases/merge-DiffTesting/commands_test_new.txt 
sudo python tools/runtime_CLI.py < cases/merge-DiffTesting/commands_prod.txt 
```
As a simple way to generate different behavior among production and testing programs, we cam install different flow entries (i.e., one will send out to port 1 while annother program to port 2) for the same flow (i.e., the flow with dstIP=10.0.0.10/32). At the same time, we configure the Comparetor to send the outputs to controller via a special port (i.e., port 3) when difference detected. As a result, we can observe the output of Differential testing.

- 3.4 Runtime configure STC tables and testing error handles
For the STC, we set packets with destination L2 address `00:04:00:00:00:01` to testing packets.
```
sudo python tools/runtime_CLI.py < cases/merge-DiffTesting/commands_STC.txt 
```

For the testing error handles, we can configure the `handle_comparator_error` table to forward the error packet to controller.


- 3.5 Tcpreply real traffic to the network

First open the xterm of the host/controller nodes connected to the ports of the switch in mininet CLI:
```
xterm h1 h2 h3
```

Second, we send testing traffic from `h1` to `h2` using tcpreply in xterm of `h1`:
```
tcpreplay -i eth0 cases/pcap/h1-h2_1.pcap
```


- 3.6 Detect the difference in real time
  
We can observe the differential outputs from the controller port in `h3`. We can observe the output packet using either wireshark or tcpdump as follows:
```
tcpdump -i eth0
```
If the production programs and testing has different output for the same packet, we can detect the output packet sent from the Comparator in switch.


## 4. Performance overhead evaluation
Given two P4 programs, we can merge them into one P4 program. We can run the programs before and after merged on Bmv2: 
```
sudo python tools/create_1sw_mininet.py --behavioral-exe /usr/local/bin/simple_switch --num-host 2 --json P4_programs.json
```
Then we can add the entries to the switch and test the throughput and latency using `iperf` tools. More detailed instructions will be available soon. Also feel free to test the overhead as you want.

## 5. Heuristic algorithm evaluation

More details and instructions are given in the file [mwis/README.md](mwis/README.md).

## To improve

- All the parser state of P4 programs should start from the start + parse_ethernet.
- Todo: test the action selector and action profile features.