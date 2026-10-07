"""Writes the small files around the page: manifest, robots, sitemap, llms.txt, CNAME and .nojekyll."""

import json
from pathlib import Path

import tomllib

WEB = Path(__file__).resolve().parents[1]
site, repo = WEB / "_site", WEB.parent
facts = json.loads((WEB / "_build/facts.json").read_text())
SITE = "https://quantum-exercises.tuguidragos.com/"
RAW = "https://raw.githubusercontent.com/TuguiDragos/quantum-exercises/main/"
manifest = {
    "name": "quantum-exercises",
    "short_name": "qx",
    "description": "Hands-on Qiskit exercises, from an empty laptop to a real QPU.",
    "start_url": "/",
    "display": "browser",
    "background_color": "#10121c",
    "theme_color": "#10121c",
    "icons": [
        {"src": "/icon-192.png", "sizes": "192x192", "type": "image/png"},
        {"src": "/icon-512.png", "sizes": "512x512", "type": "image/png"},
    ],
}
(site / "site.webmanifest").write_text(json.dumps(manifest, indent=2) + "\n")
(site / "robots.txt").write_text(f"User-agent: *\nAllow: /\n\nSitemap: {SITE}sitemap.xml\n")
(site / "sitemap.xml").write_text(f"""<?xml version="1.0" encoding="UTF-8"?>
<?xml-stylesheet type="text/css" href="/sitemap.css"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url>
    <loc>{SITE}</loc>
    <lastmod>{(WEB / "_build/modified.txt").read_text()}</lastmod>
  </url>
</urlset>
""")
(site / "CNAME").write_text("quantum-exercises.tuguidragos.com\n")
(site / ".nojekyll").write_text("")
acts = {}
for folder in sorted((repo / "exercises").iterdir()):
    meta = tomllib.loads((folder / "meta.toml").read_text())
    acts.setdefault(meta["act"], []).append(f"{folder.name[:2]} {meta['title']}")
course = "\n".join(f"- {act}: " + "; ".join(items) for act, items in acts.items())
(site / "llms.txt").write_text(f"""# quantum-exercises

> {facts["count_word"].capitalize()} free, hands-on exercises for learning Qiskit {facts["qiskit_major"]}, from an empty laptop to a quantum circuit on real IBM hardware, and then to the CHSH Bell inequality. You edit a file and run `qx run`; the runner checks the objects your code produces and explains what is wrong in quantum terms rather than as a Python traceback.

Install it with `uv tool install quantum-exercises`, copy the course with `qx init`, check the setup with `qx doctor`, and start with `qx next`. It needs basic Python and no quantum background. An IBM Quantum account is optional: every exercise runs on a local simulator, and only exercise {facts["hardware"]} can send a job to a real QPU, after asking. States are compared with `Statevector.equiv`, gates with `Operator.equiv`, and counts statistically, against the binomial standard error at 4 sigma or with a chi-square test. It runs on {facts["pythons"]} and is tested against {facts["stack"]}, and the course is verified on the 1st and the 15th of every month against the Qiskit that ships that day. It is free software under the MIT License, by Țugui Dragoș.

## Exercises

{course}

## Docs

- [README]({RAW}README.md): installation, commands, the exercises, how answers are checked, and real hardware
- [Contributing]({RAW}CONTRIBUTING.md): how to add an exercise, and every dependency with the reason it is there
- [Security]({RAW}SECURITY.md): reporting, and what the tool does with an IBM API key

## Optional

- [PyPI](https://pypi.org/project/quantum-exercises/): the package
- [Source code](https://github.com/TuguiDragos/quantum-exercises)
- [Why it exists](https://tuguidragos.com/i-built-a-place-to-practise-qiskit/): the article that introduced it
- [Sponsor](https://github.com/sponsors/TuguiDragos): GitHub Sponsors
- [Author](https://tuguidragos.com/about/): Țugui Dragoș
""")
print("site.webmanifest, robots.txt, sitemap.xml, llms.txt, CNAME, .nojekyll")
