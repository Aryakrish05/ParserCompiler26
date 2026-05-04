from genparser import *
from specgen import get_spec
from tabletograph import render_parse_graph
from stitch_back import (table_to_states, assign_extractions, enumerate_paths,
                         stitch_back, build_straight_line_states, render_states)
from p4gen import emit_p4
import argparse
import time
import sys
import contextlib
from pathlib import Path

argument_parser = argparse.ArgumentParser(description="runner.py")
argument_parser.add_argument("--input",type=str,required=True,help="Input .parser file")
argument_parser.add_argument("--output",type=str,default=None,help="Output .p4 file (default: <input>.p4)")
argument_parser.add_argument("--max_states", type=int, default=5)
argument_parser.add_argument("--max_entries", type=int, default=5)
argument_parser.add_argument("--min_states", type=int, default=1)
argument_parser.add_argument("--min_entries", type=int, default=0)
argument_parser.add_argument("--debug", type=str, default="OFF")
argument_parser.add_argument("--not_always_extract", type=str, default="OFF")
argument_parser.add_argument("--drop_uncompared", type=str, default="OFF")
argument_parser.add_argument("--constant_synthesis", type=str, default="ON")
argument_parser.add_argument("--field_min", type=str, default="ON")

args = argument_parser.parse_args()

if(args.not_always_extract=="ON" and args.drop_uncompared=="ON"):
    raise ValueError("You cannot drop uncompared fields when you are choosing the not_always_extract option")

if(args.drop_uncompared=="ON"):
    assert(args.not_always_extract=="OFF"), "stitch_back requires not_always_extract=OFF"

drop_uncompared = (args.drop_uncompared == "ON")
field_min = (args.field_min == "ON")
constant_synthesis = (args.constant_synthesis == "ON")
debug = (args.debug == "ON")
not_always_extract = (args.not_always_extract == "ON")

out_path = args.output if args.output is not None else str(Path(args.input).with_suffix('.p4'))

info,entry,max_packet_size,default_phv,spec,constants,mask_constants,ternary_match,max_field_size,is_straight_line = get_spec(args.input, drop_uncompared, field_min)

def write_p4(states):
    with open(out_path,'w') as f:
        with contextlib.redirect_stdout(f):
            emit_p4(info,states)

if(drop_uncompared and is_straight_line):
    states = build_straight_line_states(entry)
    assign_extractions(states)
    if(debug):
        render_states(states, output_name=f'stitched_{Path(args.input).stem}')
    write_p4(states)
    print(f"states=0",file=sys.stderr)
    print(f"entries=0",file=sys.stderr)
    print(f"time=0.0",file=sys.stderr)
    raise SystemExit(0)

selected_map = info.compared_field_nos if drop_uncompared else info.all_field_nos
no_fields = len(selected_map)
field_sizes = [None]*no_fields
field_names = [None]*no_fields
for attr,fno in selected_map.items():
    field_sizes[fno] = info.get_new_size(attr) if field_min else info.get_old_size(attr)
    field_names[fno] = info.get_cmpname(attr)

start = time.time()
table_entries,default_field,default_next_state = find_stm(
    field_sizes,default_phv,spec,
    args.min_states,args.max_states,args.min_entries,args.max_entries,
    max_packet_size,max_field_size,
    debug=debug,
    constant_synthesis=constant_synthesis,
    constants=constants,mask_constants=mask_constants,
    ternary_match=ternary_match,
    not_always_extract=not_always_extract)
elapsed = time.time() - start

states = table_to_states(table_entries, default_field, default_next_state,
                         info, drop_uncompared, ternary_match)

if(drop_uncompared):
    if ternary_match:
        if(debug):
            print('[stitch_back] skipped — ternary matches not supported')
    else:
        paths = enumerate_paths(entry)
        stitch_back(states, info, paths)

assign_extractions(states)

if(debug):
    render_parse_graph(table_entries,default_field,default_next_state,field_names,ternary_match)
    render_states(states, output_name=f'stitched_{Path(args.input).stem}')

write_p4(states)

print(f"states={len(default_field)}",file=sys.stderr)
print(f"entries={len(table_entries)}",file=sys.stderr)
print(f"time={elapsed:.4f}",file=sys.stderr)