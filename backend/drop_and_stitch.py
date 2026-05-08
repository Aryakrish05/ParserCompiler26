from backend.p4_generator import State
from spec.cfg_builder import EntryNode, ExtractNode, IfThenElseNode, ExitNode


#condition is a tuple of lists with == and != respectively
def is_condition_valid(condition):
    if(len(condition[0])>1):
        return False
    if(len(condition[0])==1):
        return (condition[0][0] not in condition[1])
    return True

##############Prototype Code##########################
class Path:
    def __init__(self,fields_extracted,conditions):
        self.fields_extracted = fields_extracted
        self.conditions = conditions #dictionary from attr to conditions

    #returns True if at least one packet in the path set takes this transition
    def is_valid_for_a_packet(self,attr,condition):
        #== can never be encoded by using any number of !='s
        if(attr not in self.conditions):
            return True

        path_condition = self.conditions[attr]
        if (not (is_condition_valid(condition) and is_condition_valid(path_condition))):
            raise ValueError("You should have both path and check conditions to be valid")

        path_eq = path_condition[0]
        path_ne = path_condition[1]

        if(len(condition[0])==1):
            c = condition[0][0]
            if(len(path_eq)==1):
                return path_eq[0]==c
            return c not in path_ne

        #default branch: condition[1] is the list of excluded constants
        excluded = condition[1]
        if(len(path_eq)==0):
            return True
        return path_eq[0] not in excluded


def enumerate_paths(cfg_entry):
    paths = []

    def walk(node,fields_extracted,conditions):
        if(isinstance(node,EntryNode)):
            walk(node.next,fields_extracted,conditions)
        elif(isinstance(node,ExtractNode)):
            walk(node.next,fields_extracted+[node.attr],conditions)
        elif(isinstance(node,IfThenElseNode)):
            if(node.ternary_match):
                raise NotImplementedError("Ternary matches not allowed in stitching")
            attr = node.check_attr
            value = node.value

            if(attr in conditions):
                old_eq = conditions[attr][0]
                old_ne = conditions[attr][1]
            else:
                old_eq = []
                old_ne = []

            true_cond = (old_eq+[value],old_ne)
            if(is_condition_valid(true_cond)):
                true_conds = dict(conditions)
                true_conds[attr] = true_cond
                walk(node.next_true,fields_extracted,true_conds)

            false_cond = (old_eq,old_ne+[value])
            if(is_condition_valid(false_cond)):
                false_conds = dict(conditions)
                false_conds[attr] = false_cond
                walk(node.next_false,fields_extracted,false_conds)
        elif(isinstance(node,ExitNode)):
            paths.append(Path(fields_extracted,conditions))
        else:
            raise ValueError(f"Unknown CFG node type: {type(node).__name__}")

    walk(cfg_entry,[],{})
    return paths


def get_not_compared_between_extracts(path,attr,info):
    if(attr not in path.fields_extracted):
        return []
    i = path.fields_extracted.index(attr)
    not_compared_list = []
    for j in range(i+1,len(path.fields_extracted)):
        next_attr = path.fields_extracted[j]
        if(info.is_compared(next_attr)):
            break
        not_compared_list.append(next_attr)
    return not_compared_list


def is_there_not_compared_after(path,attr,info):
    if(attr not in path.fields_extracted):
        return False
    i = path.fields_extracted.index(attr)
    for j in range(i+1,len(path.fields_extracted)):
        if(not info.is_compared(path.fields_extracted[j])):
            return True
    return False


def replicate(states,state_no):
    new_no = len(states)
    ns = State()
    ns.field_used = states[state_no].field_used
    ns.transitions = []
    states.append(ns)
    return new_no


#derive the CFG constants the current attr is tested against (from `paths`),
#and produce one dispatch entry per constant, plus default. target lookup is
#against the synth state's transitions; if the synth doesn't dispatch on a
#CFG constant, that entry's target = synth's default.
#NOTE: CFG paths carry POST-modifier (new) constants; the synth state carries
#old constants (table_to_states already remapped). we convert new->old via
#info so the output dispatch values match what's on the wire.
def get_dispatch_list(states,state_no,paths,attr,info):
    cfg_constants_new = set()
    for path in paths:
        if(attr in path.conditions):
            for v in path.conditions[attr][0]:
                cfg_constants_new.add(v)
            for v in path.conditions[attr][1]:
                cfg_constants_new.add(v)

    synth_value_to_nxt = {}
    default_nxt = None
    for (_,v,nxt) in states[state_no].transitions:
        if(v is None):
            default_nxt = nxt
        else:
            synth_value_to_nxt[v] = nxt

    branches = []
    for c_new in sorted(cfg_constants_new):
        c_old = info.get_old_constant(attr,c_new)
        if(c_old in synth_value_to_nxt):
            branches.append((c_new,c_old,synth_value_to_nxt[c_old]))
        else:
            branches.append((c_new,c_old,default_nxt))
    branches.append((None,None,default_nxt))
    return branches


def add_not_compared_onto_transition(states,nc_attrs,final_target):
    head = final_target
    for a in reversed(nc_attrs):
        new_no = len(states)
        ns = State()
        ns.field_used = a
        ns.transitions = [(None,None,head)]
        states.append(ns)
        head = new_no
    return head


#STEP 3 filter: keep only paths with at least one NC extract after attr's.
def filter_paths(paths,attr,info):
    return [p for p in paths if is_there_not_compared_after(p,attr,info)]


#always-replicate stitch. for each CFG-derived constant (+ default) at this
#state, decide a target:
#  - terminal nxt           -> point at terminal directly
#  - empty forward          -> point at original synth state (no NCs needed
#                              downstream so it's safe to share)
#  - non-empty forward      -> ALWAYS replicate downstream and recurse
#no sharing across branches; no multi-replica reasoning. simplest correct.
def process(states,state_no,replica_no,paths,info):
    attr = states[state_no].field_used
    paths = filter_paths(paths,attr,info)
    branches_with_targets = get_dispatch_list(states,state_no,paths,attr,info)
    constants_new = [c_new for (c_new,_,_) in branches_with_targets if c_new is not None]

    new_transitions = []
    for (value_new,value_old,nxt) in branches_with_targets:
        if(value_new is None):
            condition = ([],constants_new)
        else:
            condition = ([value_new],[])
        paths_in_branch = [p for p in paths if p.is_valid_for_a_packet(attr,condition)]
        if(paths_in_branch):
            nc_chain = get_not_compared_between_extracts(paths_in_branch[0],attr,info)
        else:
            nc_chain = []

        if(states[nxt].is_accept or states[nxt].is_reject):
            target = nxt
        else:
            forward = filter_paths(paths_in_branch,states[nxt].field_used,info)
            if(not forward):
                target = nxt
            else:
                target = replicate(states,nxt)
                process(states,nxt,target,forward,info)

        if(nc_chain):
            target = add_not_compared_onto_transition(states,nc_chain,target)
        new_transitions.append((None,value_old,target))

    states[replica_no].transitions = new_transitions


def stitch_back(states,info,paths):
    process(states,0,0,list(paths),info)


#straight-line case (no compared fields, no synth states): walk the CFG, emit
#one NC extract state per extract, then ACCEPT/REJECT depending on outcome.
def build_straight_line_states(cfg_entry):
    extracts = []
    outcome = [None]

    def walk(node):
        if(isinstance(node,EntryNode)):
            walk(node.next)
        elif(isinstance(node,ExtractNode)):
            extracts.append(node.attr)
            walk(node.next)
        elif(isinstance(node,ExitNode)):
            outcome[0] = node.accept_or_reject
        else:
            raise ValueError("straight-line CFG cannot have branches")

    walk(cfg_entry)

    n = len(extracts)
    accept_idx = n
    reject_idx = n+1
    states = [State() for _ in range(n+2)]

    for i in range(n):
        states[i].field_used = extracts[i]
        if(i+1<n):
            nxt = i+1
        elif(outcome[0]):
            nxt = accept_idx
        else:
            nxt = reject_idx
        states[i].transitions = [(None,None,nxt)]

    states[accept_idx].is_accept = True
    states[reject_idx].is_reject = True
    return states


#graphviz of the stitched state graph.
def render_states(states,output_name='stitched'):
    import graphviz
    g = graphviz.Digraph(output_name)
    g.attr('node',shape='box',fontname='Courier')
    for i,st in enumerate(states):
        if(st.is_accept):
            g.node(f'S{i}','ACCEPT',shape='oval',style='filled',fillcolor='lightgreen')
        elif(st.is_reject):
            g.node(f'S{i}','REJECT',shape='oval',style='filled',fillcolor='lightpink')
        else:
            attr = st.field_used
            tag = 'extract' if st.is_extraction else 'use'
            label = f'S{i}\\n{tag}({attr[0]}.{attr[1]})'
            color = 'lightyellow' if st.is_extraction else 'white'
            g.node(f'S{i}',label,style='filled',fillcolor=color)
    for i,st in enumerate(states):
        if(st.is_accept or st.is_reject):
            continue
        for (mask,value,nxt) in st.transitions:
            if(mask is None and value is None):
                lbl = 'default'
            elif(mask is None):
                lbl = f'={value}'
            else:
                lbl = f'(&{mask})={value}'
            g.edge(f'S{i}',f'S{nxt}',label=lbl)
    out = g.render(directory='./_build/stitched',view=False,cleanup=False)
    return out
