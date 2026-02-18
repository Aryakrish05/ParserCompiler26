from z3 import *
x=Real('x')
y=Real('y')
solve(x**2+y**2>3 , x**3+y<5)

set_option(precision=10)#used to set options

solve(x**2+y**2==3, x**3==2)

