from z3 import *
'''
field1:3
field2:5

extract(field1)
extract(field2)

'''

'''
max_states states at maximum
max_fields fields at maximum

pointer[i] is the index of the last bit of packet not extracted when it enters state i
(max size-size of packet)

extracted[i] is the field I want to extract into - integer

fields[j] is the bitvector for the jth field (max size-max_fields)

next_state[i] is the next state index (values from 1 to max_states)

at a particular state

extracted[i]!=0 => fields[extracted[i]] == Extract(pointer[next_state[i]]-1,pointer[i])

pointer[1]==0

pointer[next_state[i]]>=pointer[next_state[i]]

pointer[max_states]=max_size of packet

'''

max_states=3

max_fields=2

max_size=8

max_iter=100

MAX_SIZE=32

def spec(pkt):
    return [ZeroExt(MAX_SIZE-3,Extract(2,0,pkt)),ZeroExt(MAX_SIZE-5,Extract(7,3,pkt))]


### Assume that everything is 1-indexed , 0 is special char ###

def add_field_constraints(s,max_states,max_fields,max_size,pointer,extract,next_state,fields,packet):
    
    for sidx in range(1,max_states+1):
        for fidx in range(1,max_fields+1):
            for nidx in range(1,max_states+1):
                #Any better way to do this without enumerating pointer values?
                #Also zero-extension is needed
                for p_s in range(max_size):
                    for p_n in range(p_s+1,max_size+1):
                        s.add(Implies(And(extract[sidx]==fidx,next_state[sidx]==nidx,pointer[sidx]==p_s,pointer[nidx]==p_n),fields[fidx]==ZeroExt(MAX_SIZE-(p_n-p_s),Extract(p_n-1,p_s,packet))))


def add_constraints(s,max_states,max_fields,max_size,pointer,extract,next_state,fields,packet):
    
    #adding extract constraints - all between 0 and max_fields - 0 is no extraction
    for i in range(1,max_states+1):
        s.add(And(extract[i]>=0,extract[i]<=max_fields))
        
    #pointer constraints - start ptr 0 end ptr is max_size and they advance for every transition or stay as it is
    s.add(pointer[1]==0)
    for i in range(1,max_states+1):
        for j in range(i+1,max_states+1):
            s.add(Implies(next_state[i]==j,If(extract[i]!=0, pointer[i]<pointer[j], pointer[i]==pointer[j])))
    s.add(pointer[max_states]==max_size)

    #next_state constraints
    for i in range(1,max_states):
        s.add(next_state[i]>i)
    for i in range(1,max_states+1):
        s.add(next_state[i]<=max_states)
    add_field_constraints(s,max_states,max_fields,max_size,pointer,extract,next_state,fields,packet)
    
packet=BitVec('packet',max_size)

pointer=[Int(f'p{i}') for i in range(max_states+1)]

extract=[Int(f'e{i}') for i in range(max_states+1)]

next_state=[Int(f'n{i}') for i in range(max_states+1)]

fields=[BitVec(f'f{i}',MAX_SIZE) for i in range(max_fields+1)]

s=Solver()
add_constraints(s,max_states,max_fields,max_size,pointer,extract,next_state,fields,packet)

for i in range(max_iter):
    print(f'Iteration {i}')
    
    if(s.check()==sat):
        verifier=Solver()
        add_field_constraints(verifier,max_states,max_fields,max_size,pointer,extract,next_state,fields,packet)
        m=s.model()

        for sidx in range(1,max_states+1):
            verifier.add(next_state[sidx]==m[next_state[sidx]])
            verifier.add(extract[sidx]==m[extract[sidx]])
            verifier.add(pointer[sidx]==m[pointer[sidx]])
        expected=spec(packet)
        verifier.add(Or([fields[j+1]!=expected[j] for j in range(len(expected))]))
        if verifier.check()==sat:
            v_m=verifier.model()
            spec_results=spec(v_m[packet])
            fieldscex=[BitVec(f'f{i}_{j}',MAX_SIZE) for j in range(max_fields+1)]
            for idx in range(len(spec_results)):
                s.add(fieldscex[idx+1]==spec_results[idx])
            add_field_constraints(s,max_states,max_fields,max_size,pointer,extract,next_state,fieldscex,v_m[packet])
        else:
            break
    else:
        print('Bruh')
        break

if(s.check()==unsat):
    raise Exception
m=s.model()

print("Done !")
for i in range(1,max_states+1):
    print(f'State {i} | Next_State {m[next_state[i]]} | Extract_to {m[extract[i]]} | Start_Pointer {m[pointer[i]]}')
