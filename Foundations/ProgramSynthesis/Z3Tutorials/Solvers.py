from z3 import *
x=Int('x')
y=Int('y')

s=Solver()
print(s)

s.add(x>10,y==x+2)
print("Checking for satisfiability...")
print(s.check())
#s.check is to check if a set of constraints are satisfiable
#prints sat if it's satisfiable

print("Create a new scope...")
s.push()
print(s)
s.add(y<11)
#used to add constraints ->say that constraints have been asserted in solver
print(s)
print("Checking solvability of new set of constraints")
print(s.check())
#prints unsat if it's unsatisfiable

print("Restoring state")
s.pop()
print(s)

###Each solver maintains a stack of assertions -> when we use push and pop

###Some problems cannot be solved
###Prints unknown in that case
x=Real('x')
s=Solver()
s.add(2**x==3)
print(s.check())