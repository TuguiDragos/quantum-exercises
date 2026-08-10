## Hint 1

The shape of the loop matters more than the arithmetic. One prepared state fills
one **column**, not one row.

Write the outer loop over the prepared label and the inner loop over the measured
label, and the indices land the right way round: `matrix[i][j]` with `j` the
prepared one and `i` the measured one.

Use `counts.get(measured, 0)` and not `counts[measured]`. An outcome that never
occurred is simply absent from the dict, and indexing it raises `KeyError`.

## Hint 2

```python
def response_matrix(columns):
    matrix = np.zeros((4, 4))
    for j, prepared in enumerate(LABELS):
        counts = columns[prepared]
        total = sum(counts.values())
        for i, measured in enumerate(LABELS):
            matrix[i, j] = counts.get(measured, 0) / total
    return matrix
```

Two things to check before moving on. `matrix.sum(axis=0)` should be four ones,
and the four biggest numbers in the matrix should be the diagonal. If your rows
sum to 1 instead of your columns, you have built the transpose, and the runner
will say so rather than letting it through.

For `corrected`, the equation to undo is `observed = A @ true`. You have `A` and
you have `observed`, so you are solving for `true`.

## Hint 3

```python
def corrected(matrix, counts):
    observed = np.array([counts.get(label, 0) for label in LABELS], dtype=float)
    true = np.linalg.solve(matrix, observed)
    return {label: float(value) for label, value in zip(LABELS, true, strict=True)}
```

`np.linalg.solve(A, b)` solves `A @ x = b` for `x`. You could equally write
`np.linalg.inv(matrix) @ observed` and get the same answer, but solving is one
step instead of two and is better behaved numerically, which matters more as the
matrix gets closer to singular.

`strict=True` on the zip is what this repository's linter asks for. It makes the
zip complain rather than silently truncate if the two sides ever stop matching in
length.

Do not clamp the negatives to zero. The last artifact exists to show you what the
raw method really produces, and clamping also breaks the shot total: the columns
each sum to 1, which is exactly what makes the total survive the solve.
