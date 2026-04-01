from genparser import find_stm
from z3 import *
'''
Takes 18 seconds

Example 2:
Extract(field0)
if (field0==2){
    Extract(field1)
}
Extract(field2)
Extract(field3)
'''
field_sizes=[4,1,1,2]
initial_phv=[0,0,0,0]

def spec(packet):
    res=[]
    res.append(Extract(3,0,packet))
    res.append(If(Extract(3,0,packet)==2,ZeroExt(3,Extract(4,4,packet)),BitVecVal(initial_phv[1],4)))
    res.append(If(Extract(3,0,packet)==2,ZeroExt(3,Extract(5,5,packet)),ZeroExt(3,Extract(4,4,packet))))
    res.append(If(Extract(3,0,packet)==2,ZeroExt(2,Extract(7,6,packet)),ZeroExt(2,Extract(6,5,packet))))
    return res

find_stm(field_sizes,initial_phv,spec,True,5,5,10,4,debug=True)