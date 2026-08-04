# readme-assets

Screenshots for the project README. Nothing here is referenced yet; add the
image, then link it from `README.md`.

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
