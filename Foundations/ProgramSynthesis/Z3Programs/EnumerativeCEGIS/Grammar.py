from z3 import *
from typing import Any
'''
Describes an API for the AST for a simple grammar

Expr ::= VarExpr | ConstExpr | PlusExpr(Expr,Expr) | MultExpr(Expr,Expr) | IteExpr(Cond,Expr,Expr)
Cond ::= GtCond(Expr,Expr) | EqCond(Expr,Expr) | AndCond(Cond,Cond) | OrCond(Cond,Cond) | NotCond(Cond) | ConstCond

Only single variable expressions are supported for now, but it can be easily extended to multiple variables by making small changes
'''
class GenExp:
    def to_z3(self):
        raise NotImplementedError
    
    def size(self)->int:
        raise NotImplementedError
    
    def __str__(self):
        raise NotImplementedError
    
class Expr(GenExp):
    def evaluate(self,x_val:int)->int:
        raise NotImplementedError
    
class Cond(GenExp):
    def evaluate(self,x_val:int)->bool:
        raise NotImplementedError

class ConstExpr(Expr):
    def __init__(self,val:int):
        self.val=val
    
    def evaluate(self, x_val: int) -> int:
        return self.val
    
    def to_z3(self):
        return self.val
    
    def size(self):
        return 1
    
    def __str__(self):
        return str(self.val)
    
class VarExpr(Expr):
    def __init__(self,var,z3_var):
        self.var=var
        self.z3var=z3_var

    def evaluate(self,x_val:int)->int:
        return x_val
    
    def to_z3(self):
        return self.z3var
    
    def size(self)->int:
        return 1
    
    def __str__(self):
        return self.var 
    
class PlusExpr(Expr):
    def __init__(self,l:Expr,r:Expr):
        self.l=l
        self.r=r
        
    def evaluate(self,x_val:int)->int:
        return self.l.evaluate(x_val)+self.r.evaluate(x_val)
    
    def to_z3(self):
        return self.l.to_z3()+self.r.to_z3()
    
    def size(self)->int:
        return 1+self.l.size()+self.r.size()
    
    def __str__(self):
        return "("+str(self.l)+"+"+str(self.r)+")"
    
class MultExpr(Expr):
    def __init__(self,l:Expr,r:Expr):
        self.l=l
        self.r=r
        
    def evaluate(self,x_val:int)->int:
        return self.l.evaluate(x_val)*self.r.evaluate(x_val)
    
    def to_z3(self):
        return self.l.to_z3()*self.r.to_z3()
    
    def size(self)->int:
        return 1+self.l.size()+self.r.size()
    
    def __str__(self):
        return "("+str(self.l)+"*"+str(self.r)+")"
    
class IteExpr(Expr):
    def __init__(self,c:Cond,l:Expr,r:Expr):
        self.c=c
        self.l=l
        self.r=r
        
    def evaluate(self,x_val:int)->int:
        if(self.c.evaluate(x_val)):
            return self.l.evaluate(x_val)
        else:
            return self.r.evaluate(x_val)
    
    def to_z3(self):
        return If(self.c.to_z3(),self.l.to_z3(),self.r.to_z3())
    
    def size(self)->int:
        return 1+self.c.size()+self.l.size()+self.r.size()
    
    def __str__(self):
        return "If("+str(self.c)+","+str(self.l)+","+str(self.r)+")"

class GtCond(Cond):
    def __init__(self,l:Expr,r:Expr):
        self.l=l
        self.r=r
        
    def evaluate(self,x_val:int)->bool:
        return self.l.evaluate(x_val)>self.r.evaluate(x_val)
    
    def to_z3(self):
        return self.l.to_z3()>self.r.to_z3()
    
    def size(self)->int:
        return 1+self.l.size()+self.r.size()
    
    def __str__(self):
        return "("+str(self.l)+">"+str(self.r)+")"

class EqCond(Cond):
    def __init__(self,l:Expr,r:Expr):
        self.l=l
        self.r=r
        
    def evaluate(self,x_val:int)->bool:
        return self.l.evaluate(x_val)==self.r.evaluate(x_val)
    
    def to_z3(self):
        return self.l.to_z3()==self.r.to_z3()
    
    def size(self)->int:
        return 1+self.l.size()+self.r.size()
    
    def __str__(self):
        return "("+str(self.l)+"=="+str(self.r)+")"

class AndCond(Cond):
    def __init__(self,l:Cond,r:Cond):
        self.l=l
        self.r=r
        
    def evaluate(self,x_val:int)->bool:
        return self.l.evaluate(x_val) and self.r.evaluate(x_val)
    
    def to_z3(self):
        return z3.And(self.l.to_z3(),self.r.to_z3())
    
    def size(self)->int:
        return 1+self.l.size()+self.r.size()
    
    def __str__(self):
        return "("+str(self.l)+"&&"+str(self.r)+")"
    
class OrCond(Cond):
    def __init__(self,l:Cond,r:Cond):
        self.l=l
        self.r=r
        
    def evaluate(self,x_val:int)->bool:
        return self.l.evaluate(x_val) or self.r.evaluate(x_val)
    
    def to_z3(self):
        return z3.Or(self.l.to_z3(),self.r.to_z3())
    
    def size(self)->int:
        return 1+self.l.size()+self.r.size()
    
    def __str__(self):
        return "("+str(self.l)+"||"+str(self.r)+")"
    
class NotCond(Cond):
    def __init__(self,c:Cond):
        self.c=c
        
    def evaluate(self,x_val:int)->bool:
        return not self.c.evaluate(x_val)
    
    def to_z3(self):
        return z3.Not(self.c.to_z3())
    
    def size(self)->int:
        return 1+self.c.size()
    
    def __str__(self):
        return "!("+str(self.c)+")"

class ConstCond(Cond):
    def __init__(self,val:bool):
        self.val=val
        
    def evaluate(self,x_val:int)->bool:
        return self.val
    
    def to_z3(self):
        return self.val
    
    def size(self)->int:
        return 1
    
    def __str__(self):
        return str(self.val)
