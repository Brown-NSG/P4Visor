
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
        recirculate_status : 8;
        meta_t : 16; // A-B Testing: shadow program meta
        meta_p: 16; // A-B Testing: real jprogram meta
    }
}


header_type intrinsic_metadata_t {
    fields {
        mcast_grp : 4;
        egress_rid : 4;
        mcast_hash : 16;
        lf_field_list : 32;
        resubmit_flag : 16;
        recirculate_flag : 8;
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
metadata intrinsic_metadata_t intrinsic_metadata;


field_list shadow_recirculate_meta {
    shadow_metadata;
    standard_metadata;
}


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

// #define ETHERTYPE_IPV4 0x0800
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


// A-B Testing tables


/* runnint at the end of production P4 program, performe recirculate */
action _recirculate_pkt() {
    modify_field(standard_metadata.instance_type, 3);
    recirculate(shadow_recirculate_meta);
}

table recirculate_table {
    actions {
        _recirculate_pkt;
    }
}



/* record running result of production P4 program */
action _rcd_production_result() {
    modify_field(shadow_metadata.meta_p, standard_metadata.egress_spec);
}

table record_production_result {
    actions {
        _rcd_production_result;
    }
}

/* record running result of shadow testing P4 program */
action _rcd_shadow_result() {
    modify_field(shadow_metadata.meta_t, standard_metadata.egress_spec);
}

table record_shadow_result {
    actions {
        _rcd_shadow_result;
    }
}

/* conparator */
/* send the pkt out to the controller*/
action _send_pkt_to_controller(port) {
    modify_field(standard_metadata.egress_spec, port);
}

action _tmp_handle_pkt(port) {
    modify_field(standard_metadata.egress_spec, port);
}

table handle_comparator_error {
    actions {
        _tmp_handle_pkt;
        _send_pkt_to_controller;
    }
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

    if (standard_metadata.instance_type == 0 )  {
        // apply(shadow_traffic_control);

        // 1-1 logic start of production P4 program
        // apply(ipv4_lpm);
        // apply(forward);  // logic end of production P4 program

        if (shadow_metadata.shadow_bit == SHADOW_PROGRAM_ID) {
            // 1-2 record result to metadata_field_p
            apply(record_production_result);

            // 1-3 recirculate the packet
            apply(recirculate_table);
        }
    }

    else {
        // 0-1 logic start of shadow P4 program
            //re-route the shadow flow
        // apply(ipv4_lpm_shadow);
        // apply(forward_shadow); // logic end of shadow P4 program

        // 0-2 record result to metadata_field_t
        apply(record_shadow_result);

        // 0-3 compare the result of TWO P4 programs
        //     here we can configure the compare fields
        if (shadow_metadata.meta_p != shadow_metadata.meta_t) {
            // NOT EQUAL: the shadow program goes wrong
            apply(handle_comparator_error);
        }
            // ELSE: the shadow program is right, nothing to do

    }


}

control egress {
    if (standard_metadata.instance_type == 1) {
        // shadow pipeline
        apply(egress_testing_table);
    }
    else {
        // testing pipeline
        apply(egress_production_table);
    }
}
