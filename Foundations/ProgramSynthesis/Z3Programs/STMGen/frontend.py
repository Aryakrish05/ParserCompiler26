import math
import re
import sys
import math
from pathlib import Path

import pycparser.c_ast as ast
from pycparser import CParser

class CompilationError(Exception):
    pass

#LLM used for generating the two functions below 
#pycparser doesn't allow bit_<N> and comments
def prescan_widths(text):
    widths = {}
    struct_pat = re.compile(r'struct(?:\s+(\w+))?\s*\{([^}]*)\}', re.DOTALL)
    field_pat = re.compile(r'\bbit_(\d+)\s+(\w+)\s*;')
    for sm in struct_pat.finditer(text):
        struct_name = sm.group(1)
        for fm in field_pat.finditer(sm.group(2)):
            widths[(struct_name, fm.group(2))] = int(fm.group(1))
    return widths

def parse_source(filename):
    text = Path(filename).read_text()
    text = re.sub(r'/\*.*?\*/', '', text, flags=re.DOTALL)
    text = re.sub(r'//[^\n]*', '', text)
    widths = prescan_widths(text)
    substituted = re.sub(r'\bbit_\d+\b', 'int', text)
    parser = CParser()
    file_ast = parser.parse(substituted, filename=filename)
    return file_ast, widths

#First pass is to collect information - which are compared against what and how ...
class Collector(ast.NodeVisitor):
    
    def __init__(self,original_widths):
        super().__init__()
        self.phv_members = {} #dictionary of name to type
        self.original_widths = original_widths
        self.struct_decls = {} #dictionary of structs to list of (fields,size)
        self.field_info = {} #dictionary of (phv_name,field_name) to list of pairs (mask/None,value)
        
    def generic_visit(self, node: ast.Node):
        raise CompilationError("The code doesn't adhere to the specification, use only allowed constructs")
    
    def visit_Return(self,n:ast.Return):
        if((not isinstance(n.expr,ast.ID)) or self.visit(n.expr)  not in ["ACCEPT","REJECT"]):
            raise CompilationError("You must return ACCEPT or REJECT only")
    
    def visit_Constant(self,n:ast.Constant):
        val = n.value
        if n.type == 'char':
            return ord(val.strip("'").encode().decode('unicode_escape'))
        s = val.lower().rstrip('ul')
        if len(s) > 1 and s.startswith('0') and s[1] not in ('x', 'b', 'o'):
            return int(s, 8)
        return int(s, 0)

    def visit_ID(self,n:ast.ID):
        return n.name
    
    def declare_struct(self,struct:ast.Struct):
        if (struct.name in self.struct_decls):
            raise CompilationError("Two struct declarations cannot have the same name")
        if not struct.decls:
            raise CompilationError("Header structs cannot have no fields")
        fields = []
        for fd in struct.decls:
            if not isinstance(fd, ast.Decl):
                raise CompilationError("Unexpected struct member")
            key = (struct.name, fd.name)
            if key not in self.original_widths:
                raise CompilationError(f"Fields must be of bit_<N> type")
            field_sz = self.original_widths[key]
            if field_sz <= 0:
                raise CompilationError("Fields cannot have non-positive size")
            fields.append((fd.name, field_sz))
        self.struct_decls[struct.name] = fields
        
    def declare_phv(self,phv_def:ast.Decl):
        
        decls = phv_def.type.type.decls
        
        if not decls:
            raise CompilationError("phv must have at least one member")
        
        for hdr in decls:
            if not isinstance(hdr, ast.Decl):
                raise CompilationError("Unexpected phv member")
            if not (isinstance(hdr.type, ast.TypeDecl)
                    and isinstance(hdr.type.type, ast.Struct)
                    and hdr.type.type.name is not None
                    and hdr.type.type.decls is None):
                raise CompilationError(f"phv members must be of previously declared struct type")
            header_type = hdr.type.type.name
            if header_type not in self.struct_decls:
                raise CompilationError(f"phv members must refer to previously declared structs")
            if hdr.name in self.phv_members:
                raise CompilationError(f"Two headers in phv cannot have the same name")
            self.phv_members[hdr.name] = header_type
            
    def visit_FileAST(self,n):
        if n.ext is None or n.ext==[]:
            raise CompilationError("Empty input file")
        struct_defs = {}
        phv_def = None
        parse_def = None
    
        for d in n.ext:
            if (isinstance(d,ast.Decl)):
                if(d.name is None and isinstance(d.type,ast.Struct) 
                   and d.type.name is not None and d.type.decls is not None):
                    if(d.type.name in struct_defs):
                        raise CompilationError("Can't have two different struct types with same name")
                    struct_defs[d.type.name] = d.type
                    continue
                if (d.name == 'phv'):
                    if (phv_def is not None):
                        raise CompilationError("Can't have two different phv declarations")
                    phv_def = d
                    
                    if (not (isinstance(d.type,ast.TypeDecl) and 
                             isinstance(d.type.type,ast.Struct) and d.type.declname is not None and
                             d.type.type.decls is not None)):
                        raise CompilationError("phv declaration doesn't adhere to specification")
                        
                    continue
                raise CompilationError("Unknown struct declaration, only phv or struct type allowed")
            if (isinstance(d,ast.FuncDef)):
                if (parse_def is not None):
                    raise CompilationError("Only one function - parse() allowed")
                parse_def = d
                continue
            raise CompilationError(f"Unknown construct")
        
        if (phv_def is None):
            raise CompilationError("Anonymous struct - phv must be declared")
        
        if (parse_def is None):
            raise CompilationError("One function int parse() must be declared")
        
        for struct in struct_defs.values():
            self.declare_struct(struct)
        
        self.declare_phv(phv_def)
        
        self.visit(parse_def)
        
        
    def visit_FuncDef(self, n:ast.FuncDef):
        if(n.decl.name != "parse"):
            raise CompilationError("Parsing function must be named parse")
        self.visit(n.body)
        
    def visit_FuncCall(self, n:ast.FuncCall):
        
        if(n.name.name != "Extract"):
            raise CompilationError("Only function calls allowed are extracts")

        if(len(n.args.exprs) != 1):
            raise CompilationError("Only one argument for Extract")
        
        argument = n.args.exprs[0]
        if(not (isinstance(argument,ast.StructRef) and isinstance(argument.name,ast.ID) and 
                argument.name.name == "phv" and isinstance(argument.field,ast.ID) and argument.type == ".")):
            raise CompilationError("Function calls must be of the type Extract(phv.___)")
        
        member = argument.field.name
        if(member not in self.phv_members):
            raise CompilationError("The header being extracted must be a member of phv")
    
    def visit_Compound(self,n:ast.Compound):
        if(n.block_items is None):
            raise CompilationError("Blocks cannot be empty")

        for x in n.block_items:
            if(not (isinstance(x,ast.If) or isinstance(x,ast.FuncCall) or isinstance(x,ast.Return))):
                raise CompilationError("In a block, you can have only extracts,if-statements and returns")
            self.visit(x)
            
    def visit_StructRef(self,n:ast.StructRef):
        if(not(isinstance(n.name,ast.StructRef) and n.name.name.name=="phv" and isinstance(n.name.field,ast.ID) and 
           n.name.field.name in self.phv_members and isinstance(n.field,ast.ID))):
            raise CompilationError("In any if condition, check should be on a field of a member of phv")
        
        phv_member = n.name.field.name
        field_name = n.field.name
        for (fname,sz) in self.struct_decls[self.phv_members[phv_member]]:
            if(fname==field_name):
                return (phv_member,field_name)
        raise CompilationError("The field being compared on must be part of the phv member")
    
    def visit_BinaryOp(self,n:ast.BinaryOp):
        
        if(n.op not in ["==","!=","&"]):
            raise CompilationError("The only operations supported are == and != and & in a specific format")
        
        if(n.op=="&" and not isinstance(n.left,ast.StructRef)):
            raise CompilationError("Left side of an operator must be a StructRef when you are doing ternary match")
        
        if((n.op=="==" or n.op=="!=") and not (isinstance(n.left,ast.StructRef) or (isinstance(n.left,ast.BinaryOp) and n.left.op=="&"))):
            raise CompilationError("Left side of an operator must be a StructRef when you are doing an exact match")
        
        if(not isinstance(n.right,ast.Constant)):
            raise CompilationError("Right side of an operator must be a Constant")

        condition_field_or_mask = self.visit(n.left)
        condition_value = self.visit(n.right)
        
        if (condition_value is not None and condition_value<0):
            raise CompilationError("The comparison value must be non-negative")
            
        return [n.op,condition_field_or_mask,condition_value]
          
    def visit_If(self, n: ast.If):
        if(not isinstance(n.cond,ast.BinaryOp)):
            raise CompilationError("Only Binary/Ternary comparisons of identifier and constant allowed as if condition")
        
        condition = self.visit(n.cond)
        
        self.visit(n.iftrue)
        
        if(n.iffalse is not None):
            self.visit(n.iffalse)
        
        if(condition is None):
            raise ValueError("Something wrong with visit_BinaryOp")
        
        match_value = condition[2]
        match_field_tuple = condition[1]
        match_mask = None
        if(isinstance(condition[1],list)):
            match_field_tuple = condition[1][1]
            match_mask = condition[1][2]
            if(condition[1][0]!="&"):
                raise CompilationError("The only operator allowed for ternary matching is & and it should be used once")
        
        if(match_field_tuple in self.field_info):
            self.field_info[match_field_tuple].append((match_mask,match_value))
        else:
            self.field_info[match_field_tuple] = [(match_mask,match_value)]

class FieldInfo:
    def __init__(self,size,cmpname):
        self.cmpname = cmpname
        self.old_size = size
        self.new_size = size

class NotCompared(FieldInfo):
    def __init__(self,size,cmpname):
        super().__init__(size,cmpname)

class Exact(FieldInfo):
    def __init__(self, constants,size,cmpname):
        super().__init__(size,cmpname)
        self.old_constants = list(set(constants))
        self.new_constants = list(self.old_constants)

#For now we don't support modifications in ternary matched fields
class Ternary(FieldInfo):
    def __init__(self,constants,ternary_matches,size,cmpname):
        super().__init__(size,cmpname)
        self.old_constants = list(set(constants))
        self.old_ternary_matches = list(set(ternary_matches))
        self.new_constants = list(self.old_constants)
        self.new_ternary_matches = list(self.old_ternary_matches)

class Info:
    def __init__(self,attr_to_info,phvmem_to_new_contents,old_phv_members,old_struct_decls):
        self.attr_to_info = attr_to_info
        self.phvmem_new_contents = phvmem_to_new_contents#List of names in the phvmem
        self.old_phv_members = old_phv_members
        self.old_struct_decls = old_struct_decls
        self.all_field_nos = {}
        self.compared_field_nos = {}
    
    def fill_field_nos(self):
        self.all_field_nos = {}
        self.compared_field_nos = {}
        useful_ptr = 0
        all_ptr = 0
        for phv_member in self.phvmem_new_contents:
            for field in self.phvmem_new_contents[phv_member]:
                attr = (phv_member,field)
                if ( attr not in self.all_field_nos):
                    self.all_field_nos[attr] = all_ptr
                    all_ptr += 1
                if (not isinstance(self.attr_to_info[attr],NotCompared) and 
                    attr not in self.compared_field_nos):
                    self.compared_field_nos[attr] = useful_ptr
                    useful_ptr += 1
                    
    def is_compared(self,attr):
        return not isinstance(self.attr_to_info[attr],NotCompared)   
    
    def get_new_constant(self,attr,c):
        assert(not isinstance(self.attr_to_info[attr],NotCompared))
        for i in range(0,len(self.attr_to_info[attr].old_constants)):
            if(self.attr_to_info[attr].old_constants[i]==c):
                return self.attr_to_info[attr].new_constants[i]
        assert(False)
    
    def get_old_constant(self,attr,c):
        assert(not isinstance(self.attr_to_info[attr],NotCompared))
        for i in range(0,len(self.attr_to_info[attr].new_constants)):
            if(self.attr_to_info[attr].new_constants[i]==c):
                return self.attr_to_info[attr].old_constants[i]
        assert(False)
    
    def get_new_mvpair(self,attr,mv):
        assert(isinstance(self.attr_to_info[attr],Ternary))
        for i in range(0,len(self.attr_to_info[attr].old_ternary_matches)):
            if(self.attr_to_info[attr].old_ternary_matches[i]==mv):
                return self.attr_to_info[attr].new_ternary_matches[i]
        assert(False)

    def get_old_mvpair(self,attr,mv):
        assert(isinstance(self.attr_to_info[attr],Ternary))
        for i in range(0,len(self.attr_to_info[attr].new_ternary_matches)):
            if(self.attr_to_info[attr].new_ternary_matches[i]==mv):
                return self.attr_to_info[attr].old_ternary_matches[i]
        assert(False)
    
    def get_cmpname(self,attr):
        return self.attr_to_info[attr].cmpname
    
    def get_attr_from_cmpname(self,cmpname):
        for attr in self.attr_to_info:
            if(self.attr_to_info[attr].cmpname==cmpname):
                return attr
        assert(False)
    
    def get_new_size(self,attr):
        return self.attr_to_info[attr].new_size
    
    def get_old_size(self,attr):
        return self.attr_to_info[attr].old_size

    def get_no_from_attr_all(self,attr):
        return self.all_field_nos[attr]
    
    def get_no_from_attr_compared(self,attr):
        return self.compared_field_nos[attr]
    
    def get_attr_from_no_compared(self,no):
        for (k,v) in self.compared_field_nos.items():
            if(v==no):
                return k
        assert(False)
    
    def get_attr_from_no_all(self,no):
        for (k,v) in self.all_field_nos.items():
            if(v==no):
                return k
        assert(False)
        
def collect_info(file_ast,widths):
    collector = Collector(widths)
    collector.visit(file_ast)
    
    attr_to_info = {}
    phvmem_to_new_contents = {}
    cnt = 0
    for phv_mem in collector.phv_members:
        for (field,size) in collector.struct_decls[collector.phv_members[phv_mem]]:
            #not correct always but ok for now
            cmpname = f"{phv_mem}_{field}_{cnt}"
            cnt += 1
            if ((phv_mem,field) in collector.field_info):
                constants = []
                ternary = []
                for (m,v) in collector.field_info[(phv_mem,field)]:
                    if(m is None):
                        constants.append(v)
                    else:
                        ternary.append((m,v))
                if len(ternary) >= 1 :
                    attr_to_info[(phv_mem,field)] = Ternary(constants,ternary,size,cmpname)     
                else:
                    attr_to_info[(phv_mem,field)] = Exact(constants,size,cmpname)                  
            else:
                attr_to_info[(phv_mem,field)] = NotCompared(size,cmpname)
            
        phvmem_to_new_contents[phv_mem] = list(field for (field,_) in collector.struct_decls[collector.phv_members[phv_mem]])

    return Info(attr_to_info,phvmem_to_new_contents,collector.phv_members,collector.struct_decls)
            
            
class IRGen(ast.NodeVisitor):
    
    def __init__(self,info:Info,outfile):
        super().__init__()
        self.info = info
        self.outfile = outfile
        self.indent = 0

    def visit_Return(self,n:ast.Return):
        print(" "*self.indent,f"return {n.expr.name};",file=self.outfile)
    
    def visit_FileAST(self,n):
        parse_def = None
        
        for d in n.ext:
            if (isinstance(d,ast.FuncDef)):
                parse_def = d
                break
            
        if parse_def is not None:
            self.visit(parse_def)
    
    def visit_Constant(self,n:ast.Constant):
        val = n.value
        if n.type == 'char':
            return ord(val.strip("'").encode().decode('unicode_escape'))
        s = val.lower().rstrip('ul')
        if len(s) > 1 and s.startswith('0') and s[1] not in ('x', 'b', 'o'):
            return int(s, 8)
        return int(s, 0)

    def visit_ID(self,n:ast.ID):
        return n.name
            
    def visit_FuncDef(self, n:ast.FuncDef):
        print("int parse ()",end="",file=self.outfile)
        self.visit(n.body)
        
    def visit_FuncCall(self, n:ast.FuncCall):
        phv_member = n.args.exprs[0].field.name
        for fname in self.info.phvmem_new_contents[phv_member]:
            size = self.info.get_new_size((phv_member, fname))
            name = self.info.get_cmpname((phv_member, fname))
            print(" "*self.indent,f"Extract({name},{size});",file=self.outfile)
    
    def visit_Compound(self,n:ast.Compound):
        if(n.block_items is None):
            return None
        print(" "*self.indent,"{",file=self.outfile)
        self.indent += 4
        for x in n.block_items:
            self.visit(x)
        self.indent -= 4
        print(" "*self.indent,"}",file=self.outfile)
        
    def visit_StructRef(self,n:ast.StructRef):
                
        phv_member = n.name.field.name
        field_name = n.field.name
        for (fname,_) in self.info.old_struct_decls[self.info.old_phv_members[phv_member]]:
            if(fname==field_name):
                return (phv_member,field_name)
        return None
    
    def visit_BinaryOp(self,n:ast.BinaryOp):

        condition_field_or_mask = self.visit(n.left)
        condition_value = self.visit(n.right)
        
        return [n.op,condition_field_or_mask,condition_value]
          
    def visit_If(self, n: ast.If):
        
        condition = self.visit(n.cond)
                
        if(condition is None):
            raise ValueError("Something wrong with visit_BinaryOp")
        
        match_value = condition[2]
        match_field_tuple = condition[1]
        
        match_mask = None
        if(isinstance(condition[1],list)):
            match_field_tuple = condition[1][1]
            match_mask = condition[1][2]
            match_mask,match_value = self.info.get_new_mvpair(match_field_tuple,(match_mask,match_value))
            cmpname = self.info.get_cmpname(match_field_tuple)
            print(" "*self.indent,f"if(({cmpname}&{match_mask}){condition[0]}{match_value})",file=self.outfile)
        else:
            cmpname = self.info.get_cmpname(match_field_tuple)
            match_value =self.info.get_new_constant(match_field_tuple,match_value)
            print(" "*self.indent,f"if({cmpname}{condition[0]}{match_value})",file=self.outfile)
            
        self.visit(n.iftrue)
        
        if(n.iffalse is not None):
            print(" "*self.indent,"else",file=self.outfile)
            self.visit(n.iffalse)
    
def reduce_exact_size(field:Exact):
    field.new_size = math.ceil(math.log2(len(field.old_constants)+1)) + 1
    for i in range(len(field.new_constants)):
        field.new_constants[i] = i

def reduce_not_compared_size(field:NotCompared):
    field.new_size = 1

#drops not compared members which are not separate structs themselves
# it might be nice to maintain what is merged to what but truth is - i don't need that
# finally I will just end up extracting the entire struct together in P4

def drop_unused_members(info:Info):
    for phv_member in info.old_phv_members:
        is_anything_compared = False
        for (field,_) in info.old_struct_decls[info.old_phv_members[phv_member]]:
            if not isinstance(info.attr_to_info[(phv_member,field)],NotCompared):
                is_anything_compared = True
                break
        if(is_anything_compared):
            info.phvmem_new_contents[phv_member] = []
            for (field,_) in info.old_struct_decls[info.old_phv_members[phv_member]]:
                if not isinstance(info.attr_to_info[(phv_member,field)],NotCompared):
                    info.phvmem_new_contents[phv_member].append(field)
        else:
            assert(info.phvmem_new_contents[phv_member]!=[])
            info.phvmem_new_contents[phv_member] = [info.phvmem_new_contents[phv_member][0]]

def reduce_all_sizes(info:Info):
    for field in info.attr_to_info.values():
        if(isinstance(field,Exact)):
            reduce_exact_size(field)
        elif(isinstance(field,NotCompared)):
            reduce_not_compared_size(field)

def best_modifier(info):
    reduce_all_sizes(info)
    drop_unused_members(info)
    return info

def no_size_reduction_modifier(info):
    drop_unused_members(info)
    return info
            
def compile_to_pc(in_path, out_path, modifier=best_modifier):
    file_ast, widths = parse_source(in_path)
    info = collect_info(file_ast,widths)
    if (modifier is not None):
        info = modifier(info)
    info.fill_field_nos()
    with open(out_path, 'w') as f:
        IRGen(info, f).visit(file_ast)
    return info

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print('Usage: frontend.py <file.parser>', file=sys.stderr)
        sys.exit(1)
    src = sys.argv[1]
    build_dir = Path('_build')
    build_dir.mkdir(exist_ok=True)
    out = str(build_dir / (Path(src).stem + '.gen.pc'))
    compile_to_pc(src, out)
    print(f'wrote {out}')