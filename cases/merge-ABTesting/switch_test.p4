
/***************************************************************
 * SP4 header
 ***************************************************************/


header_type ethernet_t {
    fields {
        dstAddr : 48;
        srcAddr : 48;
        etherType : 16;
    }
}




/***************************************************************
 * SP4 parser
 ***************************************************************/

header ethernet_t ethernet;

parser start {
    return parse_ethernet;
}

parser parse_ethernet {
    extract(ethernet);
    return select(latest.etherType) {
        // ETHERTYPE_IPV4 : parse_ipv4;
        // ETHERTYPE_SHADOW : parse_shadow_tag;
        default: ingress;
    }
}


/***************************************************************
 * SP4 action
 ***************************************************************/

//extra
action set_eport(port) {
    modify_field(standard_metadata.egress_spec, port);
}

action _no_op() {
    no_op();
}

table shadow_dmac {
    reads {
        ethernet.dstAddr : exact;
    }
    actions {set_eport; _no_op;}
    size : 64;
}



action rewrite_mac(smac) {
    modify_field(ethernet.srcAddr, smac);
}

table shadow_send_frame {
    reads {
        standard_metadata.egress_spec: exact;
    }
    actions {
        rewrite_mac;
        _no_op;
    }
    size: 256;
}

control ingress {
    apply(shadow_dmac);
}

control egress {
    apply(shadow_send_frame);
}

