from z3 import *
x=Int('x')#creates an integer variable in Z3 named x
y=Int('y')
solve(x>2,y<10,x+2*y==7)
#solves a system of constraints

print("Test for an unsatisfiable system of equations")
x=Real('x')
solve(x>4,x<0)

x=Real('x')
print(x**2+2*x+2)