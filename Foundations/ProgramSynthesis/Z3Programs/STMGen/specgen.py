'''
Constraints on Input -

*** Extract(fieldxxx,size) as the way to extract

[NOTE - the plan is to add support later for conversion into ptr+= and reading structs
now not constraining the field for comparison in a if-else chain shall help later
you could extract and then probably later compare against that field]

*** Only one function exists - contains any arguments (which we shall ignore) and any name
- but they must return an int

*** NOTE - Main assumption - no lookaheads (also makes sense tbh)
    [TODO - add support to statically detect this and throw an error, DONE!]

*** The only conditions are == or != conditions 
    [TODO - should be possible to add support for other types also ->
    but we'll do this later]

*** No other computation happens in the code (It's supposed to represent a parser after all!)

*** NOTE, the stm generator assumes that whatever was extracted last must be used for checking - TODO
see if we really need to enforce this condition - or this is general enough !?
. Give a rigorous proof or a counterexample
CFG nodes of the following types -

*** entry which is the start of the function

*** a single extraction(should contain field name and size extracted)

*** if-else statement -> instead of considering it as a branch (like a switch case)
(which it will reduce to in case we are matching on the same field), we split
an if-else if-...-else statement into multiple if-else branches , 
one thing is that it is easier to represent

[Only this will have a true/false next node -> both should not be null obviously!]

*** exit type which is a return statement - has two diff return values --- 
ACCEPT and REJECT

'''

from z3 import *

import pycparser.c_ast as ast
import copy
from pycparser import parse_file

#TODO - get rid of tuples and use dataclasses for better readability
#TODO - document how the flow of values happen in the design - need forc cur_phv

class CompilationError(Exception):
    pass
    
class CFGNode:
    
    def print(self,indent):
        raise NotImplementedError
    
    #call only after doing get_max_packet_size
    def make_spec(self,cur_phv,default_phv,ptr,field_no_to_sizes_map,max_field_size,packet):
        #cur_phv contains the expressions for the fields on the active path
        #default_phv contains the defaults - we just say all 0's for now, but user can choose
        #ptr contains the packet pointer till now
        #returns two things, a list of expressions for fields and an expression for ptr
        
        #NOTE that we shall tack on an ifthenelse condition when we have backtracked to a IfThenElse
        
        raise NotImplementedError

    def get_max_packet_size(self,ptr,fields_extracted,field_no_to_sizes_map):
        #fields_extracted contains if the field has been extracted on the current path
        raise NotImplementedError
    
class EntryNode(CFGNode):
    def __init__(self):
        self.next = None
    
    def print(self,indent=0):
        print(" "*indent,"Entry")
        assert(self.next is not None)
        self.next.print(indent+4)
    
    def make_spec(self, cur_phv, default_phv, ptr, field_no_to_sizes_map, max_field_size,packet):
        assert(self.next is not None)
        return self.next.make_spec(cur_phv,default_phv,ptr,field_no_to_sizes_map,max_field_size,packet)
        
    def get_max_packet_size(self, ptr, fields_extracted, field_no_to_sizes_map):
        assert(self.next is not None)
        return self.next.get_max_packet_size(ptr,fields_extracted,field_no_to_sizes_map)
    
class ExtractNode(CFGNode):
    def __init__(self,extract_field_no):
        self.extract_field_no = extract_field_no
        self.next = None
    
    def print(self,indent):
        print(" "*indent,f"Extract(field{self.extract_field_no})")
        assert(self.next is not None)
        self.next.print(indent+4)
        
    def get_max_packet_size(self,ptr,fields_extracted,field_no_to_sizes_map):
        if(fields_extracted[self.extract_field_no]):
            raise CompilationError("You must not extract the same field at two different places on the same path")
        
        assert(self.next is not None)
        fields_extracted[self.extract_field_no] = True
        max_ptr_next = self.next.get_max_packet_size(ptr+field_no_to_sizes_map[self.extract_field_no],fields_extracted,field_no_to_sizes_map)
        fields_extracted[self.extract_field_no] = False
        return max_ptr_next
        
    def make_spec(self, cur_phv, default_phv, ptr, field_no_to_sizes_map, max_field_size,packet):
        #no need to take backup here as i am the first person to modify, just reset the cur_phv value to default_phv -> or lite doesn't matter
        
        cur_field_sz = field_no_to_sizes_map[self.extract_field_no]
        #cur_phv[self.extract_field_no] = ZeroExt(max_field_size-cur_field_sz,Extract(ptr+cur_field_sz-1,ptr,packet))
        cur_phv[self.extract_field_no] = Extract(ptr+cur_field_sz-1,ptr,packet)
        assert(self.next is not None)
        res_phv,res_state = self.next.make_spec(cur_phv,default_phv,ptr+cur_field_sz,field_no_to_sizes_map,max_field_size,packet)
        #res_phv[self.extract_field_no] = ZeroExt(max_field_size-cur_field_sz,Extract(ptr+cur_field_sz-1,ptr,packet))
        res_phv[self.extract_field_no] = Extract(ptr+cur_field_sz-1,ptr,packet)
        return (res_phv,res_state)

class IfThenElseNode(CFGNode):
    def __init__(self,check_field_no,equality_value):
        self.check_field_no = check_field_no
        self.value = equality_value
        self.next_true = None
        self.next_false = None
    
    def print(self,indent):
        print(" "*indent,f"If(field{self.check_field_no}=={self.value})")
        assert(self.next_true is not None)
        print(" "*indent,"IfTrue:")
        self.next_true.print(indent+4)
        assert(self.next_false is not None)
        print(" "*indent,"IfFalse:")
        self.next_false.print(indent+4)
        
    def get_max_packet_size(self, ptr, fields_extracted, field_no_to_sizes_map):
        if(not fields_extracted[self.check_field_no]):
            raise CompilationError("You must extract a field before checking on it in all possible paths")
        
        assert(self.next_true is not None)
        true_max_ptr = self.next_true.get_max_packet_size(ptr,fields_extracted,field_no_to_sizes_map)
        
        assert(self.next_false is not None)
        false_max_ptr = self.next_false.get_max_packet_size(ptr,fields_extracted,field_no_to_sizes_map)
        
        return max(true_max_ptr,false_max_ptr)
        
    def make_spec(self, cur_phv, default_phv, ptr, field_no_to_sizes_map, max_field_size, packet):
        
        
        assert(self.next_true is not None)
        true_res_phv,true_res_state = self.next_true.make_spec(cur_phv,default_phv,ptr,field_no_to_sizes_map,max_field_size,packet)
        assert(self.next_false is not None)
        false_res_phv,false_res_state = self.next_false.make_spec(cur_phv,default_phv,ptr,field_no_to_sizes_map,max_field_size,packet)
        
        res_phv = []
        for i in range(len(true_res_phv)):
            res_phv.append(If(cur_phv[self.check_field_no]==self.value,true_res_phv[i],false_res_phv[i]))
        res_state = If(cur_phv[self.check_field_no]==self.value,true_res_state,false_res_state)

        return (res_phv,res_state)
    
class ExitNode(CFGNode):
    def __init__(self,exit_type):
        if(exit_type=="ACCEPT"):
            self.accept_or_reject = True
        else:
            self.accept_or_reject = False
    
    def print(self,indent):
        print(" "*indent,"ACCEPT" if self.accept_or_reject else "REJECT")
        
    def get_max_packet_size(self, ptr, fields_extracted, field_no_to_sizes_map):
        return ptr
        
    def make_spec(self, cur_phv, default_phv, ptr,field_no_to_sizes_map, max_field_size, packet):
        return (copy.deepcopy(default_phv),self.accept_or_reject)

class CFGGenerator(ast.NodeVisitor):
    def __init__(self) -> None:
        super().__init__()
        self.field_name_to_no_map = {}
        self.field_no_to_sizes_map = {}
        self.constants = []
        self.max_fields = 0
        
    def generic_visit(self, node: ast.Node):
        raise CompilationError("The code doesn't adhere to the specification, use only allowed constructs")
    
    def visit_Constant(self,n:ast.Constant):
        return int(n.value)

    def visit_ID(self,n:ast.ID):
        return n.name
    
    def visit_ExprList(self,n:ast.ExprList):
        if(len(n.exprs)!=2):
            raise CompilationError("Extract requires exactly 2 arguments, field to be extracted and its size")
        
        if(not isinstance(n.exprs[0],ast.ID)):
            raise CompilationError("Extract's first argument must be field name, an Identifier")
        
        if(not isinstance(n.exprs[1],ast.Constant)):
            raise CompilationError("Extract's second argument must be the field size, an Integer constant")
        
        return (self.visit(n.exprs[0]),self.visit(n.exprs[1]))
    
    def visit_FuncCall(self,n:ast.FuncCall):
        
        if(n.name.name!='Extract' or n.args is None):
            raise CompilationError("Calls to functions other than Extract not permitted")
        
        args = self.visit(n.args)
        
        assert(isinstance(args,tuple))
                
        if (args[0] not in self.field_name_to_no_map):
            self.field_name_to_no_map[args[0]] = self.max_fields
            self.max_fields += 1
        
        field_no = self.field_name_to_no_map[args[0]]
        
        if(args[1] <= 0):
            raise CompilationError("Size of a field must be +ve")
        
        if(field_no in self.field_no_to_sizes_map and self.field_no_to_sizes_map[field_no]!=args[1]):
            raise CompilationError("A given field must have a unique fixed size")
        
        self.field_no_to_sizes_map[field_no] = args[1]
        
        extraction_node = ExtractNode(field_no)
        
        return (extraction_node,[(extraction_node,"next")])
    
    
    def visit_FuncDef(self,n:ast.FuncDef):
        
        entry_node = EntryNode()
        next = self.visit(n.body)
        
        if(next is None):
            raise CompilationError("Can't have an empty function which does nothing")
        
        if (next[1]!=[]):
            raise CompilationError("Not all paths return a final state")
        
        entry_node.next = next[0]
        
        return entry_node
            
    
    def visit_If(self,n:ast.If):
        
        if(not isinstance(n.cond,ast.BinaryOp)):
            raise CompilationError("Only Binary comparisons of identifier and constant allowed as if condition")
        
        condition = self.visit(n.cond)
        next_true = self.visit(n.iftrue)
        
        next_false = None
        if(n.iffalse is not None):
            next_false = self.visit(n.iffalse)
        
        if(condition is None):
            raise ValueError("Something wrong with visit_BinaryOp")
        
        if(condition[0]=="!="):
            next_false,next_true = next_true,next_false
        
        if(condition[1] not in self.field_name_to_no_map):
            #should be runtime error - but
            raise CompilationError("You must extract a field before checking on it in all possible paths")
        
        if_node = IfThenElseNode(self.field_name_to_no_map[condition[1]],condition[2])
        self.constants.append(condition[2])
        end_nodes = []
        if(next_true is not None):
            if_node.next_true = next_true[0]
            end_nodes = next_true[1]
        else:
            end_nodes = [(if_node,"next_true")]
            
        if(next_false is not None):
            if_node.next_false = next_false[0]
            end_nodes.extend(next_false[1])
        else:
            end_nodes.append((if_node,"next_false"))
        
        if(next_false is None and next_true is None):
            return None
        
        return (if_node,end_nodes)
    
    def visit_BinaryOp(self,n:ast.BinaryOp):
        
        if(n.op not in ["==","!="]):
            raise CompilationError("Only comparison operations supported are == and !=")
        
        if(not isinstance(n.left,ast.ID)):
            raise CompilationError("Left side of an operator must be an Identifier")
            #it might be possible that this ID is something else, we shall check if it is extracted while walking on the CFG
        
        if(not isinstance(n.right,ast.Constant)):
            raise CompilationError("Right side of an operator must be a Constant")

        condition_field = self.visit(n.left)
        condition_value = self.visit(n.right)
        
        if (condition_value is not None and condition_value<0):
            raise CompilationError("The comparison value must be positive")
            
        return (n.op,condition_field,condition_value)
    
    def visit_Compound(self,n:ast.Compound):
        #silently skips dead code, it doesn't chain it to the main CFG
        at_least_one_stmt = False
        start = None
        end = []
        if(n.block_items is None):
            return None
        for x in n.block_items:
            if(not isinstance(x,ast.If) and not isinstance(x,ast.FuncCall) and not isinstance(x,ast.Return)):
                raise CompilationError("In a block, you can have only extracts,if-statements and returns")
            res_x_visit = self.visit(x)
            if(res_x_visit is not None):
                if(not at_least_one_stmt):
                    at_least_one_stmt = True
                    start = res_x_visit[0]
                    end = res_x_visit[1]
                else:
                    for (node,ptr) in end:
                        setattr(node,ptr,res_x_visit[0])
                    end = res_x_visit[1]
        if(at_least_one_stmt):
            return (start,end)
        else:
            return None 
        
    def visit_Return(self,n:ast.Return):
        ret_type = self.visit(n.expr)
        if(isinstance(n.expr,ast.ID) and ret_type in ["ACCEPT","REJECT"]):
                return (ExitNode(ret_type),[])
        else:
            raise CompilationError("You must return ACCEPT or REJECT only")

    def visit_FileAST(self,n:ast.FileAST):
        if(n.ext is None or len(n.ext)!=1 or not isinstance(n.ext[0],ast.FuncDef)):
            raise CompilationError("Exactly one function expected")
        
        entry_node = self.visit(n.ext[0])
        
        assert(entry_node is not None)
        
        return entry_node,self.field_name_to_no_map,self.field_no_to_sizes_map,self.constants
    

def get_spec(filename):
    file_ast = parse_file(filename)
    cfg_gen = CFGGenerator()
    res = cfg_gen.visit(file_ast)
    
    assert(res is not None)
    
    entry,field_name_to_no_map,field_no_to_sizes_map,constants = res
    no_fields = len(field_no_to_sizes_map)
    max_field_size = max(field_no_to_sizes_map.values())
        
    cur_phv = [BitVecVal(0,field_no_to_sizes_map[i]) for i in range(no_fields)]
    
    default_phv = [BitVecVal(0,field_no_to_sizes_map[i]) for i in range(no_fields)]
    
    default_phv_padded = [BitVecVal(0,max_field_size) for i in range(no_fields)]
    
    fields_extracted = [False]*no_fields
    
    max_packet_size = entry.get_max_packet_size(0,fields_extracted,field_no_to_sizes_map)
    
    packet = BitVec('x',max_packet_size)
    def spec(packet):    
        #TODO can we not do the cfg traversal everytime ? Any better way to get closure ? Ok for now
        res_phv,res_state = entry.make_spec(cur_phv,default_phv,0,field_no_to_sizes_map,max_field_size,packet)
        for i in range(no_fields):
            res_phv[i] = ZeroExt(max_field_size-field_no_to_sizes_map[i],res_phv[i])
        return res_phv,res_state
        
    #phv, accept = (entry.make_spec(cur_phv,default_phv,0,field_no_to_sizes_map,max_field_size,packet))
    #for i, f in enumerate(phv):
    #    print(f"field[{i}]:\n{f}")
    #    print("\n\n\n")
    #print(f"accept:\n{accept}")
    #print()
    #print(field_no_to_sizes_map)
    #print(field_name_to_no_map)
    #print("max pkt sz=",max_packet_size)
    #print("max field sz= ", max_field_size)
    return field_name_to_no_map,field_no_to_sizes_map,max_packet_size,default_phv_padded,spec,list(set(constants))