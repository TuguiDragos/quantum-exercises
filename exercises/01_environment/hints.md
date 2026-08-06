## Hint 1

Two lines are enough. The first is an `import`. The second assigns to
`qiskit_version`.

Do not type the version number by hand, even if you know it. Ask the package.

## Hint 2

Almost every Python package stores its own version in an attribute named with two
leading and two trailing underscores. You have seen the pattern before in
`__init__` and `__main__`.

Try this in a terminal to see it:

```bash
uv run python -c "import qiskit; print(dir(qiskit))"
```

Look through the names that start with `__`.

## Hint 3

The attribute is `__version__`:

```python
import qiskit

qiskit_version = qiskit.__version__
```
