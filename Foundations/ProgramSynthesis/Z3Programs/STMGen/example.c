#include "extract.h"
#define ACCEPT 1
#define REJECT 2
struct ethernet{
    int src;
    int dst;
    short ethertype;
};
struct phv{
    struct ethernet ethhdr;
    struct ipv4 ipv41;
};
int parse(void* ptr){
    Extract(ethernet,ptr**);
    if(phv.ethernet.ethertype==1){

    }
    else{

    }
}