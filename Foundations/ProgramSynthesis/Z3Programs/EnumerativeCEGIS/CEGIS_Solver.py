from z3 import *
from Grammar import *
from typing import Any, List, Sequence
from Enumerator import *

'''
for now, there is an issue for inconsistent specifications ---
need to fix'''

def check_results(expr:Expr,examples:list[int],results:list[int])->bool:
    for i in range(len(examples)):
        if(expr.evaluate(examples[i])!=results[i]):
            return False
    return True

#spec_func is a function that takes a z3 variable and returns a z3 expression representing the specification to satisfy
def solve(spec_func, initial_examples_with_results: List[tuple[int, int]], max_size=10, const_range=(-5,5),debug=False):
    
    examples=[tc[0] for tc in initial_examples_with_results]
    results=[tc[1] for tc in initial_examples_with_results]
    
    z3var=Int('x')
    spec=spec_func(z3var)
    enumerator=Enumerator('x',z3var,const_range=const_range)
    
    for size in range(1,max_size+1):
        if debug:
            print("Trying expressions of size=",size)
        iter_num=1
        max_iterations=100
        while iter_num<=max_iterations:
            if debug:
                print("Iteration number=",iter_num)
            candidates=enumerator.get_expressions_by_size(size,examples)
            if debug:
                print("Number of candidates after eliminating example equivalent expressions=",len(candidates))
            examples_valid_candidates=0
            for c in candidates:
                if(check_results(c,examples,results)):
                    examples_valid_candidates+=1
                    s=Solver()
                    s.add(c.to_z3()!=spec)
                    if(s.check()==sat):
                        m=s.model()
                        if m[z3var] is None or m.eval(spec) is None:
                            continue
                        new_example=m[z3var].as_long()
                        new_result=m.eval(spec).as_long()
                        examples.append(new_example)
                        results.append(new_result)
                    else:
                        print("Found solution!")
                        return c
            if debug:
                print("Number of candidates that satisfy all examples but are wrong=",examples_valid_candidates)
            if(examples_valid_candidates==0):
                break
            iter_num+=1
            
    print("No solution found up to size=",max_size," :(")  
    return None
