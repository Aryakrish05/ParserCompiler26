from z3 import *
x=Int('x')
y=Int('y')
n=x+y>=3
print("num args: ",n.num_args())
print("children: ",n.children())
print(n.arg(0))
print(n.arg(1))
print("operator:",n.decl())
print("op name:",n.decl().name())