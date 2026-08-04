# Security

## Reporting a vulnerability

Email **contact@tuguidragos.com**. Please do not open a public issue for
anything that could expose someone's credentials.

Include what you did, what happened, and what you expected. A proof of concept
helps but is not required. You will get an acknowledgement within a few days.

GitHub's private vulnerability reporting is also enabled on this repository, and
either route reaches the same person.

## What is supported

The latest commit on `main`. This is a course rather than a deployed service, so
there are no maintained release branches: if something needs fixing, it is fixed
on `main` and you pull.

## What this project touches

Two things are worth understanding before you clone it.

### 1. It can hold a long-lived IBM Quantum API key

Only if you ask it to. Every exercise runs on a local simulator without an
account, and `qx doctor --save-account` is the only command that writes one.

When you do use it:

- The key is stored by qiskit at `~/.qiskit/qiskit-ibm.json`, **in clear text**.
  That location is qiskit's, not this project's, and it sits outside the
  repository so it cannot be committed by accident.
- `qx` tightens that file to `0600` inside a `0700` directory immediately after
  saving, because qiskit writes it with whatever umask happens to be in force,
  which is normally world-readable.
- `qx doctor` warns when the file is readable by other local users, which catches
  accounts saved before this tool existed or saved by qiskit directly.
- The key is read without terminal echo. If the terminal cannot suppress echo,
  `qx` refuses to continue rather than printing it.
- No command prints the key, the instance CRN, or the file's contents. `qx
  doctor` reports the account label and channel only.

If you believe a key was exposed, revoke it at
<https://quantum.cloud.ibm.com> and save a new one.

### 2. It executes Python from the repository you cloned

This is the part worth thinking about, because it is not obvious.

`qx run` imports two files: your `exercise.py`, and the exercise's `check.py`.
Both run as ordinary Python in a child process. That child inherits your
environment, your filesystem and your network access. It is **not a sandbox**,
and it is not trying to be: `exercise.py` is code you wrote yourself, and
`check.py` is repository code reviewed like any other source file.

The consequence: **a `check.py` from a repository you clone can read
`~/.qiskit/qiskit-ibm.json` and send it anywhere.** Verified, not theoretical.

So treat this repository the way you would treat any other you are about to run:

- Clone from <https://github.com/TuguiDragos/quantum-exercises>, not from a fork
  you have not read.
- If you do use a fork, read its `exercises/*/check.py` first. They are short.
- On a shared machine, or if you would rather not have the key reachable at all,
  run with `QX_OFFLINE=1` and skip `qx doctor --save-account` entirely. The whole
  course works that way.

The child process is hardened against accidents rather than against malice. It
gets a time limit, a bounded output buffer, its own process group, no stdin, and
no working directory on `sys.path`. Those stop a runaway loop or a stray
`qiskit.py` from breaking your session. None of them stop deliberate code.

## What is not a vulnerability

- **The worker is not a sandbox.** Reported above, by design, and documented in
  `src/quantum_exercises/worker.py`. If you want isolation, run the course in a
  container or a virtual machine.
- **The API key is stored in clear text.** That is qiskit's storage format, not
  this project's choice. What is in scope is the file's permissions and anything
  this tool prints, both covered above.
- **`qx solution` reveals answers.** It is a teaching tool, not an exam.

## Keeping secrets out of the repository

An IBM Quantum API key is 44 generic alphanumeric characters. GitHub's push
protection does not recognise that shape, and neither does gitleaks out of the
box: a hardcoded key passes the default rule set untouched, which was verified
rather than assumed.

So the repository carries its own rule in
[`.gitleaks.toml`](.gitleaks.toml), which matches a key-shaped string assigned to
a token-like name, and it runs in two places:

- **pre-commit**, on staged changes, for anyone who ran `pre-commit install`
- **CI**, over the whole tree on every push and pull request, because installing
  hooks is opt-in and easy to skip

Notebook outputs are stripped by `nbstripout` on commit, since a cell that ran
against hardware can carry job identifiers.

## Automated runs never reach hardware

Both workflows set `QX_OFFLINE=1`, and so does the test suite. Nothing automated
can submit a job or spend someone's free QPU minutes.
