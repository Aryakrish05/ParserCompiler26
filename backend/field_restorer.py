from collections import deque
from frontend.analyser import Info
from backend.p4_generator import State


def table_to_states(table_entries,default_field,default_next_state,
                    info:Info,drop_uncompared:bool,ternary_match:bool):

    n = len(default_field)
    accept_idx = n
    reject_idx = n+1
    states = [State() for _ in range(n+2)]

    for v in range(n):

        if(drop_uncompared):
            attr = info.get_attr_from_no_compared(default_field[v])
        else:
            attr = info.get_attr_from_no_all(default_field[v])

        states[v].field_used = attr

        for entry in table_entries:
            if(ternary_match):
                entry_state,entry_next,entry_value,entry_mask = entry
            else:
                entry_state,entry_next,entry_value = entry
                entry_mask = None
            if(entry_state != v):
                continue
            if(entry_mask is None):
                #synth may pick a value outside source's constants when
                #constant_synthesis is off — that entry is effectively dead, skip
                try:
                    old_value = info.get_old_constant(attr,entry_value)
                except AssertionError:
                    continue
                states[v].transitions.append((None,old_value,entry_next))
            else:
                #Ternary matches have no remapping for now
                old_size = info.get_old_size(attr)
                entry_mask = ((1<<old_size)-1)&entry_mask
                entry_value = ((1<<old_size)-1)&entry_value
                states[v].transitions.append((entry_mask,entry_value,entry_next))

        states[v].transitions.append((None,None,default_next_state[v]))

    states[accept_idx].is_accept = True
    states[reject_idx].is_reject = True

    return states



def assign_extractions(states):
    n = len(states)
    extracted:list[frozenset|None] = [None]*n
    extracted[0] = frozenset()
    q = deque([0])
    while(q):
        v = q.popleft()
        attr = states[v].field_used
        if(attr is None):
            continue

        in_set = extracted[v]

        assert(in_set is not None)

        if(attr[0] in in_set):
            states[v].is_extraction = False
            out_set = in_set
        else:
            states[v].is_extraction = True
            out_set = in_set | {attr[0]}
        for (_,_,nxt) in states[v].transitions:
            if(states[nxt].is_accept or states[nxt].is_reject):
                continue
            if(extracted[nxt] is None):
                extracted[nxt] = out_set
                q.append(nxt)
