# Enumerative CEGIS solver

Given a specification function for verification and some set of examples with expected results, CEGIS_Solver.solve can return an AST of an expression equivalent to the specification adhering to the grammar mentioned below:

    E ::= variable | constant | E+E | E*E | Ifthenelse(C,E,E)
    C ::= True | False | E>E | E==E | C&&C | C||C | !C

