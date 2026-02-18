from z3 import *

p=Bool('p')
q=Bool('q')
r=Bool('r')
solve(Implies(p,q),r==Not(q),Or(Not(p),r))

print(And(p,q,True))
print(simplify(And(p,q,True)))