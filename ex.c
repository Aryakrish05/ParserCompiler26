#define ACCEPT 1
#define REJECT 2

struct ethernet_t {
    unsigned char  dst[6];
    unsigned char  src[6];
    unsigned short ether_type;
};

struct ipv4_t { /* fields */ };
struct arp_t  { /* fields */ };

int process(unsigned char *ptr) {
    struct ethernet_t ethhdr;
    struct ipv4_t     ipv4;
    struct arp_t      arp;

    ethhdr = *((struct ethernet_t *)ptr);
    ptr   += sizeof(struct ethernet_t);

    if (ethhdr.ether_type == 0x0800) {
        ipv4 = *((struct ipv4_t *)ptr);
        ptr += sizeof(struct ipv4_t);
        /* further processing*/
        return ACCEPT;
    } else if (ethhdr.ether_type == 0x0806) {
        arp = *((struct arp_t *)ptr);
        ptr += sizeof(struct arp_t);
        return REJECT;
    }

    return ACCEPT;
}
