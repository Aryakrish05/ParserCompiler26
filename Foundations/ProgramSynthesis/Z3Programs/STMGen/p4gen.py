from frontend import Info

class State:
    def __init__(self):
        self.field_used = None #must be a (phv_member,field) pair
        self.is_extraction = False
        self.transitions = [] # A list of (mask_or_None,value,next_state),default transition if both are None
        self.is_accept = False
        self.is_reject = False

#LLM used for generating this function    
def print_boiler_plate(emit_headers=None):

    emit_headers = emit_headers or []

    if emit_headers:
        emit_lines = "\n".join(
            f"        pkt.emit(hdr.{h});" for h in emit_headers
        )
        deparser_body = f"apply {{\n{emit_lines}\n    }}"
    else:
        deparser_body = "apply { }"

    boilerplate = (
        "\n"
        "control MyVerifyChecksum(inout headers_t hdr, inout metadata_t meta) {\n"
        "    apply { }\n"
        "}\n"
        "\n"
        "control MyIngress(inout headers_t hdr,\n"
        "                  inout metadata_t meta,\n"
        "                  inout standard_metadata_t std) {\n"
        "    apply { }\n"
        "}\n"
        "\n"
        "control MyEgress(inout headers_t hdr,\n"
        "                 inout metadata_t meta,\n"
        "                 inout standard_metadata_t std) {\n"
        "    apply { }\n"
        "}\n"
        "\n"
        "control MyComputeChecksum(inout headers_t hdr, inout metadata_t meta) {\n"
        "    apply { }\n"
        "}\n"
        "\n"
        f"control MyDeparser(packet_out pkt, in headers_t hdr) {{\n"
        f"    {deparser_body}\n"
        f"}}\n"
        "\n"
        "V1Switch(MyParser(),\n"
        "         MyVerifyChecksum(),\n"
        "         MyIngress(),\n"
        "         MyEgress(),\n"
        "         MyComputeChecksum(),\n"
        "         MyDeparser()) main;\n"
    )

    print(boilerplate)

def print_headers(info:Info):
    for struct_name in info.old_struct_decls:
        print(f"header {struct_name}","{")
        for (field,width) in info.old_struct_decls[struct_name]:
            print(f"\tbit<{width}>\t{field};")
        print("}\n")
                 
def print_phv(info:Info):
    phv_order = []
    print("struct headers_t{")
    for header in info.old_phv_members:
        phv_order.append(header)
        print(f"\t{info.old_phv_members[header]}\t{header};")
    print("}\n")
    return phv_order

#called for all states but accept and reject
def print_state(state_no,states:list[State],names:dict[int,str]):
    state = states[state_no]
    print(f"\tstate {names[state_no]}","{")
    if state.field_used is not None:
        phv_member, field_name = state.field_used
        if state.is_extraction:
            print(f"\t\tpkt.extract(hdr.{phv_member});")
        print(f"\t\ttransition select(hdr.{phv_member}.{field_name})","{")
    else:
        assert(False)#must have some field associated with it - that's our design

    default_next = -1
    for (mask,value,next_no) in state.transitions:
        if(mask is None and value is None):
            default_next = next_no
        elif(mask is None):
            print(f"\t\t\t{value}:\t{names[next_no]};")
        else:
            print(f"\t\t\t{value} &&& {mask}:\t{names[next_no]};")
        
    assert(default_next!=-1)#must have a default next state
    print(f"\t\t\tdefault:\t{names[default_next]};")
    print("\t\t}")
    print("\t}")
        
def print_parser(info:Info,states:list[State]):
    #state 0 is the start state
    print("parser MyParser(packet_in pkt, out headers_t hdr,inout metadata_t meta, inout standard_metadata_t std){")
    names = {}
    names[0] = "start"
    for i in range(1,len(states)):
        if(states[i].is_accept):
            names[i] = "accept"
        elif(states[i].is_reject):
            names[i] = "reject"
        else:
            names[i] = f"state_{i}"
    for i in range(0,len(states)):
        if(states[i].is_accept or states[i].is_reject):
            continue
        print_state(i,states,names)
    print("}")
    
def emit_p4(info:Info,states:list[State]):
    print("#include <core.p4>")
    print("#include <v1model.p4>")
    print_headers(info)
    phv_order = print_phv(info)
    print("struct metadata_t { }")
    print_parser(info,states)
    print_boiler_plate(phv_order)
