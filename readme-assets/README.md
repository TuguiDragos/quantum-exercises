# readme-assets

Screenshots for the project README. Nothing here is referenced yet; add the
image, then link it from `README.md`.

## Naming

`NN-short-description.png`, numbered in the order they appear in the README, so
the folder reads in the same order as the page:

```
01-qx-list.png
02-qx-run-fail.png
03-qx-run-pass.png
04-qx-doctor.png
05-vscode-split.png
06-vscode-notebook.png
07-qx-watch.png
08-real-hardware.png
```

## Capture settings

Keep these identical across every shot, or the set looks assembled rather than
designed.

| Setting | Value |
|---|---|
| Terminal width | 100 columns for run output, 84 for `qx list` |
| Font | any mono with box-drawing glyphs, 15pt or 16pt |
| Theme | one dark theme, the same one in every shot |
| Window | rounded corners with a drop shadow, no desktop behind it |
| Format | PNG, 2x pixel density on a retina display |

## Before you publish

Two commands print your home directory, and one prints your IBM account name:

- `qx doctor` shows `/Users/<you>/...` and the saved account
- `qx version` and any error panel can show a full path

Either crop those out, or run the capture with `HOME` pointed at a scratch
directory, which the tutorial explains.
