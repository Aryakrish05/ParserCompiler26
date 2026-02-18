#Sudoku solver
#Input size of small square in Sudoku
#Input board with values available and empty entries as zeroes

from z3 import *

def create_sudoku(n):
    X=[[Int('x_%s_%s' % (i,j)) for j in range(n*n)] for i in range(n*n)]
    s=Solver()

    s.add(Distinct(X[i*n+r][j*n+c] for r in range(n) for c in range(n)) for i in range(n) for j in range(n))

    s.add(Distinct(X[i][j] for j in range(n*n)) for i in range(n*n))

    s.add(Distinct(X[i][j] for i in range(n*n)) for j in range(n*n))

    s.add(And(X[i][j]>=1,X[i][j]<=n*n) for i in range(n*n) for j in range(n*n))
    
    return s

def print_solved_sudoku(s,n):
    if s.check() == sat:
        m = s.model()
        print("Solution:")
        for i in range(n*n):
            for j in range(n*n):
                val = m.eval(Int('x_%s_%s' % (i,j)))
                print(val, end=" ")
            print()
    else:
        print("No solution")
        
def sudoku():
    n=int(input("Enter the size of the Sudoku (n for n x n): "))
    solvers=create_sudoku(n) 
    print("Enter the Sudoku puzzle row by row (use 0 for empty cells):")   
    for i in range(n*n):
        row=input().split()
        for j in range(n*n):
            if row[j] != '0':
                solvers.add(Int('x_%s_%s' % (i,j)) == int(row[j]))
    print_solved_sudoku(solvers,n)
    
sudoku()