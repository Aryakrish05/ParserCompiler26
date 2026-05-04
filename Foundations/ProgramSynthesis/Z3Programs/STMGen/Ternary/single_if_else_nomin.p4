#include <core.p4>
#include <v1model.p4>
header field0 {
	bit<4>	v;
}

header field1 {
	bit<4>	v;
}

header field2 {
	bit<4>	v;
}

header field3 {
	bit<4>	v;
}

struct headers_t{
	field0	field0;
	field1	field1;
	field2	field2;
	field3	field3;
}

struct metadata_t { }
parser MyParser(packet_in pkt, out headers_t hdr,inout metadata_t meta, inout standard_metadata_t std){
	state start {
		pkt.extract(hdr.field0);
		transition select(hdr.field0.v) {
			0 &&& 5:	state_3;
			default:	state_1;
		}
	}
	state state_1 {
		pkt.extract(hdr.field3);
		transition select(hdr.field3.v) {
			default:	state_2;
		}
	}
	state state_2 {
		pkt.extract(hdr.field2);
		transition select(hdr.field2.v) {
			default:	reject;
		}
	}
	state state_3 {
		pkt.extract(hdr.field1);
		transition select(hdr.field1.v) {
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
        pkt.emit(hdr.field0);
        pkt.emit(hdr.field1);
        pkt.emit(hdr.field2);
        pkt.emit(hdr.field3);
    }
}

V1Switch(MyParser(),
         MyVerifyChecksum(),
         MyIngress(),
         MyEgress(),
         MyComputeChecksum(),
         MyDeparser()) main;

