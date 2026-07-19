# Theory — Reference

## SymPy Solve Examples by Kind

```python
import sympy as sp

# Algebraic equation
x = sp.symbols('x')
sp.solve(x**2 - 5*x + 6, x)                # [2, 3]

# System of linear equations
x, y = sp.symbols('x y')
sp.solve([x + y - 10, 2*x - y - 5], (x, y)) # {x: 5, y: 5}

# Ordinary differential equation
f = sp.Function('f')
sp.dsolve(sp.Eq(f(x).diff(x, x) + f(x), 0), f(x))
# Eq(f(x), C1*sin(x) + C2*cos(x))

# Transcendental (numerical solve)
sp.nsolve(sp.Eq(sp.exp(x) + x, 5), 0)        # 1.306...

# Matrix eigenvalue
M = sp.Matrix([[2, 1], [1, 2]])
M.eigenvals()                                # {1: 1, 3: 1}
```

- Use `sp.nsolve` for equations without closed-form solutions.
- Use `sp.solve` for linear/polynomial systems; `sp.solveset` for set-valued output.
- Always specify the variable(s) to solve for — omitting them can yield unexpected results.

## Asymptotic Notation Reference

| Notation | Form | Meaning | Example |
|----------|------|---------|---------|
| O (Big-O) | `f(n) <= c*g(n)` | Upper bound | `3n^2 + 2n` is O(n^2) |
| Omega | `f(n) >= c*g(n)` | Lower bound | `3n^2 + 2n` is Omega(n^2) |
| Theta | `f(n) = c*g(n)` | Tight bound | `3n^2 + 2n` is Theta(n^2) |
| o (little-o) | `f(n) < c*g(n)` | Strict upper | `n^2` is o(n^3) |
| omega | `f(n) > c*g(n)` | Strict lower | `n^2` is omega(n) |

**Master Theorem**: For `T(n) = aT(n/b) + f(n)`:
- If `f(n) = O(n^(log_b(a) - e))` => `T(n) = Theta(n^(log_b(a)))`.
- If `f(n) = Theta(n^(log_b(a)) * log^k(n))` => `T(n) = Theta(n^(log_b(a)) * log^(k+1)(n))`.
- If `f(n) = Omega(n^(log_b(a) + e))` and `a*f(n/b) <= c*f(n)` => `T(n) = Theta(f(n))`.

## Common Proof Patterns

| Pattern | Strategy | When to Use |
|---------|----------|-------------|
| Direct proof | Assume premises, derive conclusion | Simple implications |
| Contrapositive | Prove `not Q -> not P` for `P -> Q` | Implication with negative conclusion |
| Contradiction | Assume false, derive contradiction | Existence, irrationality, infinitude |
| Induction | Base case + inductive step | Properties over N, trees, recursion |
| Pigeonhole | n items into m < n boxes | Combinatorial existence |
| Invariant | Quantity preserved by all operations | Loop correctness, state machines |
