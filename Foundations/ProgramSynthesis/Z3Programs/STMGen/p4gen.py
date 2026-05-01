from frontend import Info

class State:
    def __init__(self):
        self.field_used = None #must be a (phv_member,field) pair
        self.is_extraction = False
        self.transitions = [] # A list of (mask_or_None,value,next_state)
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
    print_headers(info)
    phv_order = print_phv(info)
    print("struct metadata_t { }")
    print_parser(info,states)
    print_boiler_plate(phv_order)

if __name__ == "__main__":
    old_struct_decls = {
        "ethernet_t": [("dstAddr", 48), ("srcAddr", 48), ("etherType", 16)],
        "ipv4_t": [
            ("version", 4), ("ihl", 4), ("tos", 8), ("totalLen", 16),
            ("id", 16), ("flags", 3), ("fragOffset", 13), ("ttl", 8),
            ("protocol", 8), ("hdrChecksum", 16),
            ("srcAddr", 32), ("dstAddr", 32),
        ],
    }
    old_phv_members = {"eth": "ethernet_t", "ipv4": "ipv4_t"}

    # attr_to_info / phvmem_new_contents are unused by p4gen, pass empty stubs.
    info = Info({}, {}, old_phv_members, old_struct_decls)

    # state 0: start — extract eth, select on etherType
    s0 = State()
    s0.is_extraction = True
    s0.field_used = ("eth", "etherType")
    s0.transitions = [
        (None, 0x0800, 2),   # IPv4 -> state_2
        (0xF000, 0x8000, 3), # ternary example -> reject
        (None, None, 1),     # default -> accept
    ]

    # state 1: accept
    s1 = State(); s1.is_accept = True

    # state 2: extract ipv4, branch on version
    s2 = State()
    s2.is_extraction = True
    s2.field_used = ("ipv4", "version")
    s2.transitions = [
        (None, 4, 1),        # v4 -> accept
        (None, None, 3),     # default -> reject
    ]

    # state 3: reject
    s3 = State(); s3.is_reject = True

    emit_p4(info, [s0, s1, s2, s3])
