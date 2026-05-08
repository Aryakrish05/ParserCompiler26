from z3 import *

from pathlib import Path
from pycparser import parse_file

from frontend.analyser import CompilationError
from frontend.field_minimiser import best_modifier, no_size_reduction_modifier
from frontend.ir_generator import compile_to_pc
from spec.cfg_builder import CFGGenerator


def get_spec(parser_filename, drop_uncompared, field_min=True):

    build_dir = Path('_build')
    build_dir.mkdir(exist_ok=True)
    pc_filename = str(build_dir / (Path(parser_filename).stem + '.pc'))
    modifier = best_modifier if field_min else no_size_reduction_modifier
    info = compile_to_pc(parser_filename, pc_filename, modifier=modifier)

    file_ast = parse_file(pc_filename)
    cfg_gen = CFGGenerator(info)
    res = cfg_gen.visit(file_ast)
    assert(res is not None)
    entry,constants,mask_constants,ternary_match = res

    selected_map = info.compared_field_nos if drop_uncompared else info.all_field_nos
    no_fields = len(selected_map)
    is_straight_line = (no_fields == 0)
    if is_straight_line:
        # No synthesis now :)
        max_field_size = 0
        cur_phv = []
        default_phv = []
        default_phv_padded = []
    else:
        max_field_size = max(info.get_new_size(attr) for attr in selected_map) + 1
        sentinel = BitVecVal(1<<(max_field_size-1), max_field_size)
        cur_phv             = [sentinel for _ in range(no_fields)]
        default_phv         = [sentinel for _ in range(no_fields)]
        default_phv_padded  = [sentinel for _ in range(no_fields)]

    if(ternary_match):
        mask_constants.append((1<<max_field_size)-1)

    # Reject when duplicate extracts are present on a path
    fields_extracted = [False]*len(info.all_field_nos)
    max_packet_size = entry.get_max_packet_size(0,fields_extracted,info,False)

    def spec(packet):
        res_phv,res_state = entry.make_spec(cur_phv,default_phv,0,info,drop_uncompared,max_field_size,packet)
        return res_phv,res_state

    return info,entry,max_packet_size,default_phv_padded,spec,list(set(constants)),list(set(mask_constants)),ternary_match,max_field_size,is_straight_line
