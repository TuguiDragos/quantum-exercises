# quantum-exercises.tuguidragos.com

The website is built from this repository, so its figures follow the course instead of being typed
into the page:

| On the page | Read from |
| --- | --- |
| The exercises, their acts, and what each one leaves you with | each exercise's `meta.toml`, and the table in the README |
| Which exercise reaches for real hardware | the `hardware` flag in `meta.toml` |
| Tests | `pytest --collect-only` on this tree, without the deselected hardware test |
| Supported Pythons | the CI matrix, checked against `requires-python` and the classifiers |
| The locked Qiskit stack | `uv.lock` |
| Exercise 11, before and after the fix | qx run on a fresh `qx init` copy of the course |
| The 404 terminal | qx run on an exercise that does not exist |
| Every command | the command table in the README |
| The version | `pyproject.toml` |

A sentence the page quotes from the docs is checked against them, and every figure is checked for
consistency with the files it comes from. When one no longer holds, the build stops with the reason
instead of publishing a page that says something untrue, and the site already online stays as it
was. A notebook added to `notebooks/` stops the build too, until it is given a line in
`scripts/build_site.py`.

The page is dated by what it says, not by when it was built: the build compares the page with the
one already online and keeps that page's date unless something on it changed, so `dateModified` and
the sitemap's `lastmod` only move when the page does. `sitemap.css` gives `sitemap.xml` a readable
look in a browser; it is CSS rather than XSLT, which Chrome removes on November 17, 2026.

## How it is published

`.github/workflows/website.yml` builds the site on every push to `main` and publishes it to GitHub
Pages. Once, in the repository's **Settings > Pages**: set **Source** to **GitHub Actions**, and
**Custom domain** to `quantum-exercises.tuguidragos.com`. At the DNS provider, `quantum-exercises`
is a `CNAME` to `tuguidragos.github.io`.

## Building it locally

```bash
uv sync --all-extras --dev
npm ci --prefix website
website/build.sh
```

It needs Node.js 24 as well. The page is then in `website/_site`. Serve it with
`python -m http.server -d website/_site` and open <http://localhost:8000>.

## What lives where

| Path | What it is |
| --- | --- |
| `scripts/` | the build: the page, the 404, `llms.txt`, the manifest, robots, sitemap |
| `static/` | copied as is: the stylesheet, the script, the icons, the screenshots, the share image |
| `theme/` | Tapetum Quantum, which colors exercise 11's code |
| `tools/` | run by hand, only when a picture should change |

`tools/make_images.py` remakes the screenshots from `readme-assets`
(`uv run --with pillow python website/tools/make_images.py`). `tools/make_favicons.mjs` remakes
every icon from `tools/favicon-source.svg`, a Bell state's histogram: two tall bars for `00` and
`11`, and the two short ones a real device adds. `tools/make_card.mjs` remakes the share image and
`_build/github-social-preview.png`, the picture to upload in **Settings > Social preview**. Those
two need Playwright once: `npm install --no-save --prefix website playwright@1`, then
`npx --prefix website playwright install chromium`.
