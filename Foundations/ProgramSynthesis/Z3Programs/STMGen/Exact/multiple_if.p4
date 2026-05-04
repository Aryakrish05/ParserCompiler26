#include <core.p4>
#include <v1model.p4>
header hdr0 {
	bit<16>	f0;
}

header hdr1 {
	bit<16>	f1;
}

header hdr2 {
	bit<16>	f2;
}

header hdr3 {
	bit<16>	f2;
}

header tail {
	bit<8>	f0;
	bit<16>	f1;
}

struct headers_t{
	hdr0	hdr0;
	tail	tail;
	hdr1	hdr1;
	hdr2	hdr2;
	hdr3	hdr3;
}

struct metadata_t { }
parser MyParser(packet_in pkt, out headers_t hdr,inout metadata_t meta, inout standard_metadata_t std){
	state start {
		pkt.extract(hdr.hdr0);
		transition select(hdr.hdr0.f0) {
			2:	state_1;
			default:	state_3;
		}
	}
	state state_1 {
		pkt.extract(hdr.hdr1);
		transition select(hdr.hdr1.f1) {
			default:	state_2;
		}
	}
	state state_2 {
		pkt.extract(hdr.hdr2);
		transition select(hdr.hdr2.f2) {
			default:	state_3;
		}
	}
	state state_3 {
		pkt.extract(hdr.hdr1);
		transition select(hdr.hdr1.f1) {
			3:	state_4;
			default:	state_5;
		}
	}
	state state_4 {
		pkt.extract(hdr.hdr3);
		transition select(hdr.hdr3.f2) {
			default:	state_5;
		}
	}
	state state_5 {
		pkt.extract(hdr.tail);
		transition select(hdr.tail.f0) {
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
        pkt.emit(hdr.hdr0);
        pkt.emit(hdr.tail);
        pkt.emit(hdr.hdr1);
        pkt.emit(hdr.hdr2);
        pkt.emit(hdr.hdr3);
    }
}

V1Switch(MyParser(),
         MyVerifyChecksum(),
         MyIngress(),
         MyEgress(),
         MyComputeChecksum(),
         MyDeparser()) main;

