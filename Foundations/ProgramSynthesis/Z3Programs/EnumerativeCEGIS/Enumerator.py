from Grammar import *
from z3 import *
from typing import Any, Sequence

class Enumerator:
    def __init__(self,var_name,var_z3,const_range=(-5,5)):
        self.const_range=const_range
        self.var_name=var_name
        self.var_z3=var_z3
        self.base_exprs=[VarExpr(var_name,var_z3)]+[ConstExpr(i) for i in range(const_range[0],const_range[1]+1)]
        self.base_conds=[ConstCond(True),ConstCond(False)]
        self.exprs_by_size={}
        self.conds_by_size={}
    
    def get_expr_example_results(self,expr:Expr,examples:list[int])->list[int]:
        return [expr.evaluate(x) for x in examples]
    
    def get_cond_example_results(self,cond:Cond,examples:list[int])->list[bool]:
        return [cond.evaluate(x) for x in examples]
    
    def get_expressions_by_size(self,size:int,examples:list[int])->Sequence[Expr]:
        self.exprs_by_size={}
        self.conds_by_size={}
        return self.enumerate_expressions(size,examples)
    
    def enumerate_expressions(self,size:int,examples:list[int])->Sequence[Expr]:
        if(size==1):
            return self.base_exprs
        
        list_of_exprs=[]        
        example_results=set()
        
        #Fill in expressions of smaller sizes
        for i in range(1,size-1):
            if(i not in self.exprs_by_size):
                self.exprs_by_size[i]=self.enumerate_expressions(i,examples)
        for i in range(1,size-2):
            if(i not in self.conds_by_size):
                 self.conds_by_size[i]=self.enumerate_conditions(i,examples)
            
        #Plus and Mult
        for l in range(1,size-1):
            for el in self.exprs_by_size[l]:
                for er in self.exprs_by_size[size-1-l]:
                    plus_expr=PlusExpr(el,er)
                    mult_expr=MultExpr(el,er)
                    cur_results=tuple(self.get_expr_example_results(plus_expr,examples))
                    if (cur_results not in example_results):
                        example_results.add(cur_results)
                        list_of_exprs.append(plus_expr)
                    cur_results=tuple(self.get_expr_example_results(mult_expr,examples))
                    if (cur_results not in example_results):
                        example_results.add(cur_results)
                        list_of_exprs.append(mult_expr)
        
        #Ite
        for c in range(1,size-2):
            for l in range(1,size-1-c):
                for el in self.exprs_by_size[l]:
                    for er in self.exprs_by_size[size-1-c-l]:
                        for cond in self.conds_by_size[c]:
                            ite_expr=IteExpr(cond,el,er)
                            cur_results=tuple(self.get_expr_example_results(ite_expr,examples))
                            if (cur_results not in example_results):
                                example_results.add(cur_results)
                                list_of_exprs.append(ite_expr)
                                
        return list_of_exprs

    def enumerate_conditions(self,size:int,examples:list[int])->Sequence[Cond]:
        if(size==1):
            return [ConstCond(True),ConstCond(False)]
        
        list_of_conds=[]
        example_results=set()
        
        #Fill in expressions of smaller sizes
        for i in range(1,size-1):
            if(i not in self.exprs_by_size):
                self.exprs_by_size[i]=self.enumerate_expressions(i,examples)
        for i in range(1,size):
            if(i not in self.conds_by_size):
                 self.conds_by_size[i]=self.enumerate_conditions(i,examples)
                 
        #Gt and Eq
        for l in range(1,size-1):
            for el in self.exprs_by_size[l]:
                for er in self.exprs_by_size[size-1-l]:
                    gt_cond=GtCond(el,er)
                    eq_cond=EqCond(el,er)
                    cur_results=tuple(self.get_cond_example_results(gt_cond,examples))
                    if (cur_results not in example_results):
                        example_results.add(cur_results)
                        list_of_conds.append(gt_cond)
                    cur_results=tuple(self.get_cond_example_results(eq_cond,examples))
                    if (cur_results not in example_results):
                        example_results.add(cur_results)
                        list_of_conds.append(eq_cond)
                        
        #And and Or
        for c in range(1,size-1):
            for cl in self.conds_by_size[c]:
                for cr in self.conds_by_size[size-1-c]:
                    and_cond=AndCond(cl,cr)
                    or_cond=OrCond(cl,cr)
                    cur_results=tuple(self.get_cond_example_results(and_cond,examples))
                    if (cur_results not in example_results):
                        example_results.add(cur_results)
                        list_of_conds.append(and_cond)
                    cur_results=tuple(self.get_cond_example_results(or_cond,examples))
                    if (cur_results not in example_results):
                        example_results.add(cur_results)
                        list_of_conds.append(or_cond)
        
        #Not
        for c in self.conds_by_size[size-1]:
            not_cond=NotCond(c)
            cur_results=tuple(self.get_cond_example_results(not_cond,examples))
            if (cur_results not in example_results):
                example_results.add(cur_results)
                list_of_conds.append(not_cond)
        
        return list_of_conds
