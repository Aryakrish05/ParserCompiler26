#include <core.p4>
#include <v1model.p4>
header h {
	bit<8>	v;
	bit<8>	dummy;
}

header p_a {
	bit<20>	d;
}

header p_b {
	bit<20>	d;
}

header p_c {
	bit<20>	d;
}

struct headers_t{
	h	h;
	p_a	a;
	p_b	b;
	p_c	c;
}

struct metadata_t { }
parser MyParser(packet_in pkt, out headers_t hdr,inout metadata_t meta, inout standard_metadata_t std){
	state start {
		pkt.extract(hdr.h);
		transition select(hdr.h.v) {
			4 &&& 7:	state_2;
			1 &&& 7:	state_3;
			2 &&& 7:	state_1;
			default:	reject;
		}
	}
	state state_1 {
		pkt.extract(hdr.b);
		transition select(hdr.b.d) {
			default:	accept;
		}
	}
	state state_2 {
		pkt.extract(hdr.c);
		transition select(hdr.c.d) {
			default:	accept;
		}
	}
	state state_3 {
		pkt.extract(hdr.a);
		transition select(hdr.a.d) {
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
        pkt.emit(hdr.h);
        pkt.emit(hdr.a);
        pkt.emit(hdr.b);
        pkt.emit(hdr.c);
    }
}

V1Switch(MyParser(),
         MyVerifyChecksum(),
         MyIngress(),
         MyEgress(),
         MyComputeChecksum(),
         MyDeparser()) main;

