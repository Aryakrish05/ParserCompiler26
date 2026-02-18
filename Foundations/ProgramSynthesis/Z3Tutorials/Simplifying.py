from z3 import *
x=Int('x')
y=Int('y')

print(simplify(x+y+2*x+3))
print(simplify(x<y+x+2))
print(simplify(And(x+1>=3,x**2+x**2+y**2+2>=5)))

x, y = Reals('x y')
# Put expression in sum-of-monomials form
t = simplify((x + y)**3, som=True)
print (t)
# Use power operator
t = simplify(t, mul_to_power=True)
print (t)
help_simplify()

x, y = Reals('x y')
# Using Z3 native option names
print (simplify(x == y + 2, ':arith-lhs', True))
# Using Z3Py option names
print (simplify(x == y + 2, arith_lhs=True))

print ("\nAll available options:")
help_simplify()