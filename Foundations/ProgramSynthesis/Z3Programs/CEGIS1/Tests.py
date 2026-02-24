from z3 import *
from Grammar import *
from typing import Any, Sequence
from CEGIS_Solver import solve

tests=[]
max_size=10
const_range=(-5,5)
debug=False

def test1(x):
    return x+5
tests.append((test1,[(0,5)],"x+5"))

def test2(x):
    return x*x+5*x+2
tests.append((test2,[(0,2)],"x*x+5*x+2"))

def test3(x):
    return If(x>0,x*x,x+5)
tests.append((test3,[(0,5)],"If(x>0,x*x,x+5)"))

def test4(x):
    return If(And(x>0,x<3),1,2)
tests.append((test4,[(0,2)],"If(And(x>0,x<3),1,2)"))

def test5(x):
    return 0
tests.append((test5,[(5,1),(-3,1)],"No Solution"))

def test6(x):
    return If(x>0,If(x<3,1,2),3)
tests.append((test6,[(0,3)],"If(x>0,If(x<3,1,2),3)"))

def test7(x):
    return If(Or(x>0,x<-3),1,2)
tests.append((test7,[(0,2)],"If(Or(x>0,x<-3),1,2)"))

for test in tests:
    if(test[2]=="No Solution"):
        print("Expected function: No solution")
        solve(test[0],test[1],5,const_range,debug)
    else:
        print("Expected function:",test[2])
        print("Synthesised function:",solve(test[0],test[1],max_size,const_range,debug))