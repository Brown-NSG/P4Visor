# Copyright Brown University & Xi'an Jiaotong University
# 
# Licensed under the Apache License, Version 2.0 (the "License");
#
# Author: Peng Zheng
# Email:  zeepean@gmail.com
#

/***************************************************************
 * SP4 header
 ***************************************************************/

header_type shadow_tag_t {
    fields {
        shadow_id : 16;
        etherType : 16;
    }
}

header_type shadow_metadata_t {
    fields {
        shadow_bit : 16; // the flag to mark packets status: shadow status
    }
}


header_type ethernet_t {
    fields {
        dstAddr : 48;
        srcAddr : 48;
        etherType : 16;
    }
}


/***************************************************************
 * SP4 header and header instance
 ***************************************************************/

header shadow_tag_t shadow_tag;

metadata shadow_metadata_t shadow_metadata;


/***************************************************************
 * SP4 parser
 ***************************************************************/

#define ETHERTYPE_SHADOW 0x8100 //0x0fff


header ethernet_t ethernet;

parser start {
    return parse_ethernet;
}

parser parse_ethernet {
    extract(ethernet);
    return select(latest.etherType) {
        // ETHERTYPE_IPV4 : parse_ipv4;
        ETHERTYPE_SHADOW : parse_shadow_tag;
        default: ingress;
    }
}

parser parse_shadow_tag {
    extract(shadow_tag);
    return select(latest.etherType){
        // ZEEP NOTE: here is the place to add branch
        // ETHERTYPE_IPV4 : parse_ipv4;
        default: ingress;
    }
}


/***************************************************************
 * SP4 action
 ***************************************************************/
#define SHADOW_PROGRAM_ID 0x1
#define REAL_PROGRAM_ID 0
// ACTION: real -> shadow packet
action SP4_add_shadow_tag() {
    add_header(shadow_tag);
    modify_field(shadow_tag.etherType, ethernet.etherType);
    modify_field(shadow_metadata.shadow_bit, SHADOW_PROGRAM_ID);
    modify_field(ethernet.etherType, 0x8100);
}

// ACTION: shadow -> real packet
action SP4_remove_shadow_tag() {
    modify_field(ethernet.etherType, shadow_tag.etherType);
    modify_field(shadow_metadata.shadow_bit, REAL_PROGRAM_ID);
    remove_header(shadow_tag);
}

action goto_production_pipe() {
    no_op();
}

action goto_testing_pipe() {
    no_op();
}

/***************************************************************
 * SP4 traffic control table
 ***************************************************************/

/* This table used to mark specific real pkts to shadow pkts*/
table shadow_traffic_control {
    reads {
        ethernet.dstAddr : exact;
    }
    actions {
        SP4_add_shadow_tag;
        SP4_remove_shadow_tag;
        goto_testing_pipe;
        goto_production_pipe;
    }
    size: 16;
}



table egress_production_table {
    actions {
        goto_production_pipe;
    }
}

table egress_testing_table {
    actions {
        goto_testing_pipe;
    }
}

control ingress {
    apply(shadow_traffic_control); // todo fix it: add bit to handle resubmited packet
}

control egress {
    if (shadow_metadata.shadow_bit == SHADOW_PROGRAM_ID) {
        // shadow pipeline
        apply(egress_testing_table);
    }
    else {
        // testing pipeline
        apply(egress_production_table);
    }
}
