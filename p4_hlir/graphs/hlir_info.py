# Copyright 2013-present Barefoot Networks, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import math
import pprint as pp
import p4_hlir.hlir.p4_tables as p4_tables
import p4_hlir.hlir.p4_headers as p4_headers
import p4_hlir.hlir.p4_imperatives as p4_imperatives
import p4_hlir.hlir.p4_stateful as p4_stateful
import p4_hlir.hlir.p4_expressions as p4_expressions


def match_field_info(table):
    """Given a p4_table, return a dict with the following keys:

        'table_name' (str) - name of the table

        'num_fields' (int) - number of fields in the table search key

        'total_field_width' (int) - total number of bits in all search
        key fields

        'field_name_widths' (list of (str, int)) - a list of tuples,
        where each tuple is a string describing the search key field,
        and an int with the width of that field in bits.  The string
        is often just hte name of the field, but also mentions the
        mask if one is specified, or 'valid(field)' if the match type
        is 'valid'."""
    if type(table) is p4_tables.p4_conditional_node:
        # TBD: It might be nice to return info about the fields used
        # in the evaluation of the condition node here.  For now
        # simply return 0.
        # print 'DBG|GRAPH|hlir_info|condition node:', table
        return {'table_name': table.name,
                'num_fields': 0,
                'total_field_width': 0,
                'field_names_widths': []}
    try:
        mfs = table.match_fields
    except AttributeError:
        print('type(table)=%s' % (type(table)))
        pp.pprint(table)
        raise
    fnames = []
    total_width = 0
    for mf in mfs:
        if isinstance(mf[0], p4_headers.p4_header_instance):
            # Then the match type had better be P4_MATCH_VALID, or else
            # it seems to violate the P4 spec from my reading.
            assert(mf[1] == p4_tables.p4_match_type.P4_MATCH_VALID)
            assert(mf[2] is None)
            # Whether a field is valid only needs 1 bit in the search key
            width = 1
            fname = "valid(%s)" % (mf[0].name)
        elif isinstance(mf[0], p4_headers.p4_field):
            fullwidth = mf[0].width
            if mf[2] is None:
                width = fullwidth
                fname = mf[0].name
            elif isinstance(mf[2], int) or isinstance(mf[2], long):
                # Then it is a mask width
                mask = mf[2]
                fullmask = (1 << fullwidth) - 1
                # All bits in the mask should be inside the field's width
                assert((mask & fullmask) == mask)
                # Count 1s in the binary representation of the mask.
                # Any bits that are 0 in the mask need not be sent to the
                # table as part of the search key.
                width = bin(mask).count('1')
                fname = "%s mask 0x%x" % (mf[0].name, mf[2])
            else:
                msg = ("Unexpected type %s for mf[2]=%s" % (type(mf[2]), mf[2]))
                raise ValueError(msg)
        else:
            msg = ("Unexpected type %s for arg %s" % (type(mf[0]), mf[0]))
            raise ValueError(msg)
        fnames.append((fname, width))
        total_width += width
    return {'table_name': table.name,
            'num_fields': len(mfs),
            'total_field_width': total_width,
            'field_names_widths': fnames}


def address_width(num_addressable_things):
    """For a table with `num_addressable_things` entries, return the
    minimum number of bits required to address each of those
    entries.
    """
    return int(math.ceil(math.log(num_addressable_things, 2)))


def num_action_type_bits(num_actions):
    """For a table with `num_actions` different actions that can be
    performed, return the number of bits to do a straightforward
    encoding of these as separate unique ids."""
    assert(num_actions >= 0)
    if num_actions == 0:
        return 0
    return int(math.ceil(math.log(num_actions, 2)))


def result_info(table):
    """Given a p4_table, return a dict with the following keys:

        'table_name' (str) - name of the table

        'result_width' (int) - total number of bits in one
        straightforward encoding of the result bits, with a single
        unique identifier with log_2(n) bits where n is the number of
        possible actions, plus the maximum size of result fields
        needed by any of those actions.

        'actions' (dict) - a sub-dict with string keys equal to the
        action names for the table, and values that are sub-sub-dicts
        with these keys:

            'signature' (list of str) - a list of argument names to
            the action block.

            'signature_widths' (list of int) - a list of argument
            widths in bits, in the same order as the names in the
            previous list.

            'total_width' (int) - sum of all widths in
            'signature_widths' list.
    """
    ret = {'table_name': table.name,
           'actions': {}}
    if type(table) is p4_tables.p4_conditional_node:
        # The 'result' of a condition node is 1 bit to represent
        # True/False.
        ret['num_actions'] = 1
        ret['result_width'] = 1
        return ret
    assert(isinstance(table.actions, list))
    max_width = 0
    for act in table.actions:
        if isinstance(act, p4_imperatives.p4_action):
            assert(isinstance(act.name, str))
            assert(isinstance(act.required_params, int))
            assert(isinstance(act.signature, list))
            assert(isinstance(act.signature_flags, dict))
            assert(isinstance(act.signature_widths, list))
            assert(len(act.signature_flags) == 0)
            assert(act.required_params == len(act.signature))
            assert(act.required_params == len(act.signature_widths))
            total_width = sum(act.signature_widths)
#            info = {'required_params': act.required_params,
            info = {'signature': act.signature,
                    'signature_widths': act.signature_widths,
                    'total_width': total_width}
            ret['actions'][act.name] = info
            if total_width > max_width:
                max_width = total_width
        else:
            msg = ("Unexpected type %s for act=%s" % (type(act), act))
            raise ValueError(msg)
    ret['num_actions'] = len(table.actions)
    # Don't worry about trying to absolutely minimize table width
    # using Huffman encoding of the action type, but a real optimized
    # implementation might want to do that.

    # Little nit-pick case I'd like to get somewhere close to correct,
    # but it may still be a little bit off.  Assume that if the search
    # key is _not empty_, then the result needs to include an
    # indication that a miss occurred, so that the processor can do
    # the miss action for the table.

    # If the search key is empty, then there is no way to have a hit
    # versus a miss.  I do not know if the P4 language allows multiple
    # actions in this case, but if so (because the 'default action'
    # for the table is configurable as any one of several actions at
    # run time), then handle that case.
    num_actions = ret['num_actions']
    search_key_width = match_field_info(table)['total_field_width']
    if search_key_width > 0:
        num_actions += 1
    ret['result_width'] = (num_action_type_bits(num_actions) +
                           max_width)
    return ret


def pure_action_table(table, match=None, result=None):
    """Return True if `table` is a 'pure action' table.
    'Pure action' tables are those created simply for their
    primitive action side effects.  They have 0 search key
    bits, and 0 result bits (i.e. only one possible kind of
    action, and that action has no parameters).

    It is not necessary to pass any values for the optional arguments
    `match` and `result`, but if you pass the corresponding
    return values of functions match_field_info and result_info, it
    may save a little bit of compute time."""
    if match is None:
        match = match_field_info(table)
    if result is None:
        result = result_info(table)
    if match['total_field_width'] == 0 and result['result_width'] == 0:
        return True
    return False


def header_instance_size_bytes(header_inst):
    assert(isinstance(header_inst, p4_headers.p4_header_instance))
    size_bits = 0
    for fld in header_inst.fields:
        assert(isinstance(fld, p4_headers.p4_field))
        size_bits += fld.width
    assert((size_bits % 8) == 0)
    return size_bits / 8


def field_list_info(fld_list):
    # TBD: Does not handle non-flat field lists.  Would be good to
    # generalize it to handle that case.
    assert(isinstance(fld_list, p4_headers.p4_field_list))
    ret = {'name': fld_list.name,
           'num_fields': 0,
           'width': 0,
           'widths': []}
    for fld in fld_list.fields:
        assert(isinstance(fld, p4_headers.p4_field))
        ret['num_fields'] += 1
        ret['width'] += fld.width
        ret['widths'].append(fld.width)
    return ret


def field_list_calc_info(fld_list_calc):
    assert(isinstance(fld_list_calc, p4_headers.p4_field_list_calculation))
    fld_lists = fld_list_calc.input
    ret = {'field_lists': fld_lists,
           'output_width': fld_list_calc.output_width,
           'num_fields': 0,
           'input_width': 0,
           'input_widths': []}
    for fld_list in fld_lists:
        tmp = field_list_info(fld_list)
        ret['num_fields'] += tmp['num_fields']
        ret['input_width'] += tmp['width']
        ret['input_widths'] += tmp['widths']
    return ret


def fld_width(arg):
    assert(isinstance(arg, p4_headers.p4_field))
    return arg.width


def val_width(arg, signature_widths, dest_width):
    assert(isinstance(arg, p4_imperatives.p4_signature_ref) or
           isinstance(arg, int) or
           isinstance(arg, long))
    if isinstance(arg, p4_imperatives.p4_signature_ref):
        return signature_widths[arg.idx]
    # Constant value should be coerced to dest_width
    return dest_width


def val_or_fld_width(arg, signature_widths, dest_width):
    assert(isinstance(arg, p4_headers.p4_field) or
           isinstance(arg, p4_imperatives.p4_signature_ref) or
           isinstance(arg, p4_expressions.p4_expression) or
           isinstance(arg, int) or
           isinstance(arg, long))
    if isinstance(arg, p4_headers.p4_field):
        return arg.width
    elif isinstance(arg, p4_imperatives.p4_signature_ref):
        return signature_widths[arg.idx]
    # Constant value should be coerced to dest_width
    return dest_width


# A dictionary defining abbreviations for P4 v1.0.3 primitive action
# names.  This allows them to be summarized more briefly.  There is
# some level of "Huffman coding" going on here by hand, based upon how
# often these are used in switch.p4.  modify_field is the most common
# by far, hence warranting a very short abbreviation.

primitive_action_abbreviations = {
    'add': 'add',
    'add_header': 'add_hdr',
    'add_to_field': 'add_fld',
    'bit_and': 'and',
    'bit_or': 'or',
    'bit_xor': 'xor',
    'bit_slc': 'bit_slc',      # Not in P4 standard.  Perhaps a Cisco-internal extension?
    'clone_egress_pkt_to_egress': 'clone_e2e',
    'clone_egress_pkt_to_ingress': 'clone_e2i',
    'clone_ingress_pkt_to_egress': 'clone_i2e',
    'clone_ingress_pkt_to_ingress': 'clone_i2i',
    'copy_header': 'cp_hdr',
    'count': 'count',
    'drop': 'drop',
    'execute_meter': 'meter',
    'generate_digest': 'digest',
    'modify_field': 'm',
    'modify_field_rng_uniform': 'm_rng',
    'modify_field_with_hash_based_offset': 'm_hash',
    'no_op': 'no_op',
    'pop': 'pop',
    'push': 'push',
    'recirculate': 'recirc',    # tbd
    'register_read': 'reg_rd',    # tbd
    'register_write': 'reg_wr',    # tbd
    'remove_header': 'rm_hdr',
    'resubmit': 'resub',    # tbd
    'shift_left': 'sh_lf',
    'shift_right': 'sh_rt',
    'subtract': 'sub',
    'subtract_from_field': 'sub_fld',
    'truncate': 'trunc',    # tbd
}


def action_info(table, tally=None, debug=False):
    """Given a p4_table, return a dict with the following keys:

        'table_name' (str) - name of the table

        'action_descriptions' (list) - a list, where each element is a
        list of strings.  Element `i` is a list of strings containing
        abbreviated descriptions for action `i` of the table.

        'num_actions' (int) - the number of actions the table has.

        'max_primitive_actions' (int) - the maximum number of
        primitive actions across all of the table's actions.
    """
    ret = {'table_name': table.name}
    if type(table) is p4_tables.p4_conditional_node:
        # TBD
        ret['num_actions'] = 0
        ret['action_descriptions'] = []
        return ret
    assert(isinstance(table.actions, list))
    if debug:
        print('dbg action_info table.name=%s # actions=%d'
              '' % (table.name, len(table.actions)))
    ret['num_actions'] = len(table.actions)
    act_descs = []
    actions_by_name = sorted(table.actions, key=lambda x: x.name)
    for act in actions_by_name:
        if not isinstance(act, p4_imperatives.p4_action):
            msg = ("Unexpected type %s for act=%s" % (type(act), act))
            raise ValueError(msg)
        assert(isinstance(act.name, str))
        assert(isinstance(act.flat_call_sequence, list))
        if debug:
            print('    act.name=%s # primitive actions=%d'
                  '' % (act.name, len(act.flat_call_sequence)))
        prim_act_descs = []
        for prim_act_call in act.flat_call_sequence:
            assert(isinstance(prim_act_call, tuple))
            assert(len(prim_act_call) == 3)

            # prim_act_call[0].name is the name of the primitive
            # action, e.g. modify_field

            # prim_act_call[1] is a list of arguments to the primitive
            # action

            # prim_act_call[2] is a list of tuples describing the
            # location in the 'action expansion tree' of the original
            # action act.name.  This is useful for knowing how
            # primitive actions nest inside of user-defined actions,
            # i.e. why is the primitive action in
            # act.flat_call_sequence?

            (prim_act_kind, args, call_loc) = prim_act_call
            assert(isinstance(prim_act_kind, p4_imperatives.p4_action))
            assert(isinstance(args, list))
            assert(isinstance(call_loc, list))
            if tally is not None:
                tally[prim_act_kind] += 1
            if debug:
                print('')
                print('        prim_act_kind %s num_args %d'
                      '' % (prim_act_kind.name, len(args)))
            i = 0
            for arg in args:
                if isinstance(arg, int) or isinstance(arg, long):
                    if debug:
                        print('        %d int value 0x%x'
                              '' % (i, arg))
                elif isinstance(arg, p4_headers.p4_field):
                    if debug:
                        print('        %d p4_field width %d name %s.%s'
                              '' % (i, arg.width, arg.instance.name, arg.name))
                elif isinstance(arg, p4_imperatives.p4_signature_ref):
                    if debug:
                        print('        %d p4_signature_ref width %d idx %s'
                              '' % (i, act.signature_widths[arg.idx],
                                    arg.idx))
                elif isinstance(arg, p4_headers.p4_header_instance):
                    if debug:
                        print('        %d p4_header_instance %s num_bytes %d'
                              '' % (i, arg.name,
                                    header_instance_size_bytes(arg)))
                elif isinstance(arg, p4_headers.p4_field_list_calculation):
                    tmp = field_list_calc_info(arg)
                    if debug:
                        print('        %d p4_field_list_calc'
                              ' num_flists %d 1st_flist %s'
                              ' num_fs %d input_width %d widths %s'
                              ' output_width %d'
                              '' % (i, len(tmp['field_lists']),
                                    tmp['field_lists'][0].name,
                                    tmp['num_fields'], tmp['input_width'],
                                    ','.join(map(str, tmp['input_widths'])),
                                    tmp['output_width']))
                elif isinstance(arg, p4_headers.p4_field_list):
                    tmp = field_list_info(arg)
                    if debug:
                        print('        %d p4_field_list %s num_fs %d width %d'
                              ' widths %s'
                              '' % (i, arg.name, tmp['num_fields'],
                                    tmp['width'],
                                    ','.join(map(str, tmp['widths']))))
                elif isinstance(arg, p4_stateful.p4_counter):
                    if debug:
                        print('        %d p4_counter name %s type %s'
                              '' % (i, arg.name, arg.type))
                elif isinstance(arg, p4_stateful.p4_meter):
                    if debug:
                        print('        %d p4_meter name %s type %s'
                              '' % (i, arg.name, arg.type))
                elif isinstance(arg, p4_stateful.p4_register):
                    if debug:
                        print('        %d p4_register name %s type %s'
                              '' % (i, arg.name, arg.type))
                elif isinstance(arg, p4_expressions.p4_expression):
                    if debug:
                        pp.pprint(arg.__dict__)
                        print('        DBG|HLIR_INFO|arg %d of primitive call %s has unhandled type %s'
                           '' % (i, prim_act_kind.name, type(arg)))                                      
                else:
                    pp.pprint(arg.__dict__)
                    msg = ('arg %d of primitive call %s has unhandled type %s'
                           '' % (i, prim_act_kind.name, type(arg)))
                    raise ValueError(msg)
                i += 1

            # Special case processing for modify_field, the most
            # common primitive action in many P4 programs.
            abbrev_name = primitive_action_abbreviations[prim_act_kind.name]
            short_desc = '(unk)'
            if prim_act_kind.name == 'modify_field':
                # TBD: Consider using different abbreviations for the
                # cases of the source is a constant, a field in the
                # table result, or another field of the packet.

                # TBD: Also whether the actions are conditioned on a
                # header being valid or not valid, or involve none of
                # those so that it always occurs 100% of the time,
                # regardless of packet header contents.
                # print 'DBG|GRAPH|hlir_info|ARGS|', len(args)
                pp.pprint(args[1])
                assert(len(args) == 2 or len(args) == 3)
                dest_width = fld_width(args[0])
                src_width = val_or_fld_width(args[1], act.signature_widths,
                                             dest_width)
                mask_width = None
                if len(args) == 3:
                    abbrev_name += 'msk'
                    mask_width = val_width(args[2], act.signature_widths,
                                           dest_width)
                    if dest_width == src_width and dest_width == mask_width:
                        short_desc = '%s%d' % (abbrev_name, dest_width)
                    else:
                        short_desc = '%s(%d,%d,%d)' % (abbrev_name, dest_width,
                                                       src_width, mask_width)
                else:
                    if dest_width == src_width:
                        short_desc = '%s%d' % (abbrev_name, dest_width)
                    else:
                        short_desc = '%s(%d,%d)' % (abbrev_name, dest_width,
                                                    src_width)
            elif (prim_act_kind.name == 'bit_and' or
                  prim_act_kind.name == 'bit_or' or
                  prim_act_kind.name == 'bit_xor' or
                  prim_act_kind.name == 'add' or
                  prim_act_kind.name == 'subtract' or
                  prim_act_kind.name == 'modify_field_rng_uniform' or
                  prim_act_kind.name == 'shift_left' or
                  prim_act_kind.name == 'shift_right'):
                assert(len(args) == 3)
                dest_width = fld_width(args[0])
                src_width1 = val_or_fld_width(args[1], act.signature_widths,
                                              dest_width)
                src_width2 = val_or_fld_width(args[2], act.signature_widths,
                                              dest_width)
                if dest_width == src_width1 and dest_width == src_width2:
                    short_desc = '%s(%d)' % (abbrev_name, dest_width)
                else:
                    short_desc = '%s(%d,%d,%d)' % (abbrev_name, dest_width,
                                                   src_width1, src_width2)
            elif (prim_act_kind.name == 'add_to_field' or
                  prim_act_kind.name == 'subtract_from_field'):
                assert(len(args) == 2)
                dest_width = fld_width(args[0])
                src_width = val_or_fld_width(args[1], act.signature_widths,
                                             dest_width)
                if dest_width == src_width:
                    short_desc = '%s(%d)' % (abbrev_name, dest_width)
                else:
                    short_desc = '%s(%d,%d)' % (abbrev_name, dest_width,
                                                src_width)
            elif (prim_act_kind.name == 'drop' or
                  prim_act_kind.name == 'no_op'):
                assert(len(args) == 0)
                short_desc = abbrev_name
            elif prim_act_kind.name == 'modify_field_with_hash_based_offset':
                assert(len(args) == 4)
                dest_width = fld_width(args[0])
                base_width = val_width(args[1], act.signature_widths,
                                       dest_width)
                tmp = field_list_calc_info(args[2])
                size_width = val_width(args[3], act.signature_widths,
                                       dest_width)
                short_desc = '%s(%d,%d,%d,%d,%s)' % (
                    abbrev_name, dest_width, base_width, size_width,
                    tmp['input_width'],
                    ' '.join(map(str, tmp['input_widths'])))
            elif (prim_act_kind.name == 'add_header' or
                  prim_act_kind.name == 'remove_header'):
                assert(len(args) == 1)
                hdr_num_bytes = header_instance_size_bytes(args[0])
                short_desc = '%s(%d)' % (abbrev_name, 8 * hdr_num_bytes)
            elif prim_act_kind.name == 'copy_header':
                assert(len(args) == 2)
                hdr_num_bytes0 = header_instance_size_bytes(args[0])
                hdr_num_bytes1 = header_instance_size_bytes(args[1])
                assert(hdr_num_bytes0 == hdr_num_bytes1)
                short_desc = '%s(%d)' % (abbrev_name, 8 * hdr_num_bytes0)
            elif (prim_act_kind.name == 'clone_egress_pkt_to_egress' or
                  prim_act_kind.name == 'clone_egress_pkt_to_ingress' or
                  prim_act_kind.name == 'clone_ingress_pkt_to_egress' or
                  prim_act_kind.name == 'clone_ingress_pkt_to_ingress'):
                assert(len(args) == 2)
                clone_spec_width = val_width(args[0], act.signature_widths,
                                             None)
                tmp = field_list_info(args[1])
                short_desc = '%s(%s)' % (abbrev_name,
                                         ','.join(map(str, tmp['widths'])))
            elif prim_act_kind.name == 'generate_digest':
                assert(len(args) == 2)
                receiver_width = val_width(args[0], act.signature_widths,
                                           None)
                tmp = field_list_info(args[1])
                short_desc = '%s(%s)' % (abbrev_name,
                                         ','.join(map(str, tmp['widths'])))
            elif (prim_act_kind.name == 'push' or
                  prim_act_kind.name == 'pop'):
                assert(len(args) == 2)
                hdr_num_bytes = header_instance_size_bytes(args[0])
                assert(isinstance(args[1], int))
                short_desc = '%s(%d,%d)' % (abbrev_name, hdr_num_bytes,
                                            args[1])
            elif prim_act_kind.name == 'count':
                assert(len(args) == 2)
                assert(isinstance(args[0], p4_stateful.p4_counter))
                counter_type = args[0].type
                counter_instance_count = args[0].instance_count
                if counter_instance_count < 1:
                    print('warning: p4_counter %s has instance_count %s.'
                          '  Behaving as if it is actually 1.'
                          '' % (args[0].name, args[0].instance_count))
                    counter_instance_count = 1
                counter_addr_width = address_width(counter_instance_count)
                # Note: P4 v1.0.3 spec says args[1] should be VAL
                # only, but primitives.json in p4-hlir code allows FLD
                # also, so I will allow it here as well.
                index_width = val_or_fld_width(args[1], act.signature_widths,
                                               counter_addr_width)
                # TBD: Would be good to include the type of counter in
                # short_desc, too (bytes, packets, or
                # packets_and_bytes)
                short_desc = '%s(%s,%s)' % (abbrev_name, str(index_width),
                                            str(counter_type))
            elif prim_act_kind.name == 'execute_meter':
                assert(len(args) == 3)
                assert(isinstance(args[0], p4_stateful.p4_meter))
                meter_type = args[0].type
                meter_instance_count = args[0].instance_count
                if meter_instance_count < 1:
                    print('warning: p4_meter %s has instance_count %s.'
                          '  Behaving as if it is actually 1.'
                          '' % (args[0].name, args[0].instance_count))
                    meter_instance_count = 1
                meter_addr_width = address_width(meter_instance_count)
                # Note: P4 v1.0.3 spec says args[1] should be VAL
                # only, but primitives.json in p4-hlir code allows FLD
                # also, so I will allow it here as well.
                index_width = val_or_fld_width(args[1], act.signature_widths,
                                               meter_addr_width)
                dest_width = fld_width(args[2])
                # TBD: Would be good to include the type of counter in
                # short_desc, too (bytes or packets)
                short_desc = '%s(%s,%s,%s)' % (abbrev_name, str(index_width),
                                               str(meter_type), str(dest_width))
            elif prim_act_kind.name == 'register_read':
                assert(len(args) == 3)
                dest_width = fld_width(args[0])
                assert(isinstance(args[1], p4_stateful.p4_register))
                register_data_width = args[1].width
                register_instance_count = args[1].instance_count
                if register_instance_count < 1:
                    print('warning: p4_register %s has instance_count %s.'
                          '  Behaving as if it is actually 1.'
                          '' % (args[1].name, args[1].instance_count))
                    register_instance_count = 1
                register_addr_width = address_width(register_instance_count)
                # Note: P4 v1.0.3 spec says args[2] should be VAL
                # only, but primitives.json in p4-hlir code allows FLD
                # also, so I will allow it here as well.
                index_width = val_or_fld_width(args[2], act.signature_widths,
                                               register_addr_width)
                short_desc = '%s(%s,%s,%s)' % (abbrev_name,
                                               str(dest_width),
                                               str(register_data_width),
                                               str(index_width))
            elif prim_act_kind.name == 'register_write':
                assert(len(args) == 3)
                assert(isinstance(args[0], p4_stateful.p4_register))
                register_data_width = args[0].width
                register_instance_count = args[0].instance_count
                if register_instance_count < 1:
                    print('warning: p4_register %s has instance_count %s.'
                          '  Behaving as if it is actually 1.'
                          '' % (args[0].name, args[0].instance_count))
                    register_instance_count = 1
                register_addr_width = address_width(register_instance_count)
                # Note: P4 v1.0.3 spec says args[1] should be VAL
                # only, but primitives.json in p4-hlir code allows FLD
                # also, so I will allow it here as well.
                index_width = val_or_fld_width(args[1], act.signature_widths,
                                               register_addr_width)
                src_width = val_or_fld_width(args[2], act.signature_widths,
                                             register_data_width)
                short_desc = '%s(%s,%s,%s)' % (abbrev_name,
                                            str(register_data_width),
                                            str(src_width),
                                            str(index_width))
            else:
                short_desc = '%s(%d unk args)' % (abbrev_name, len(args))

            assert(len(call_loc) >= 1)
            for action_nest_info in call_loc:
                assert(isinstance(action_nest_info, tuple))
                assert(len(action_nest_info) == 2)
                assert(isinstance(action_nest_info[0], p4_imperatives.p4_action))
                assert(isinstance(action_nest_info[1], int))
            prim_act_descs.append(short_desc)
        act_descs.append(prim_act_descs)
    ret['action_descriptions'] = act_descs
    if debug:
        print('table actions for: %s' % (ret['table_name']))
        for i in range(0, len(ret['action_descriptions'])):
            print('  %d %s' % (i, ' '.join(ret['action_descriptions'][i])))
        pp.pprint(ret)

    max_primitive_actions = 0
    for i in range(0, ret['num_actions']):
        num_primitive_actions = len(ret['action_descriptions'][i])
        if num_primitive_actions > max_primitive_actions:
            max_primitive_actions = num_primitive_actions
    ret['max_primitive_actions'] = max_primitive_actions

    return ret


def print_tally_of_primitive_actions(tally):
    # Including x.name in the sort key makes the order repeatable
    # across multiple runs.
    prim_act_kinds_by_most_used = sorted(tally.keys(),
                                         key=lambda x: [tally[x], x.name],
                                         reverse=True)
    print('# of primitive actions used in actions, from most to least often used:')
    n = 0
    for prim_act_kind in prim_act_kinds_by_most_used:
        n += tally[prim_act_kind]
    for prim_act_kind in prim_act_kinds_by_most_used:
        print('%4d %5.1f%% %-9s %s' % (
            tally[prim_act_kind],
            (100.0 * tally[prim_act_kind]) / n,
            primitive_action_abbreviations[prim_act_kind.name],
            prim_act_kind.name))
