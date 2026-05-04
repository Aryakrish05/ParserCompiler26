import graphviz

def render_parse_graph(table_entries,default_field,default_next_state,field_names,ternary_match=False):
    
    parse_graph = graphviz.Digraph('ParseGraph',comment = 'Parser as State Machine')
    num_nodes = len(default_field)
    num_entries = len(table_entries)
    
    for i in range(num_nodes):
        parse_graph.node(f'Node{i}',f'Extract({field_names[default_field[i]]})')
        
    no_accept = True
    no_reject = True
    
    for ns in default_next_state:
        if(ns==num_nodes):
            no_accept = False
        elif(ns==num_nodes+1):
            no_reject = False
    
    if(ternary_match):
        for _,ns,_,_ in table_entries:
            if(ns==num_nodes):
                no_accept = False
            elif(ns==num_nodes+1):
                no_reject = False
    else:
        for _,ns,_ in table_entries:
            if(ns==num_nodes):
                no_accept = False
            elif(ns==num_nodes+1):
                no_reject = False

    if (not no_accept):
        parse_graph.node('ACCEPT','ACCEPT')
    if (not no_reject):
        parse_graph.node('REJECT','REJECT')
    
    for i in range(num_nodes):
        if(default_next_state[i]==num_nodes):
            parse_graph.edge(f'Node{i}','ACCEPT')
        elif(default_next_state[i]==num_nodes+1):
            parse_graph.edge(f'Node{i}','REJECT')
        else:
            parse_graph.edge(f'Node{i}',f'Node{default_next_state[i]}')
    
    for i in range(num_entries):
        assert(table_entries[i][0]<num_nodes)
        #this assertion can fail if it's not the minimum
        if(ternary_match):
            if(table_entries[i][1]==num_nodes):
                parse_graph.edge(f'Node{table_entries[i][0]}','ACCEPT',label=f'v={table_entries[i][2]},m={table_entries[i][3]}')
            elif(table_entries[i][1]==num_nodes+1):
                parse_graph.edge(f'Node{table_entries[i][0]}','REJECT',label=f'v={table_entries[i][2]},m={table_entries[i][3]}')
            else:
                parse_graph.edge(f'Node{table_entries[i][0]}',f'Node{table_entries[i][1]}',label=f'v={table_entries[i][2]},m={table_entries[i][3]}')
        else:
            if(table_entries[i][1]==num_nodes):
                parse_graph.edge(f'Node{table_entries[i][0]}','ACCEPT',label=f'v={table_entries[i][2]}')
            elif(table_entries[i][1]==num_nodes+1):
                parse_graph.edge(f'Node{table_entries[i][0]}','REJECT',label=f'v={table_entries[i][2]}')
            else:
                parse_graph.edge(f'Node{table_entries[i][0]}',f'Node{table_entries[i][1]}',label=f'v={table_entries[i][2]}')
            
    parse_graph.render(directory='./doctest-output', view=False)

            