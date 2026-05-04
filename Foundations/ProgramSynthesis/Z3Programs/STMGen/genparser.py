from z3 import *
from enum import Enum

#We shall make an assumption that the packet is in little endian
#Standard followed across both STMGenerator and STMVerifier: 
    #start state is 0
    #accept state is no_states
    #reject state is no_states+1

set_param('verbose', 0)

class STMNotFoundError(Exception):
    pass

class OrderingType(Enum):
    NO_ORDERING = 0
    STATE_ORDERING = 1
    FIELD_ORDERING = 2
    FIELD_FIXING = 3
    
class STMSolver:

    def __init__(self,table_size,no_states,no_fields,max_packet_size,max_field_size,not_always_extract=True):

        self.table_size = table_size
        self.no_states = no_states
        self.no_fields = no_fields
        self.accept = no_states
        self.reject = no_states+1
        self.solver = Solver()
        self.max_packet_size = max_packet_size
        self.max_field_size = max_field_size
        #When True, a state extracts a field only if it hasn't been extracted yet
        #on this path (sentinel guard via initial_phv). When False, every state
        #visit extracts unconditionally - the original encoding.
        self.not_always_extract = not_always_extract
    
    def transition(self,cur_state,cur_pos,cur_phv,field_sizes,packet,initial_phv):
        
        raise NotImplementedError
        
    def simulate_stm(self,field_sizes,initial_phv,packet,num_steps):
        
        cur_state=0
        cur_pos=0
        cur_phv=initial_phv
        
        for _ in range(num_steps):
            cur_state,cur_pos,cur_phv = self.transition(cur_state,cur_pos,cur_phv,field_sizes,packet,initial_phv)
        
        return cur_state,cur_pos,cur_phv
    
    def is_sat(self):
        is_sat_or_not = self.solver.check()==sat
        #print(self.solver.statistics ())
        return is_sat_or_not
    
        
class STMGenerator(STMSolver):

    def __init__(self,table_size,no_states,no_fields,max_packet_size,max_field_size,ordering_type,ternary_match,not_always_extract=True):

        super().__init__(table_size,no_states,no_fields,max_packet_size,max_field_size,not_always_extract)
        
        self.entry_state = [Int(f's{i}') for i in range(table_size)]
        self.entry_next_state = [Int(f'ns{i}') for i in range(table_size)]
        self.entry_match_value = [BitVec(f'v{i}',self.max_field_size) for i in range(table_size)]
        self.ternary_match = ternary_match
        
        if(self.ternary_match):
            self.entry_match_mask = [BitVec(f'm{i}',self.max_field_size) for i in range(table_size)]
        
        self.default_field = [Int(f'f{i}') for i in range(no_states)]
        self.default_next_state = [Int(f'd{i}') for i in range(no_states)]
        
        constraints = []
        
        #domain constraints
        for i in range(table_size):
            constraints.append(And(self.entry_state[i]>=0,self.entry_state[i]<no_states))
            constraints.append(And(self.entry_next_state[i]<=no_states+1,self.entry_next_state[i]>=0))

        for i in range(no_states):
            constraints.append(self.default_next_state[i]<=no_states+1)
            constraints.append(And(self.default_field[i]>=0,self.default_field[i]<no_fields))
        
        #determinism constraints
        for i in range(table_size):
            for j in range(i+1,table_size):
                if(self.ternary_match):
                    #constraints.append(Implies(And(self.entry_state[i]==self.entry_state[j],self.entry_match_mask[i]==self.entry_match_mask[j]),self.entry_match_value[i]!=self.entry_match_value[j]))
                    pass
                else:
                    constraints.append(Implies(self.entry_state[i]==self.entry_state[j],self.entry_match_value[i]!=self.entry_match_value[j]))

        #ternary well-formedness: value must have no bits outside mask, otherwise
        #(phv & mask) == value is unsatisfiable in Z3 (entry is dead) but P4
        #emits `value &&& mask` which interprets value & mask, flipping behavior.
        if(self.ternary_match):
            for i in range(table_size):
                constraints.append(self.entry_match_value[i] & ~self.entry_match_mask[i] == 0)
                
            
        self.solver.add(constraints)
        
        self.fields_fixed = False
        match ordering_type:
            case OrderingType.STATE_ORDERING:
                self.add_state_ordering_constraints()
            case OrderingType.FIELD_ORDERING:
                self.add_field_ordering_constraints()
            case OrderingType.FIELD_FIXING:
                self.add_field_fixing_constraints()
                self.fields_fixed = True
            case OrderingType.NO_ORDERING:
                pass
        
    '''
        The outermost if-else checks check if there is no rejection because of inability of extraction,
        Then we check if there is a table field which matches,
        After that we check if the state is not accept or reject -> forward to default next states,
        Otherwise, if it is accept or reject, they stay the same [anyway phv and pos also don't get updated]
        
        NOTE - cur_pos is guaranteed to be <=MAX_PACKET_SIZE
    '''    
    
    def transition(self,cur_state,cur_pos,cur_phv,field_sizes,packet,initial_phv):

        next_pos = cur_pos
        next_phv  = [cur_phv[i] for i in range(self.no_fields)]

        #When not_always_extract: extraction only fires the first time a field is
        #seen on this path (sentinel guard), table entries only fire on extracted
        #fields, and out-of-bounds reject only triggers when the state actually
        #attempts extraction. Otherwise: original always-extract encoding.
        for s in range(self.no_states):
            for f in range(self.no_fields):
                if(self.fields_fixed and s!=f):
                    continue
                for p in range(self.max_packet_size-field_sizes[f]+1):
                    g = And(cur_state==s,self.default_field[s]==f,cur_pos==p)
                    if self.not_always_extract:
                        g = And(g,next_phv[f]==initial_phv[f])
                    next_pos = If(g,p+field_sizes[f],next_pos)
                    next_phv[f] = If(g,
                                ZeroExt(self.max_field_size-field_sizes[f],Extract(p+field_sizes[f]-1,p,packet))
                                ,next_phv[f])

        next_state = cur_state #reject if reject and accept if accept

        for s in range(self.no_states):
            next_state = If(cur_state==s,self.default_next_state[s],next_state)

        for idx in range(self.table_size):
            for s in range(self.no_states):
                for f in range(self.no_fields):
                    if(self.fields_fixed and s!=f):
                        continue
                    if(self.ternary_match):
                        g = And(cur_state==s,self.default_field[s]==f,self.entry_state[idx]==s,
                                (next_phv[f]&self.entry_match_mask[idx])==self.entry_match_value[idx])
                    else:
                        g = And(cur_state==s,self.default_field[s]==f,self.entry_state[idx]==s,
                                next_phv[f]==self.entry_match_value[idx])
                    if self.not_always_extract:
                        g = And(g,next_phv[f]!=initial_phv[f])
                    next_state = If(g,self.entry_next_state[idx],next_state)

        for s in range(self.no_states):
            for f in range(self.no_fields):
                if(self.fields_fixed and s!=f):
                    continue
                for p in range(self.max_packet_size-field_sizes[f]+1,self.max_packet_size+1):
                    g = And(cur_state==s,self.default_field[s]==f,cur_pos==p)
                    if self.not_always_extract:
                        g = And(g,cur_phv[f]==initial_phv[f])
                    next_state = If(g,self.reject,next_state)

        return next_state,next_pos,next_phv
    
    def add_state_ordering_constraints(self):
        
        constraints = []
        
        for i in range(self.table_size):
            constraints.append(self.entry_next_state[i]>self.entry_state[i])
        
        for i in range(self.no_states):
            constraints.append(self.default_next_state[i]>i)
        
        self.solver.add(constraints)
    
    #It is not always necessary that a state with a greater number extracts a greater numbered field
    #Consider the case where a header tells what the next header should be and so on...
    #This OR state_ordering_constraints may be applied but NOT both
    def add_field_ordering_constraints(self):
        
        constraints = []
    
        for i in range(0,self.no_states):
            for j in range(i+1,self.no_states):
                constraints.append(self.default_field[j]>=self.default_field[i])
    
        self.solver.add(constraints)
        
    #An optimisation where it is known that only one state can extract a particular field
    #If no_states!=no_fields, the solver.check() is unsat always
    #This OR state_ordering_constraints may be applied but NOT both
    def add_field_fixing_constraints(self):
        
        constraints = []
        
        if (self.no_fields!=self.no_states):
            constraints.append(False)    
        
        for i in range(self.no_states):
            constraints.append(self.default_field[i]==i)
            
        self.solver.add(constraints)
    
    def add_correctness_constraint(self,field_sizes,initial_phv,packet,num_steps,desired_phv,accept_or_reject):
        #accept_or_reject - Z3py expression which says whether to accept or reject depending on input
        
        final_state,_,final_phv = self.simulate_stm(field_sizes,initial_phv,packet,num_steps)
        
        constraints=[]
        
        for f in range(self.no_fields):
            constraints.append(final_phv[f]==desired_phv[f])

        constraints.append(final_state==If(accept_or_reject,self.accept,self.reject))
        
        self.solver.add(constraints)
        
    def add_constant_synthesis_constraints(self,constants,mask_constants=[]):
        
        #TODO : analyse if it is worth doing separately for each field

        for i in range(self.table_size):
            constraints = []
            for c in constants:
                constraints.append(self.entry_match_value[i]==c)
            self.solver.add(Or(constraints))
        
        if(self.ternary_match):
            for i in range(self.table_size):
                constraints = []
                for c in mask_constants:
                    constraints.append(self.entry_match_mask[i]==c)
                self.solver.add(Or(constraints))

    def get_candidate_stm(self):
        #Assumes that check() has been called and is sa
        m = self.solver.model()
        def val(var, default=0):
            v = m[var]
            return v.as_long() if v is not None else default
        table_entries = []
        default_field = []
        default_next_state = []
        for i in range(self.table_size):
            if(self.ternary_match):
                table_entries.append((
                    val(self.entry_state[i]),
                    val(self.entry_next_state[i]),
                    val(self.entry_match_value[i]),
                    val(self.entry_match_mask[i])
                ))
            else:
                table_entries.append((
                    val(self.entry_state[i]),
                    val(self.entry_next_state[i]),
                    val(self.entry_match_value[i])
                ))
        for i in range(self.no_states):
            default_field.append(val(self.default_field[i]))
            default_next_state.append(val(self.default_next_state[i]))

        return table_entries,default_field,default_next_state

class STMVerifier(STMSolver):

    def __init__(self,table_entries,default_field,default_next_state,no_fields,max_packet_size,max_field_size,ternary_match,not_always_extract=True):

        super().__init__(len(table_entries),len(default_field),no_fields,max_packet_size,max_field_size,not_always_extract)

        self.table_entries = table_entries
        self.default_field = default_field
        self.default_next_state = default_next_state
        self.counterexample = BitVec('packet',self.max_packet_size)
        self.ternary_match = ternary_match

    def transition(self,cur_state,cur_pos,cur_phv,field_sizes,packet,initial_phv):

        next_pos = cur_pos
        next_phv  = [cur_phv[i] for i in range(self.no_fields)]

        for s in range(self.no_states):
            f = self.default_field[s]
            for p in range(self.max_packet_size-field_sizes[f]+1):
                g = And(cur_state==s,cur_pos==p)
                if self.not_always_extract:
                    g = And(g,next_phv[f]==initial_phv[f])
                next_pos = If(g,p+field_sizes[f],next_pos)
                next_phv[f] = If(g,
                                    ZeroExt(self.max_field_size-field_sizes[f],Extract(p+field_sizes[f]-1,p,packet))
                                    ,next_phv[f])

        next_state = cur_state

        for s in range(self.no_states):
            next_state = If(cur_state==s,self.default_next_state[s],next_state)

        for idx in range(self.table_size):
            for s in range(self.no_states):
                f = self.default_field[s]
                if(self.ternary_match):
                    g = And(cur_state==s,self.table_entries[idx][0]==s,
                            (next_phv[f]&BitVecVal(self.table_entries[idx][3],self.max_field_size))==BitVecVal(self.table_entries[idx][2],self.max_field_size))
                else:
                    g = And(cur_state==s,self.table_entries[idx][0]==s,
                            next_phv[f]==BitVecVal(self.table_entries[idx][2],self.max_field_size))
                if self.not_always_extract:
                    g = And(g,next_phv[f]!=initial_phv[f])
                next_state = If(g,self.table_entries[idx][1],next_state)

        for s in range(self.no_states):
            f = self.default_field[s]
            for p in range(self.max_packet_size-field_sizes[f]+1,self.max_packet_size+1):
                g = And(cur_state==s,cur_pos==p)
                if self.not_always_extract:
                    g = And(g,cur_phv[f]==initial_phv[f])
                next_state = If(g,self.reject,next_state)

        return next_state,next_pos,next_phv
    

    def add_verification_constraint(self,field_sizes,initial_phv,num_steps,spec):
        
        #accept_or_reject - Z3py expression which says whether to accept or reject depending on input
        
        final_state,_,final_phv = self.simulate_stm(field_sizes,initial_phv,self.counterexample,num_steps)
        
        constraints = []
        desired_output,accept_or_reject = spec(self.counterexample)
        
        for f in range(self.no_fields):
            constraints.append(final_phv[f]!=desired_output[f])

        constraints.append(final_state!=If(accept_or_reject,self.accept,self.reject))
                
        self.solver.add(Or(constraints))
    
    def get_counterexample(self):
        #Assumes check() is called and is sat
        m = self.solver.model()
        return m[self.counterexample]

def print_table(table_entries,default_field,default_next_state,ternary_match):
    print("\nTable entries:")
    for entry in table_entries:
        if(ternary_match):
            print(f"Current state: {entry[0]}, Next state: {entry[1]}, Match value: {entry[2]}, Match mask: {entry[3]}")
        else:
            print(f"Current state: {entry[0]}, Next state: {entry[1]}, Match value: {entry[2]}")
            
    print("\nDefault fields and next states:")
    for i in range(len(default_field)):
        print(f"State: {i}, Default field: {default_field[i]}, Default next state: {default_next_state[i]}")


#returns a valid parsing state machine with min no of states and minimum table entries as 
#(table entries specifying special transitions, default fields for states, default next states)

def find_stm(field_sizes,initial_phv,spec,min_num_states,max_num_states,min_num_entries,max_num_entries,max_packet_size,max_field_size,
             ordering_type=OrderingType.STATE_ORDERING,constant_synthesis=False,constants=None,debug=False,mask_constants=None,ternary_match=False,not_always_extract=True):

    #TODO - try iterating in another order, statically detect ranges for states
    #TODO - add certain fields which are for ternary matches - can we detect this also statically
    for table_size in range(min_num_entries,max_num_entries+1):
        for no_states in range(min_num_states,max_num_states+1):
            if(debug):
                print(f"no_states={no_states} && table_size={table_size}")
            stm = STMGenerator(table_size,no_states,len(field_sizes),max_packet_size,max_field_size,ordering_type,ternary_match,not_always_extract)

            if(constant_synthesis):
                
                if(constants is None):
                    raise ValueError("Need to provide valid constant list if constant synthesis is enabled")
                if(ternary_match and mask_constants is None):
                    raise ValueError("Need to provide valid mask constant list if constant synthesis and ternary match are enabled")
                stm.add_constant_synthesis_constraints(constants,mask_constants)
            
            #Start with one simple counterexample 0
            pkt = BitVecVal(0,max_packet_size)
            desired_phv,accept_or_reject = spec(pkt)
            stm.add_correctness_constraint(field_sizes,initial_phv,pkt,no_states,desired_phv,accept_or_reject)
            
            while True:
                if stm.is_sat():
                    
                    table_entries,default_field,default_next_state=stm.get_candidate_stm()
                    
                    if debug:
                        print(f"\nCandidate STM found for table size {table_size} and number of states {no_states}")
                        print_table(table_entries,default_field,default_next_state,ternary_match)
                        
                    
                    v = STMVerifier(table_entries,default_field,default_next_state,len(field_sizes),max_packet_size,max_field_size,ternary_match,not_always_extract)
                    
                    v.add_verification_constraint(field_sizes,initial_phv,no_states,spec)
                    
                    if v.is_sat():
                        
                        counterexample = v.get_counterexample()
                        
                        if debug:
                            print(f"Candidate STM doesn't parse the following packet correctly: {counterexample}\n")
                        
                        desired_phv,accept_or_reject = spec(counterexample)
                        
                        stm.add_correctness_constraint(field_sizes,initial_phv,counterexample,no_states,desired_phv,accept_or_reject)
                    
                    else:
                    
                        if debug:
                            print("An STM parsing all possible packets with given constraints found!")
                            print_table(table_entries,default_field,default_next_state,ternary_match)
                        
                        return table_entries,default_field,default_next_state
                                    
                else:
                    if(debug):
                        print(f"No valid candidate STMs for table size {table_size} and number of states {no_states}\n")
                    break

    raise STMNotFoundError
        