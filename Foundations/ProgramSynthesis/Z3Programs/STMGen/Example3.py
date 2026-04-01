from genparser import find_stm
from z3 import *
'''
Takes 3 seconds

Example 3:
Extract(field0)
if (field0==3){
    Extract(field1)
}
else{
    Extract(field1)
}
Extract(field2)
'''

field_sizes=[4,1,1]
initial_phv=[0,0,0]
def spec(packet):
    res=[]
    res.append(Extract(3,0,packet))
    res.append(If(Extract(3,0,packet)==3,ZeroExt(3,Extract(4,4,packet)),ZeroExt(3,Extract(4,4,packet))))
    res.append(ZeroExt(3,Extract(5,5,packet)))
    return res

find_stm(field_sizes,initial_phv,spec,True,10,10,10,4,debug=True)
