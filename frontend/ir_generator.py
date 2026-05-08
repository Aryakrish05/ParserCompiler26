import sys
from pathlib import Path

import pycparser.c_ast as ast

from frontend.analyser import Info, parse_source, collect_info
from frontend.field_minimiser import best_modifier


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
