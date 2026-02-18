from z3 import *
x,y,z=Reals('x y z')
s=Solver()
s.add(x>1,y>1,x+y>3,z-x<10)
print(s.check())
m=s.model()
#basically a dictionary which maps variables to values in the model
#model is basically a satisfying assignment to the variables
print("x = %s" % m[x])


###decls is something like the list of declared elements
print ("traversing model...")
for d in m.decls():
    print ("%s = %s" % (d.name(), m[d]))