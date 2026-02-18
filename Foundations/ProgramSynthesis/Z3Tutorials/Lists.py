from z3 import *
print([x+1 for x in range(5)])

X=[Int('x%s' % i) for i in range(5)]
Y=[Int('y%s' % i) for i in range(5)]
print(X)

X_plus_Y=[X[i]+Y[i] for i in range(5)]
print(X_plus_Y)

X_distinct=[Distinct(X[i] for i in range(5))]
print(X_distinct)

X =[[Int("x_%s_%s" % (i,j)) for j in range(5)]for i in range(5)]
print(X)
pp(X)