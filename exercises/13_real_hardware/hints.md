## Hint 1

`build_bell` is exercise 11's circuit with one extra line at the end, the one that
adds the measurement.

`to_isa` is two lines: build a pass manager, then run the circuit through it.
`generate_preset_pass_manager` is already imported for you.

## Hint 2

A pass manager is a transpiler that has been configured for one specific backend.
You build it, then you use it:

```python
pass_manager = generate_preset_pass_manager(optimization_level=1, backend=backend)
result = pass_manager.run(circuit)
```

`optimization_level` goes from 0 to 3. Level 1 is a sensible default: it does the
required rewriting plus light optimization, without spending a long time
searching.

Do not forget to `return` what `.run()` gives back. Returning the original
`circuit` is the mistake the exercise is built around.

## Hint 3

```python
def build_bell() -> QuantumCircuit:
    qc = QuantumCircuit(2)
    qc.h(0)
    qc.cx(0, 1)
    qc.measure_all()
    return qc


def to_isa(circuit: QuantumCircuit, backend) -> QuantumCircuit:
    pass_manager = generate_preset_pass_manager(optimization_level=1, backend=backend)
    return pass_manager.run(circuit)
```

Print `isa.count_ops()` afterwards if you want to see what your Hadamard turned
into. It is usually `rz` and `sx`.
