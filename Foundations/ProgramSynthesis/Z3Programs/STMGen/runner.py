from genparser import *
from specgen import get_spec
import argparse

#TODO - add options for enabling optimisations via commandline
#first work on a convenient representation for conversion of table into p4 code
#(needed to check for correctness)
#also see how you would do state-merging and remapping of field numbers to fieldnames

argument_parser = argparse.ArgumentParser(description="runner.py")
argument_parser.add_argument("--input",type=str,required=True,help="Input file")
argument_parser.add_argument("--max_states", type=int, default=5)
argument_parser.add_argument("--max_entries", type=int, default=5)
args = argument_parser.parse_args()

field_name_to_no_map,field_no_to_sizes_map,max_packet_size,default_phv,spec = get_spec(args.input)

no_fields = len(field_name_to_no_map)

field_sizes = [field_no_to_sizes_map[i] for i in range(no_fields)]

max_num_states = args.max_states

max_num_entries = args.max_entries

max_field_size = max(field_no_to_sizes_map.values())

find_stm(field_sizes,default_phv,spec,max_num_states,max_num_entries,max_packet_size,max_field_size,debug=True)

