'''

Motivation for the table generator

Attempt 1::

Implementation of a CEGIS loop which spits out a table of entries
(All these optimisations are possible since we are ignoring Ternary matching )

What is the output format of this compilation phase ?

Must get the start,accept states.

(TODO : add support for reject states)

Each table entry signifies a transition 
1. current state
2. next state
3. field which should be extracted when current state is reached
4. boolean value which signifies if a comparison must be done or not (if false, then go to default state - should be unique for a given state)
5. value which the extracted field must be exactly matched with to reach the next state
   (must ensure a distinct condition amongst them else the state machine doesn't make any sense)

NOTE 

There should only be one default state

The table encodes a state machine which operates on a packet to give the desired set of output fields

NOTE 
We can fix field 1 extraction as the start state and fix an accept state

NOTE Question to think about :: Can I remove states and denote a state by the field which shall be extracted 
itself ? 

Specification format ?

1. Lengths of all fields - available from the C code
2. Default field value for each field when it's not extracted
3. Desired output dictionary in Z3py format.
4. Obviously number of fields!!!

(TODO:: an optimisation - if we make the assumption that the code given in C doesn't have ternary matches - i.e with bitwise operations and
ONLY exact matches - we could just constrain each of the table entries for a given state to be fixed to these values which would reduce our
search space considerably)

(TODO:: Can we relax this Assumption?
    We assume that every piece of data from the packet used in the code is extracted - there is an assigment. Arbitrary pointer derefs are
    NOT ALLOWED)
    
Procedure:
We shall iterate over the table entry size and then over the number of states
and keep synthesing things till we find unsat (run a cegis loop basically). After this proceed
to the next table size.
(Idea is to get the table entry of minimum size)

Inherently, since matching is not done on every single field, we will just have a bunch of states which have no branches, 
but since the C code given as input is an imperative one, we shall just have a DAG in this case, and we can end up merging these linear states
into a struct for simplicity 

(TODO:: Finally, since we don't want it to be cryptic, we would like to come up with a way to match these field names with the corresponding
names in C) 

Another salient feature - all those C code checks for packet bounds will be automatically taken care of in P4, if I can't extract something
I will drop it anyway. So, we can just discard these things while considering the C code. 
 
Attempt 2::(WRONG!!!)

Since everything involves the extraction of a field except the accept state - we shall just say that every state is bound to a given field.
So, we just end up having the number of states as the number of fields(field_cnt) + one accept state
(TODO :: Again, add reject state support also)
So, now each table entry need not have the field - we just say that state i extracts the ith field .
 
Additionally we fix state 0 as the start state and fix state (field_cnt+1) as the accept state.

(THIS IS INCORRECT BECAUSE OF THE FOLLOWING POINT - IF I HAD ONLY ONE STATE FOR EVERY FIELD EXTRACTION,
THEN IT MEANS THAT WHATEVER I HAVE EXTRACTED BEFORE DON'T ADD ANY INFORMATION TO THIS STATE - 
THIS CAN HAPPEN ONLY TO COMMON STATES - ASSUMING A GENERALIZATION OF THIS IS WRONG)

A POINT TO NOTE IS THAT IF A TRANSITION FROM A STATE DEPENDED ONLY ON THE CURRENT STATE - I.E
THE C CODE DOESN'T HAVE ANY DUPLICATIONS OF THE IF-ELSE STATEMENTS OR COMBINED CONDITIONS IN IF-ELSE

basically an example for which this fails is

if (field1==4){
    if(field2==3){
        goto state k;
    }
    else{
        goto state l;
    }
}
else if(field1==5){
    if(field2==4){
        goto state m;
    }
    else{
        goto state n;
    }
} 

k,l,m and n are new states with separate processing.


NOTE 
Thinking about attempt 1 - this would suffer as opposed the alloc[i][j] approach in ParserHawk
paper in the following way - for the above code I will definitely end up having two states extracting
field 2 which MAY be avoided in some cases thereby minimising the number of entries in the lookup table

TODO WHAT ABOUT THE SINGLE ALLOC IDEA FROM THE PAPER - CAN WE COME UP WITH A CASE WHERE A PARTICULAR
BIT MIGHT BE NEEDED IN TWO DIFFERENT STATE TRANSITIONS ?


NOTE

Why is attempt 1 a general enough outline ?

A very reasonable assumption is that everything is at the granularity of fields (which is good enough -
in fact even if you don't assume this, if there are other mixed constraints or something, with enough
number of table entries, you can get as much expressiveness as you want.)

Notice that we are allowing a particular field to be extracted by multiple states and the states get
to choose which field they shall extract and select on - when at a particular state, you can see
that a given set of field values and the remaining values not mentioned partition the space into 
a few parts. And they need not be invoked later.
'''
