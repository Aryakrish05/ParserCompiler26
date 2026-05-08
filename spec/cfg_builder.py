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
from frontend.analyser import Info, CompilationError

#TODO - get rid of tuples and use dataclasses for better readability
#TODO - document how the flow of values happen in the design - need forc cur_phv

class CFGNode:

    def print(self,indent):
        raise NotImplementedError

    #call only after doing get_max_packet_size
    def make_spec(self,cur_phv,default_phv,ptr,info,drop_uncompared,max_field_size,packet):
        #cur_phv contains the expressions for the fields on the active path
        #default_phv contains the defaults - all sentinel for now, but user can choose
        #ptr contains the packet pointer till now
        #info: frontend.Info — source of truth for sizes and attr->fno maps
        #drop_uncompared: True -> uncompared attrs are wire-skips (not in synth phv);
        #         False -> every attr is in synth phv
        raise NotImplementedError

    def get_max_packet_size(self,ptr,fields_extracted,info,drop_uncompared):
        #For validation this should be called with drop_uncompared=False so every extract
        raise NotImplementedError

class EntryNode(CFGNode):
    def __init__(self):
        self.next = None

    def print(self,indent=0):
        print(" "*indent,"Entry")
        assert(self.next is not None)
        self.next.print(indent+4)

    def make_spec(self, cur_phv, default_phv, ptr, info, drop_uncompared, max_field_size, packet):
        assert(self.next is not None)
        return self.next.make_spec(cur_phv,default_phv,ptr,info,drop_uncompared,max_field_size,packet)

    def get_max_packet_size(self, ptr, fields_extracted, info, drop_uncompared):
        assert(self.next is not None)
        return self.next.get_max_packet_size(ptr,fields_extracted,info,drop_uncompared)

class ExtractNode(CFGNode):
    def __init__(self,attr):
        self.attr = attr
        self.next = None

    def print(self,indent):
        print(" "*indent,f"Extract({self.attr})")
        assert(self.next is not None)
        self.next.print(indent+4)

    def get_max_packet_size(self,ptr,fields_extracted,info,drop_uncompared):
        assert(self.next is not None)
        sz = info.get_new_size(self.attr)

        if drop_uncompared and not info.is_compared(self.attr):
            return self.next.get_max_packet_size(ptr+sz,fields_extracted,info,drop_uncompared)

        fno = info.get_no_from_attr_compared(self.attr) if drop_uncompared else info.get_no_from_attr_all(self.attr)

        if(fields_extracted[fno]):
            raise CompilationError("You must not extract the same field at two different places on the same path")
        fields_extracted[fno] = True
        max_ptr_next = self.next.get_max_packet_size(ptr+sz,fields_extracted,info,drop_uncompared)
        fields_extracted[fno] = False
        return max_ptr_next

    def make_spec(self, cur_phv, default_phv, ptr, info, drop_uncompared, max_field_size, packet):
        assert(self.next is not None)
        sz = info.get_new_size(self.attr)

        if drop_uncompared and not info.is_compared(self.attr):
            return self.next.make_spec(cur_phv,default_phv,ptr+sz,info,drop_uncompared,max_field_size,packet)

        fno = info.get_no_from_attr_compared(self.attr) if drop_uncompared else info.get_no_from_attr_all(self.attr)
        cur_phv[fno] = ZeroExt(max_field_size-sz,Extract(ptr+sz-1,ptr,packet))
        res_phv,res_state = self.next.make_spec(cur_phv,default_phv,ptr+sz,info,drop_uncompared,max_field_size,packet)
        res_phv[fno] = ZeroExt(max_field_size-sz,Extract(ptr+sz-1,ptr,packet))
        return (res_phv,res_state)

class IfThenElseNode(CFGNode):
    def __init__(self,check_attr,equality_value,mask=None,ternary_match=False):
        self.ternary_match = ternary_match
        self.mask = mask
        if(self.ternary_match and mask is None):
            raise ValueError("IfThenElseNode constructor: you need to provide mask if it is ternary")
        # check_attr is always a compared attr (you can only branch on compared fields).
        self.check_attr = check_attr
        self.value = equality_value
        self.next_true = None
        self.next_false = None

    def print(self,indent):
        if(self.ternary_match):
            print(" "*indent,f"If(({self.check_attr}&{self.mask})=={self.value})")
        else:
            print(" "*indent,f"If({self.check_attr}=={self.value})")
        assert(self.next_true is not None)
        print(" "*indent,"IfTrue:")
        self.next_true.print(indent+4)
        assert(self.next_false is not None)
        print(" "*indent,"IfFalse:")
        self.next_false.print(indent+4)

    def get_max_packet_size(self, ptr, fields_extracted, info, drop_uncompared):
        # check_attr is always compared, so it lives in both maps.
        fno = info.get_no_from_attr_compared(self.check_attr) if drop_uncompared else info.get_no_from_attr_all(self.check_attr)
        if(not fields_extracted[fno]):
            raise CompilationError("You must extract a field before checking on it in all possible paths")
        assert(self.next_true is not None)
        true_max_ptr = self.next_true.get_max_packet_size(ptr,fields_extracted,info,drop_uncompared)
        assert(self.next_false is not None)
        false_max_ptr = self.next_false.get_max_packet_size(ptr,fields_extracted,info,drop_uncompared)
        return max(true_max_ptr,false_max_ptr)

    def make_spec(self, cur_phv, default_phv, ptr, info, drop_uncompared, max_field_size, packet):
        fno = info.get_no_from_attr_compared(self.check_attr) if drop_uncompared else info.get_no_from_attr_all(self.check_attr)
        assert(self.next_true is not None)
        true_res_phv,true_res_state = self.next_true.make_spec(cur_phv,default_phv,ptr,info,drop_uncompared,max_field_size,packet)
        assert(self.next_false is not None)
        false_res_phv,false_res_state = self.next_false.make_spec(cur_phv,default_phv,ptr,info,drop_uncompared,max_field_size,packet)
        res_phv = []
        for i in range(len(true_res_phv)):
            if(self.ternary_match):
                res_phv.append(If((cur_phv[fno]&self.mask)==self.value,true_res_phv[i],false_res_phv[i]))
            else:
                res_phv.append(If(cur_phv[fno]==self.value,true_res_phv[i],false_res_phv[i]))
        if(self.ternary_match):
            res_state = If((cur_phv[fno]&self.mask)==self.value,true_res_state,false_res_state)
        else:
            res_state = If(cur_phv[fno]==self.value,true_res_state,false_res_state)
        return (res_phv,res_state)

class ExitNode(CFGNode):
    def __init__(self,exit_type):
        if(exit_type=="ACCEPT"):
            self.accept_or_reject = True
        else:
            self.accept_or_reject = False

    def print(self,indent):
        print(" "*indent,"ACCEPT" if self.accept_or_reject else "REJECT")

    def get_max_packet_size(self, ptr, fields_extracted, info, drop_uncompared):
        return ptr

    def make_spec(self, cur_phv, default_phv, ptr, info, drop_uncompared, max_field_size, packet):
        return (copy.deepcopy(default_phv),self.accept_or_reject)

class CFGGenerator(ast.NodeVisitor):
    def __init__(self,info:Info):
        super().__init__()
        self.info = info
        self.constants = []
        self.mask_constants = []
        self.ternary_match = False

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

        cmpname = args[0]
        attr = self.info.get_attr_from_cmpname(cmpname)

        if(args[1] != self.info.get_new_size(attr)):
            raise CompilationError(f"Size mismatch for {cmpname}: pc={args[1]} info={self.info.get_new_size(attr)}")

        extraction_node = ExtractNode(attr)
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
            raise CompilationError("Only Binary/Ternary comparisons of identifier and constant allowed as if condition")

        condition = self.visit(n.cond)
        next_true = self.visit(n.iftrue)

        next_false = None
        if(n.iffalse is not None):
            next_false = self.visit(n.iffalse)

        if(condition is None):
            raise ValueError("Something wrong with visit_BinaryOp")

        if(condition[0]=="!="):
            next_false,next_true = next_true,next_false

        match_value = condition[2]
        match_field_name = condition[1]
        match_mask = None
        if(isinstance(condition[1],tuple)):
            match_field_name = condition[1][1]
            match_mask = condition[1][2]
            self.ternary_match = True
            if(condition[1][0]!="&"):
                raise CompilationError("The only operator allowed for ternary matching is & and it should be used once")

        match_attr = self.info.get_attr_from_cmpname(match_field_name)

        if(match_mask is None):
            if_node = IfThenElseNode(match_attr,match_value)
        else:
            if_node = IfThenElseNode(match_attr,match_value,match_mask,True)
            self.mask_constants.append(match_mask)

        self.constants.append(match_value)

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

        if(n.op not in ["==","!=","&"]):
            raise CompilationError("The only operations supported are == and != and & in a specific format")

        if(n.op=="&" and not isinstance(n.left,ast.ID)):
            raise CompilationError("Left side of an operator must be an Identifier when you are doing ternary match")

        if(not isinstance(n.right,ast.Constant)):
            raise CompilationError("Right side of an operator must be a Constant")

        if((n.op=="==" or n.op=="!=") and not (isinstance(n.left,ast.ID) or (isinstance(n.left,ast.BinaryOp) and n.left.op=="&"))):
            raise CompilationError("Left side of an operator must be an Identifier when you are doing an exact match")

        condition_field_or_mask = self.visit(n.left)
        condition_value = self.visit(n.right)

        if (condition_value is not None and condition_value<0):
            raise CompilationError("The comparison value must be non-negative")

        return (n.op,condition_field_or_mask,condition_value)

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
        return entry_node,self.constants,self.mask_constants,self.ternary_match
