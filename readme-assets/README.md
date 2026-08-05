# readme-assets

Screenshots referenced by the project README. Replacing a file updates the page
without touching it, as long as the name stays the same.

## Naming

`NN-short-description.png`, numbered in the order they appear in the README, so
the folder reads in the same order as the page:

| File | What it shows |
|---|---|
| `01-qx-list.png` | the curriculum and your progress |
| `02-qx-run-fail.png` | a wrong answer, explained in the language of the problem |
| `03-qx-run-pass.png` | the same exercise passing, with statevector and histogram |
| `04-qx-doctor.png` | the environment check |
| `05-vscode-split.png` | the exercise file beside the terminal |
| `06-vscode-notebook.png` | the playground notebook with a rendered histogram |
| `07-qx-watch.png` | watch mode waiting on a save |
| `08-real-hardware.png` | exercise 13 on a real QPU |

## When a shot goes stale

Five of these were retaken for 0.5.0, when the course grew from 14 exercises in
three acts to 17 in four and `notebooks/` went from one file to four. What made
them stale is worth knowing, because the same things will do it again:

- **a count changes.** `01-qx-list.png` showed 14 rows and a 0/14 bar,
  `04-qx-doctor.png` reported "14 exercises found in".
- **the file tree is in shot.** The three VS Code shots show `exercises/` and
  `notebooks/` in the sidebar, so adding either puts them out of date.
- **the tool's own wording changes.** `07-qx-watch.png` carried the pre-0.3.4
  spelling of the run command, and a `__pycache__` directory from before the
  worker stopped writing one.

`02-qx-run-fail.png`, `03-qx-run-pass.png` and `08-real-hardware.png` survived
all of that: each shows one run of one exercise, with no tree and no totals.
Framing a shot that way is what makes it last.

Shots 1 to 3 and 5 to 7 come from a throwaway copy of the repository, so the
progress shown is chosen rather than whatever happens to be finished, and so
nothing in the sidebar belongs to whoever took the picture. Exclude `.venv`,
`.git`, `.DS_Store` and any editor or assistant directory from that copy, and
hide the caches through `files.exclude`.

## Capture settings

Keep these identical across every shot, or the set looks assembled rather than
designed.

| Setting | Value |
|---|---|
| Terminal width | 100 columns, checked with `tput cols` |
| Font | any mono with box-drawing glyphs, 15pt or 16pt |
| Theme | one dark theme, the same one in every shot |
| Window | drop shadow, no desktop behind it |
| Format | PNG, 2x pixel density on a retina display |

Shots 1 to 3 and 7 are taken against the demo tree, so the progress shown is
deliberate rather than whatever you happen to have finished.

## What the output does and does not reveal

Checked rather than assumed: `qx doctor` prints no API key, no CRN and no
account credentials. What it does print is the account label, for example
`default-ibm-quantum-platform`, and absolute paths that contain your username.
Neither is a secret, so the shot is safe to publish as it is.

The one thing worth watching is shot 8, which runs on a real QPU. The result
panel names the backend and the job's counts, none of it sensitive.
