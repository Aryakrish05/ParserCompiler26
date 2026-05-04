#include <core.p4>
#include <v1model.p4>
header hdr1 {
	bit<8>	f0;
	bit<8>	f1;
}

header hdr2 {
	bit<8>	f0;
	bit<8>	f1;
	bit<8>	f2;
}

header hdr3 {
	bit<32>	f0;
}

header hdr4 {
	bit<32>	f0;
}

struct headers_t{
	hdr1	hdr1;
	hdr2	hdr2;
	hdr3	hdr3;
	hdr4	hdr4;
}

struct metadata_t { }
parser MyParser(packet_in pkt, out headers_t hdr,inout metadata_t meta, inout standard_metadata_t std){
	state start {
		pkt.extract(hdr.hdr1);
		transition select(hdr.hdr1.f0) {
			10:	state_2;
			15:	state_3;
			default:	state_1;
		}
	}
	state state_1 {
		pkt.extract(hdr.hdr2);
		transition select(hdr.hdr2.f0) {
			default:	state_5;
		}
	}
	state state_2 {
		pkt.extract(hdr.hdr2);
		transition select(hdr.hdr2.f0) {
			5:	state_4;
			default:	state_5;
		}
	}
	state state_3 {
		pkt.extract(hdr.hdr2);
		transition select(hdr.hdr2.f0) {
			2:	state_4;
			default:	state_5;
		}
	}
	state state_4 {
		pkt.extract(hdr.hdr3);
		transition select(hdr.hdr3.f0) {
			default:	state_6;
		}
	}
	state state_5 {
		pkt.extract(hdr.hdr3);
		transition select(hdr.hdr3.f0) {
			default:	accept;
		}
	}
	state state_6 {
		pkt.extract(hdr.hdr4);
		transition select(hdr.hdr4.f0) {
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
        pkt.emit(hdr.hdr1);
        pkt.emit(hdr.hdr2);
        pkt.emit(hdr.hdr3);
        pkt.emit(hdr.hdr4);
    }
}

V1Switch(MyParser(),
         MyVerifyChecksum(),
         MyIngress(),
         MyEgress(),
         MyComputeChecksum(),
         MyDeparser()) main;

