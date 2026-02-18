from z3 import *

HW = Int('HelloWorld')

s = Solver()

s.add(HW>6)

s.add(HW<8)

print(s.check())

m = s.model()

for i in m.decls():
    print("%s = %s" % (i.name(), m[i]))