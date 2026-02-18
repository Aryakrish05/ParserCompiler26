'''note that the expression 3/2 reduces to a python integer and not a 
z3 rational number - 
'''
from z3 import *
print(1/3)

###equivalent ways to create rational numbers in Z3py
print(RealVal(1)/3)
print(Q(1,3))

x=Real('x')
print(x+1/3)
print(x+Q(1,3))
print(x+"1/3")
print(x+0.25)

print("DISPLAY RATNOS AS DECIMAL")
set_option(rational_to_decimal=True)
solve(3*x==1)

set_option(precision=30)
solve(3*x==1)
