from genparser import *
from specgen import get_spec
from tabletograph import render_parse_graph
import argparse
import time

#TODO - add options for enabling optimisations via commandline
#first work on a convenient representation for conversion of table into p4 code
#(needed to check for correctness)
#also see how you would do state-merging and remapping of field numbers to fieldnames
#work on proof of generality
#also, look at heuristic stm generator

argument_parser = argparse.ArgumentParser(description="runner.py")
argument_parser.add_argument("--input",type=str,required=True,help="Input file")
argument_parser.add_argument("--max_states", type=int, default=5)
argument_parser.add_argument("--max_entries", type=int, default=5)
args = argument_parser.parse_args()

field_name_to_no_map,field_no_to_sizes_map,max_packet_size,default_phv,spec,constants = get_spec(args.input)

no_fields = len(field_name_to_no_map)

field_sizes = [field_no_to_sizes_map[i] for i in range(no_fields)]

max_num_states = args.max_states

max_num_entries = args.max_entries

max_field_size = max(field_no_to_sizes_map.values())

start=time.time()
print(constants)
print(field_name_to_no_map)
table_entries,default_field,default_next_state = find_stm(field_sizes,default_phv,spec,1,15,1,15,max_packet_size,max_field_size,debug=True,constant_synthesis=True,constants=constants)
end=time.time()
print(end-start)

field_names = [' ' for _ in range(no_fields)]
for k,v in field_name_to_no_map.items():
    field_names[v] = k
render_parse_graph(table_entries,default_field,default_next_state,field_names)