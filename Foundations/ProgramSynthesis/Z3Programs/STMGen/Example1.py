from genparser import *
from z3 import *

'''
Example 1:

Takes 25.5 seconds

Extract(field0)
if (field0==3){
    Extract(field1)
}
else if(field0==4){
    Extract(field2)
}
Extract(field3)
'''
field_sizes = [4,1,1,2]
initial_phv = [0,0,0,0]
def spec(packet):
    res=[]
    res.append(Extract(3,0,packet))
    res.append(If(Extract(3,0,packet)==3,ZeroExt(3,Extract(4,4,packet)),BitVecVal(initial_phv[1],4)))
    res.append(If(Extract(3,0,packet)==4,ZeroExt(3,Extract(4,4,packet)),BitVecVal(initial_phv[2],4)))
    res.append(If(And(Extract(3,0,packet)!=3 ,Extract(3,0,packet)!=4),ZeroExt(2,Extract(5,4,packet)),ZeroExt(2,Extract(6,5,packet))))
    return res

find_stm(field_sizes,initial_phv,spec,True,5,5,10,4,debug=True)