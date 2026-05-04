#include <core.p4>
#include <v1model.p4>
header struct1 {
	bit<8>	field0;
}

header struct2 {
	bit<32>	field1;
}

header struct3 {
	bit<32>	field2;
}

header struct4 {
	bit<32>	field3;
}

header struct5 {
	bit<32>	field4;
}

struct headers_t{
	struct1	struct1;
	struct2	struct2;
	struct3	struct3;
	struct4	struct4;
	struct5	struct5;
}

struct metadata_t { }
parser MyParser(packet_in pkt, out headers_t hdr,inout metadata_t meta, inout standard_metadata_t std){
	state start {
		pkt.extract(hdr.struct1);
		transition select(hdr.struct1.field0) {
			5 &&& 255:	state_1;
			2 &&& 3:	state_2;
			default:	state_5;
		}
	}
	state state_1 {
		pkt.extract(hdr.struct3);
		transition select(hdr.struct3.field2) {
			default:	state_4;
		}
	}
	state state_2 {
		pkt.extract(hdr.struct2);
		transition select(hdr.struct2.field1) {
			1 &&& 439:	state_4;
			default:	state_3;
		}
	}
	state state_3 {
		pkt.extract(hdr.struct3);
		transition select(hdr.struct3.field2) {
			default:	state_5;
		}
	}
	state state_4 {
		pkt.extract(hdr.struct4);
		transition select(hdr.struct4.field3) {
			default:	state_5;
		}
	}
	state state_5 {
		pkt.extract(hdr.struct5);
		transition select(hdr.struct5.field4) {
			default:	accept;
		}
	}
}

control MyVerifyChecksum(inout headers_t hdr, inout metadata_t meta) {
    apply { }
}

control MyIngress(inout headers_t hdr,
                  inout metadata_t meta,
                  inout standard_metadata_t std) {
    apply { }
}

control MyEgress(inout headers_t hdr,
                 inout metadata_t meta,
                 inout standard_metadata_t std) {
    apply { }
}

control MyComputeChecksum(inout headers_t hdr, inout metadata_t meta) {
    apply { }
}

control MyDeparser(packet_out pkt, in headers_t hdr) {
    apply {
        pkt.emit(hdr.struct1);
        pkt.emit(hdr.struct2);
        pkt.emit(hdr.struct3);
        pkt.emit(hdr.struct4);
        pkt.emit(hdr.struct5);
    }
}

V1Switch(MyParser(),
         MyVerifyChecksum(),
         MyIngress(),
         MyEgress(),
         MyComputeChecksum(),
         MyDeparser()) main;

