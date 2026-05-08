import math

from frontend.analyser import Exact, NotCompared, Info


def reduce_exact_size(field:Exact):
    field.new_size = math.ceil(math.log2(len(field.old_constants)+1)) + 1
    for i in range(len(field.new_constants)):
        field.new_constants[i] = i

def reduce_not_compared_size(field:NotCompared):
    field.new_size = 1

#drops not compared members which are not separate structs themselves
# it might be nice to maintain what is merged to what but truth is - i don't need that
# finally I will just end up extracting the entire struct together in P4

def drop_unused_members(info:Info):
    for phv_member in info.old_phv_members:
        is_anything_compared = False
        for (field,_) in info.old_struct_decls[info.old_phv_members[phv_member]]:
            if not isinstance(info.attr_to_info[(phv_member,field)],NotCompared):
                is_anything_compared = True
                break
        if(is_anything_compared):
            info.phvmem_new_contents[phv_member] = []
            for (field,_) in info.old_struct_decls[info.old_phv_members[phv_member]]:
                if not isinstance(info.attr_to_info[(phv_member,field)],NotCompared):
                    info.phvmem_new_contents[phv_member].append(field)
        else:
            assert(info.phvmem_new_contents[phv_member]!=[])
            info.phvmem_new_contents[phv_member] = [info.phvmem_new_contents[phv_member][0]]

def reduce_all_sizes(info:Info):
    for field in info.attr_to_info.values():
        if(isinstance(field,Exact)):
            reduce_exact_size(field)
        elif(isinstance(field,NotCompared)):
            reduce_not_compared_size(field)

def best_modifier(info):
    reduce_all_sizes(info)
    drop_unused_members(info)
    return info

def no_size_reduction_modifier(info):
    return info
