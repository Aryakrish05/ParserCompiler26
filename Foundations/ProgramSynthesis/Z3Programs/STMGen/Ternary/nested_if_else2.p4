#include <core.p4>
#include <v1model.p4>
header h0 {
	bit<4>	f0;
}

header h1 {
	bit<4>	f1;
}

header h2 {
	bit<4>	f2;
}

header h3 {
	bit<4>	f3;
}

struct headers_t{
	h0	h0;
	h1	h1;
	h2	h2;
	h3	h3;
}

struct metadata_t { }
parser MyParser(packet_in pkt, out headers_t hdr,inout metadata_t meta, inout standard_metadata_t std){
	state start {
		pkt.extract(hdr.h0);
		transition select(hdr.h0.f0) {
			4 &&& 6:	state_1;
			default:	accept;
		}
	}
	state state_1 {
		pkt.extract(hdr.h1);
		transition select(hdr.h1.f1) {
			default:	state_2;
		}
	}
	state state_2 {
		transition select(hdr.h0.f0) {
			8 &&& 11:	state_3;
			default:	accept;
		}
	}
	state state_3 {
		pkt.extract(hdr.h2);
		transition select(hdr.h2.f2) {
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
        pkt.emit(hdr.h0);
        pkt.emit(hdr.h1);
        pkt.emit(hdr.h2);
        pkt.emit(hdr.h3);
    }
}

V1Switch(MyParser(),
         MyVerifyChecksum(),
         MyIngress(),
         MyEgress(),
         MyComputeChecksum(),
         MyDeparser()) main;

