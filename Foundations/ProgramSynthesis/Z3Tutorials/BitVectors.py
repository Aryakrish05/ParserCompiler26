from z3 import *

x=BitVec('x',16)
y=BitVec('y',16)

z=BitVecVal(100,16)

low_byte=BitVec('low_byte',4)

s=Solver()
s.add(x^y==100,low_byte==Extract(3,0,x))
print(s.check())


print ("z is",z)
m=s.model()
for i in m.decls():
    print(i,m[i])
    
a,b=BitVecs('a b',8)
c=BitVec('c',16)
s.add(c==Concat(a,b))

print(s.check())
m=s.model()
for i in m.decls():
    print(i,m[i])
    
p=Int('p')
q=Int('q')
r=BitVec('r',16)
s.add(Implies(p>=q,r==Extract(p,q,r)))

