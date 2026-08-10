## Hint 1

Count the outcomes by hand for the first few sizes and the pattern falls out.

One qubit can be measured as `0` or `1`, so two amplitudes. Two qubits give `00`,
`01`, `10`, `11`, so four. Three qubits give eight. Adding a qubit does not add a
fixed amount, it doubles what was already there. Python spells that with `**`.

`quantum_bytes_for` then calls `amplitudes_for` and multiplies by
`BYTES_PER_AMPLITUDE`, which the file already gives you.

`classical_bytes_for` is the odd one out, and deliberately so. It has no `2**n`
anywhere in it. A classical register holds one value, so `n` bits cost `n` bits,
and bits become bytes by dividing by eight.

## Hint 2

```python
def amplitudes_for(n):
    return 2**n


def quantum_bytes_for(n):
    return amplitudes_for(n) * BYTES_PER_AMPLITUDE
```

For the last one, try `classical_bytes_for(9)` in your head before you write it.
Nine bits do not fit in one byte. They need two, and the second byte is mostly
empty. Any answer that gives 1 has rounded the wrong way, and `9 // 8` gives
exactly that.

Check the boundary too: 8 bits is 1 byte, 9 bits is 2, 16 bits is 2, 17 bits is 3.

## Hint 3

```python
def classical_bytes_for(n):
    return math.ceil(n / BITS_PER_BYTE)
```

`math` is already imported at the top of the file for you, so nothing to add.
`math.ceil` rounds up, which is what "how many whole bytes do I need" always
means.

If you would rather not lean on the import at all, `-(-n // BITS_PER_BYTE)` does
the same thing: negating twice around a floor division turns it into a ceiling.

Do not use `round`. It rounds to nearest, so nine bits would come back as one
byte and the two smallest cases in the checker would disagree with you.

Once all three pass, read the ratio column in the first artifact. That number is
the reason this exercise sits where it does in the course.
