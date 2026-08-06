## Hint 1

For `qc_undo`, you already know the gate. Apply it twice, on qubit 0 both times.

For `qc_flip`, keep those two and put one gate between them. Exercise 07 listed
the single-qubit gates that touch only the `|1>` amplitude. You want the one that
multiplies it by -1.

For `coin_model_prediction`, read the question twice. It asks what the **wrong**
model predicts, not what you will measure.

## Hint 2

```python
qc_undo.h(0)
qc_undo.h(0)
```

That is it. Run it and watch every single shot come back as 0.

For `qc_flip`, the middle gate is `z`. And for the prediction: if a gate simply
randomises a bit, applying it a second time cannot un-randomise it, so the coin
model has to say 0.5 no matter how many times you apply it. That is exactly the
prediction the experiment destroys.

## Hint 3

```python
qc_undo = QuantumCircuit(1)
qc_undo.h(0)
qc_undo.h(0)

qc_flip = QuantumCircuit(1)
qc_flip.h(0)
qc_flip.z(0)
qc_flip.h(0)

coin_model_prediction = 0.5
```

Worth trying afterwards: replace `z` with `s`, which is a half-sized version of
the same idea. You land exactly halfway between the two behaviours, back at
50/50, and this time it really is random.
