"""Builds the website of quantum-exercises from the repository it sits in: the exercises' own metadata, what qx
prints for exercise 11 and for an exercise that does not exist, the test suite, and the workflows. Every figure is read
here, on every build, so the page grows with the course; a sentence the page quotes from the docs is checked against
them, and a build whose claim no longer holds stops rather than publishing it."""

import datetime
import html
import json
import re
import subprocess
import urllib.request
from pathlib import Path

import tomllib

WEB = Path(__file__).resolve().parents[1]
repo = WEB.parent
WORK, out_dir = WEB / "_build", WEB / "_site"
THEME = WEB / "theme/quantum-dark.json"

SITE = "https://quantum-exercises.tuguidragos.com/"
REPO = "https://github.com/TuguiDragos/quantum-exercises"
PYPI = "https://pypi.org/project/quantum-exercises/"
UV = "https://docs.astral.sh/uv/"
SPONSOR = "https://github.com/sponsors/TuguiDragos"
ARTICLE = (
    "I could not find a place to practise Qiskit, so I built one",
    "https://tuguidragos.com/i-built-a-place-to-practise-qiskit/",
)
INSTALL = "uv tool install quantum-exercises"
ONES = [
    "zero",
    "one",
    "two",
    "three",
    "four",
    "five",
    "six",
    "seven",
    "eight",
    "nine",
    "ten",
    "eleven",
    "twelve",
    "thirteen",
    "fourteen",
    "fifteen",
    "sixteen",
    "seventeen",
    "eighteen",
    "nineteen",
]
TENS = ["twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety"]


def word(n):
    if n < 20:
        return ONES[n]
    tens, ones = divmod(n, 10)
    return TENS[tens - 2] + (f"-{ONES[ones]}" if ones else "")


def esc(text):
    return html.escape(text, quote=True)


readme = (repo / "README.md").read_text()
pyproject = tomllib.loads((repo / "pyproject.toml").read_text())
version = pyproject["project"]["version"]
ci = (repo / ".github/workflows/ci.yml").read_text()
PYTHONS = re.findall(r'"(3\.\d+)"', re.search(r"python-version: \[(.+?)\]", ci).group(1))
assert pyproject["project"]["requires-python"] == f">={PYTHONS[0]}"
assert [
    c.rsplit(" :: ", 1)[1]
    for c in pyproject["project"]["classifiers"]
    if re.fullmatch(r"Programming Language :: Python :: 3\.\d+", c)
] == PYTHONS
PYTHON_RANGE = f"Python {PYTHONS[0]} to {PYTHONS[-1]}"
PYTHON_LIST = ", ".join(PYTHONS[:-1]) + f" and {PYTHONS[-1]}"

# The course, from each exercise's own meta.toml, and what the README says each one leaves you with.
exercises = []
for folder in sorted((repo / "exercises").iterdir()):
    meta = tomllib.loads((folder / "meta.toml").read_text())
    number = folder.name[:2]
    row = re.search(rf"^\| {number} \| {re.escape(meta['title'])} \| (.+?) \|$", readme, re.M)
    assert row, (number, meta["title"])
    exercises.append(
        {
            "number": number,
            "slug": folder.name,
            "title": meta["title"],
            "act": meta["act"],
            "takeaway": row.group(1),
            "hardware": meta.get("hardware", False),
        }
    )
acts = []
for e in exercises:
    if not acts or acts[-1][0] != e["act"]:
        acts.append((e["act"], []))
    acts[-1][1].append(e)
assert len({act for act, _ in acts}) == len(acts), "each act's exercises are numbered together"
COUNT, ACTS = len(exercises), word(len(acts))
COUNT_WORD = word(COUNT)
TITLE = f"quantum-exercises: {COUNT} Hands-On Qiskit Exercises"
DESCRIPTION = (
    f"{COUNT_WORD.capitalize()} hands-on Qiskit exercises, from an empty laptop to real IBM quantum hardware. "
    "One command checks your answer and explains what is wrong."
)
assert len(DESCRIPTION) <= 160, len(DESCRIPTION)
by_slug = {e["slug"].split("_", 1)[1]: e["number"] for e in exercises}
hardware = [e["number"] for e in exercises if e["hardware"]]
assert len(hardware) == 1, "the page says exactly one exercise reaches for real hardware"
HW, MIGRATION, HONEST, FIRST = (
    hardware[0],
    by_slug["migration"],
    by_slug["honest_reading"],
    exercises[0]["number"],
)
assert by_slug["real_hardware"] == HW and int(HONEST) == int(HW) + 1, (
    "the honest reading follows the hardware run it reads"
)
BELL = by_slug["bell_entanglement"]
assert BELL == "11", "the hero shows exercise 11 by number, in the code and in the share image"


def code_html(text):
    return re.sub(r"`([^`]+)`", r"<code>\1</code>", esc(text))


def command_html(command):
    """A command that may break only between its words, or after a slash of an address too long for the line."""
    words = []
    for word in command.split(" "):
        if "://" in word:
            scheme, rest = word.split("://", 1)
            words.append(esc(scheme) + "://" + "/<wbr>".join(esc(part) for part in rest.split("/")))
        else:
            words.append(f'<span class="cmd">{esc(word)}</span>')
    return " ".join(words)


def typeset(text, sentence=False):
    """Text from the course as the page sets it: a typographic apostrophe outside code, and a takeaway that ends
    like the sentence it is."""
    parts = re.split(r"(`[^`]+`)", text)
    text = "".join(
        part if part.startswith("`") else re.sub(r"(?<=\w)'(?=\w)", "’", part) for part in parts
    )
    return text + "." if sentence and not text.endswith((".", "!", "?")) else text


act_html = []
for act, items in acts:
    numeral, name = act.split(" - ", 1)
    rows = "".join(
        f'<li><span class="num">{e["number"]}</span><div><h4>{esc(typeset(e["title"]))}</h4>'
        f"<p>{code_html(typeset(e['takeaway'], sentence=True))}</p></div></li>"
        for e in items
    )
    act_html.append(
        f'<article class="act reveal"><p class="act-name">{esc(numeral)}</p><h3>{esc(name)}</h3><ol class="lessons">{rows}</ol></article>'
    )

# The test suite on this checkout, as pytest collects it (the hardware test is deselected by default, so it is not
# counted), and what CI and the scheduled verification run.
tests = sum(int(n) for n in re.findall(r": (\d+)$", (WORK / "collect.txt").read_text(), re.M))
verify = (repo / ".github/workflows/verify.yml").read_text()
assert "uv run pytest -q" in ci
assert '- cron: "23 6 1 * *"' in verify and '- cron: "23 6 15 * *"' in verify
assert "os: [ubuntu-latest, macos-latest, windows-latest]" in verify
# Which job runs on which date: the operating systems on the 1st only, the fresh resolution and the next-major probe on
# both dates, as the page says.
jobs = dict(
    re.findall(r"^  (\w+):\n(.*?)(?=^  \w+:\n|\Z)", verify.split("\njobs:\n", 1)[1], re.M | re.S)
)
assert set(jobs) == {"locked", "wheel", "latest", "preview"}, sorted(jobs)
for job in ("locked", "wheel"):
    assert re.search(r"^    if: github\.event\.schedule != '23 6 15 \* \*'$", jobs[job], re.M), job
    assert "matrix.os" in jobs[job], job
for job in ("latest", "preview"):
    assert not re.search(r"^    if:", jobs[job], re.M), job
assert (
    "uv sync --upgrade" in jobs["latest"] and "qiskit[visualization]>=3.0.0.dev0" in jobs["preview"]
)
assert "fail_under = 100" in (repo / "pyproject.toml").read_text()
checks = (repo / "src/quantum_exercises/checks.py").read_text()
assert "Z_THRESHOLD = 4.0" in checks and "from scipy.stats import chi2" in checks
cli = (repo / "src/quantum_exercises/cli.py").read_text()
assert (
    "HARDWARE_WINDOW_SECONDS = 3 * 60 * 60" in cli
    and "Send it now? Answering no changes nothing and costs nothing" in cli
)
assert "job(s) ahead of you" in cli and "os.chmod(CREDENTIALS_PATH, 0o600)" in cli
backends = (repo / "src/quantum_exercises/backends.py").read_text()
assert 'FAKE_BACKEND = "FakeManilaV2"' in backends and "AerSimulator.from_backend(fake)" in backends
check11 = (repo / "exercises/11_bell_entanglement/check.py").read_text()
assert "StatevectorSampler(seed=99)" in check11
lock = (repo / "uv.lock").read_text()
STACK = {
    name: re.search(rf'name = "{name}"\nversion = "([^"]+)"', lock).group(1)
    for name in ("qiskit", "qiskit-ibm-runtime", "qiskit-aer")
}
QISKIT_MAJOR = STACK["qiskit"].split(".")[0]
STACK_SENTENCE = (
    f"Qiskit {STACK['qiskit']}, qiskit-ibm-runtime {STACK['qiskit-ibm-runtime']} and qiskit-aer "
    f"{STACK['qiskit-aer']}"
)

# What qx printed for exercise 11 in a fresh course, before and after the fix, written by build.sh.
fail_out = (WORK / "bell-fail.txt").read_text()
pass_out = (WORK / "bell-pass.txt").read_text()
for needle in [
    "Your circuit does not prepare (|00> + |11>) / sqrt(2).",
    "Your probabilities:   {'00': 1.0000}",
    "Target probabilities: {'00': 0.5000, '11': 0.5000}",
    "Note: global phase is ignored, so a phase difference is not the problem here.",
]:
    assert needle in fail_out, needle
for needle in [
    "|00>       0.707       0.5000",
    "|11>       0.707       0.5000",
    "2048 shots: the two qubits always agree",
    "972   47.5%",
    "1076   52.5%",
    "PASS  11_bell_entanglement",
]:
    assert needle in pass_out, needle

start = (repo / "exercises/11_bell_entanglement/template.py").read_text()
solution = (repo / "exercises/11_bell_entanglement/solution.py").read_text()
before_code = start.split('"""', 2)[2].strip()
after_code = solution.split('"""', 2)[2].strip()
UV_INSTALL = "curl -LsSf https://astral.sh/uv/install.sh | sh"
UV_WINDOWS = 'powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"'
assert UV_INSTALL in readme and UV_WINDOWS in readme and INSTALL in readme
snippets = WORK / "snippets.json"
snippets.write_text(
    json.dumps(
        [
            {"id": "before", "code": before_code, "lang": "python"},
            {"id": "after", "code": after_code, "lang": "python"},
        ]
    )
)
subprocess.run(
    [
        "node",
        str(WEB / "scripts/highlight.mjs"),
        str(THEME),
        str(snippets),
        str(WORK / "colored.json"),
    ],
    check=True,
)
COLORED = json.loads((WORK / "colored.json").read_text())

# Every command, as the README's table lists it, so a new one reaches the page with it.
COMMANDS = re.findall(r"^\| `(qx [^`]+)` \| (.+?) \|$", readme, re.M)
assert ("qx run [n]", "check an exercise") in COMMANDS, "the README's command table"
commands_html = "".join(
    f'<tr><td><code class="cmd">{esc(c)}</code></td><td>{esc(w[0].upper() + w[1:])}</td></tr>'
    for c, w in COMMANDS
)

NOTEBOOKS = [
    ("playground.ipynb", "Scratch space. Change numbers, see what moves."),
    (
        "lab-1-qiskit-patterns.ipynb",
        "The four steps of any program that touches real hardware: map, optimize, execute, post-process.",
    ),
    (
        "lab-2-noise.ipynb",
        "Readout error against gate error, measured on a real device’s published rates.",
    ),
    (
        "lab-3-dynamic-circuits.ipynb",
        "Measuring partway through and branching on the result, ending in teleportation.",
    ),
]
assert sorted(n for n, _ in NOTEBOOKS) == sorted(
    p.name for p in (repo / "notebooks").glob("*.ipynb")
)
# Each line says what its notebook says it does, so a rewritten notebook stops the build until its line follows.
for name, needles in {
    "lab-1-qiskit-patterns": [
        "Every Qiskit program that touches real hardware has the same four steps",
        "post-process",
    ],
    "lab-2-noise": ["readout", "gate error", "Both numbers are published"],
    "lab-3-dynamic-circuits": ["measures partway through", "teleport"],
}.items():
    cells = json.loads((repo / f"notebooks/{name}.ipynb").read_text())["cells"]
    text = " ".join("".join(cell["source"]) for cell in cells).replace("\n", " ")
    for needle in needles:
        assert needle.lower() in text.lower(), (name, needle)
NOTEBOOK_WORD = word(len(NOTEBOOKS)).capitalize()
notebooks_html = "".join(
    f"<tr><td><code>{n.replace('.ipynb', '<wbr>.ipynb')}</code></td><td>{esc(d)}</td></tr>"
    for n, d in NOTEBOOKS
)

GALLERY = [
    (
        "Side by side",
        "05-vscode-split",
        "VS Code with exercise.py open on the left and the integrated terminal on the right, showing a passing run of exercise 11.",
        "A course made by <code>qx init</code> needs no editor setup: <code>qx</code> is on your PATH, so any terminal in the folder runs it.",
    ),
    (
        "Watch mode",
        "07-qx-watch",
        "Watch mode running in the VS Code terminal, showing a failed check followed by the line: watching exercises/11_bell_entanglement/exercise.py, save to re-run, Ctrl-C to stop.",
        "<code>qx watch</code> re-runs on every save, and moves on to the next exercise by itself when one passes.",
    ),
    (
        "The noise lab",
        "06-vscode-notebook",
        "The noise lab open in VS Code, showing an executed cell that runs the same Bell pair on three different pairs of physical qubits, and a table where the measured fidelity, 0.94, 0.88 and 0.97, tracks what the published readout rates predict.",
        "The labs are where you are shown rather than checked, at a length an exercise cannot afford.",
    ),
    (
        "qx doctor",
        "04-qx-doctor",
        "qx doctor --online listing ten checks, all reading ok: Python, uv, the Qiskit SDK, the Aer simulator, the IBM Runtime client, a circuit smoke test, the visualization extra, twenty exercises, the saved IBM Quantum account, and a live connection reporting three QPUs on the open plan.",
        "Every check names the problem and the fix. Only <code>--online</code> asks IBM anything; plain <code>qx doctor</code> never touches the network.",
    ),
]
for _, name, alt, _ in GALLERY:
    assert alt in readme, name


def webp_header(path):
    """A WebP's width and height, and whether it kept its alpha channel, from the header alone."""
    head = path.read_bytes()[:30]
    assert head[:4] == b"RIFF" and head[8:16] == b"WEBPVP8X", path.name
    width = 1 + int.from_bytes(head[24:27], "little")
    height = 1 + int.from_bytes(head[27:30], "little")
    return width, height, bool(head[20] & 0x10)


def picture(name, alt, sizes, eager=False):
    files = {
        int(p.stem.rsplit("-", 1)[1]): p for p in (WEB / "static/images").glob(f"{name}-*.webp")
    }
    assert {800, 1200} <= set(files), name
    for path in files.values():
        assert webp_header(path)[2], (
            f"{path.name} lost its transparency, so its rounded corners would turn black"
        )
    w, h, _ = webp_header(files[1200])
    srcset = ", ".join(f"images/{name}-{x}.webp {x}w" for x in sorted(files))
    loading = "" if eager else ' loading="lazy" decoding="async"'
    return (
        f'<img src="images/{name}-1200.webp" srcset="{srcset}" sizes="{sizes}" width="{w}" height="{h}"'
        f'{loading} alt="{esc(alt)}">'
    )


SHOT_SIZES = "(max-width: 640px) calc(100vw - 32px), (max-width: 1124px) calc(100vw - 44px), 1080px"
shot_tabs, shot_panels = [], []
for i, (label, name, alt, caption) in enumerate(GALLERY):
    slug = "shot-" + name.split("-", 1)[1]
    shot_tabs.append(
        f'<li><button type="button" data-tab="{slug}" aria-pressed="{"true" if i == 0 else "false"}" aria-controls="{slug}">{esc(label)}</button></li>'
    )
    shot_panels.append(f'''<figure class="panel shot{" active" if i == 0 else ""}" id="{slug}">
            <a href="images/{name}-1600.webp">{picture(name, alt, SHOT_SIZES)}</a>
            <figcaption>{caption}</figcaption>
          </figure>''')
HARDWARE_ALT = (
    "Exercise 14 run on ibm_marrakesh, a real IBM QPU. The queue question is answered yes, then the histogram shows "
    "1024 shots: 00 at 49.0 percent, 11 at 48.4 percent, and 01 and 10 together at 2.54 percent. The summary "
    "reports the circuit as submitted, its ISA form, and that the disagreeing shots are noise rather than a bug."
)
assert HARDWARE_ALT in readme

FAQ = [
    (
        "What is quantum-exercises?",
        f"{COUNT_WORD.capitalize()} free, hands-on exercises for learning Qiskit, IBM’s quantum computing SDK. You edit a file, run one command, "
        "and it tells you what is wrong in the language of the problem rather than as a Python traceback. The course goes "
        "from an empty laptop to a circuit on real IBM hardware, and then to the Bell inequality.",
    ),
    (
        "Do I need to know quantum physics or linear algebra?",
        "No. You need basic Python: variables, functions, and dictionaries. No quantum background, and no linear algebra "
        "beyond multiplying a small matrix by a vector. Where a matrix shows up, the runner prints it.",
    ),
    (
        "Do I need an IBM Quantum account?",
        f"No. Every exercise runs on a local simulator without one. Only exercise {HW} reaches for real hardware, and it asks "
        "before it sends anything; without an account it runs on a simulator with a noise model copied from a real device.",
    ),
    (
        "How long does the course take?",
        "Act I takes well under an hour. The whole course is an afternoon or two, depending on how much you stop to poke at "
        "things.",
    ),
    (
        "Which version of Qiskit does it teach?",
        f"Qiskit {QISKIT_MAJOR}. It is tested against {STACK_SENTENCE}, and verified on the "
        "1st and the 15th of every month against the Qiskit that ships that day.",
    ),
    (
        "Why do so many Qiskit tutorials fail with an ImportError?",
        "Most were written for Qiskit 0.x. <code>execute()</code> was removed, <code>Aer</code> moved to its own package, "
        f"<code>IBMQ</code> became something else entirely, and the shape of results changed. Exercise {MIGRATION} teaches the "
        "migration, so every old tutorial becomes usable again.",
    ),
    (
        "Can it spend my QPU time without asking?",
        "No. Nothing automated reaches a QPU: a script, a CI job, an editor task and watch mode all stay on the local "
        f"simulator. <code>qx run {HW}</code> shows the least busy QPU and asks before sending, and answering no costs nothing.",
    ),
    ("Is it free?", "Yes. quantum-exercises is free and open source under the MIT License."),
]
for needle in [
    "Act I takes well under an hour",
    "Every exercise runs on a local simulator without one",
    "Nothing automated reaches a QPU",
    "`execute()` was removed, `Aer` moved to its",
]:
    assert needle in readme.replace("\n", " "), needle
faq_html = "\n".join(f"<details><summary>{q}</summary><p>{a}</p></details>" for q, a in FAQ)


def plain(text):
    return html.unescape(re.sub(r"<[^>]+>", "", text))


PERSON = "https://tuguidragos.com/#person"
SAME_AS = [
    "https://www.linkedin.com/in/tuguidragos/",
    "https://github.com/TuguiDragos",
    "https://x.com/TuguiDragos",
    "https://www.facebook.com/TuguiDragos/",
    "https://www.instagram.com/tuguidragos/",
    "https://n8n.io/creators/tuguidragos/",
    "https://www.credly.com/users/tuguidragos",
    "https://tuguidragos.gumroad.com",
    "https://bsky.app/profile/tuguidragos.com",
    "https://mastodon.social/@tuguidragos",
    "https://www.threads.com/@tuguidragos",
    "https://www.tiktok.com/@tuguidragos",
    "https://www.youtube.com/@TuguiDragos",
]
PROFILES = [
    ("GitHub", "https://github.com/TuguiDragos"),
    ("LinkedIn", "https://www.linkedin.com/in/tuguidragos/"),
    ("X", "https://x.com/TuguiDragos"),
    ("Credly", "https://www.credly.com/users/tuguidragos"),
    ("Bluesky", "https://bsky.app/profile/tuguidragos.com"),
    ("Mastodon", "https://mastodon.social/@tuguidragos"),
    ("Instagram", "https://www.instagram.com/tuguidragos/"),
    ("YouTube", "https://www.youtube.com/@TuguiDragos"),
]
MIT = "https://spdx.org/licenses/MIT.html"
ld = {
    "@context": "https://schema.org",
    "@graph": [
        {
            "@type": "WebSite",
            "@id": SITE + "#website",
            "url": SITE,
            "name": "quantum-exercises",
            "inLanguage": "en-US",
            "publisher": {"@id": PERSON},
        },
        {
            "@type": "WebPage",
            "@id": SITE + "#webpage",
            "url": SITE,
            "name": TITLE,
            "description": DESCRIPTION,
            "inLanguage": "en-US",
            "isPartOf": {"@id": SITE + "#website"},
            "about": {"@id": SITE + "#course"},
            "mainEntity": {"@id": SITE + "#course"},
            "primaryImageOfPage": SITE + "images/social.png",
            "dateModified": datetime.date.today().isoformat(),
        },
        {
            "@type": "Person",
            "@id": PERSON,
            "name": "Țugui Dragoș",
            "alternateName": [
                "Tugui Dragos",
                "Țugui Dragoș-Constantin",
                "Tugui Dragos-Constantin",
                "Dragoș Țugui",
                "Dragos Tugui",
            ],
            "url": "https://tuguidragos.com/",
            "image": "https://tuguidragos.com/content/images/2026/06/Dragos-Tugui.webp",
            "jobTitle": "Automation & AI Systems Builder",
            "sameAs": SAME_AS,
        },
        {
            "@type": "Course",
            "@id": SITE + "#course",
            "name": "quantum-exercises",
            "description": f"{COUNT_WORD.capitalize()} hands-on exercises that take you from an empty laptop to a quantum circuit on real IBM "
            "hardware, and then to the Bell inequality. Each answer is checked by inspecting the objects your "
            "code produces, and feedback is given in quantum terms rather than as a Python traceback.",
            "url": SITE,
            "sameAs": [REPO],
            "image": SITE + "images/social.png",
            "inLanguage": "en-US",
            "provider": {"@id": PERSON},
            "author": {"@id": PERSON},
            "isAccessibleForFree": True,
            "offers": {"@type": "Offer", "price": "0", "priceCurrency": "USD", "category": "Free"},
            "educationalLevel": "Beginner",
            "learningResourceType": "Exercise",
            "coursePrerequisites": "Basic Python: variables, functions, and dictionaries",
            "teaches": [
                f"Qiskit {QISKIT_MAJOR}",
                "Quantum circuits",
                "Measurement and counts",
                "Statevectors and global phase",
                "Gates as matrices",
                "Interference",
                "Deutsch's algorithm",
                "Bell states",
                "Transpilation",
                "Readout error mitigation",
                "The Estimator primitive",
                "The CHSH inequality",
            ],
            "syllabusSections": [
                {
                    "@type": "Syllabus",
                    "name": act,
                    "description": "; ".join(f"{e['number']} {typeset(e['title'])}" for e in items),
                }
                for act, items in acts
            ],
            "license": MIT,
        },
        {
            "@type": "SoftwareApplication",
            "@id": SITE + "#app",
            "name": "quantum-exercises",
            "alternateName": "qx",
            "url": SITE,
            "sameAs": [REPO, PYPI],
            "description": "The qx command line runner: it copies the course, checks each exercise in quantum "
            "terms, gives hints, watches files, and tracks progress.",
            "applicationCategory": "EducationalApplication",
            "operatingSystem": "macOS, Windows, Linux",
            "softwareRequirements": f"{PYTHON_RANGE}, installed by uv",
            "softwareVersion": version,
            "downloadUrl": PYPI,
            "installUrl": PYPI,
            "isAccessibleForFree": True,
            "offers": {"@type": "Offer", "price": "0", "priceCurrency": "USD"},
            "license": MIT,
            "author": {"@id": PERSON},
            "image": SITE + "images/social.png",
        },
        {
            "@type": "SoftwareSourceCode",
            "@id": "https://tuguidragos.com/#quantum-exercises",
            "name": "quantum-exercises",
            "url": REPO,
            "codeRepository": REPO,
            "programmingLanguage": "Python",
            "runtimePlatform": "Qiskit",
            "license": MIT,
            "author": {"@id": PERSON},
            "maintainer": {"@id": PERSON},
            "targetProduct": {"@id": SITE + "#app"},
            "subjectOf": {"@type": "Article", "headline": ARTICLE[0], "url": ARTICLE[1]},
        },
        {
            "@type": "FAQPage",
            "@id": SITE + "#questions",
            "mainEntity": [
                {
                    "@type": "Question",
                    "name": q,
                    "acceptedAnswer": {"@type": "Answer", "text": plain(a)},
                }
                for q, a in FAQ
            ],
        },
    ],
}
ld_json = json.dumps(ld, ensure_ascii=False, indent=2).replace("</", "<\\/")

GITHUB_MARK = '<svg viewBox="0 0 16 16" aria-hidden="true"><path fill="currentColor" d="M6.766 11.328c-2.063-.25-3.516-1.734-3.516-3.656 0-.781.281-1.625.75-2.188-.203-.515-.172-1.609.063-2.062.625-.078 1.468.25 1.968.703.594-.187 1.219-.281 1.985-.281.765 0 1.39.094 1.953.265.484-.437 1.344-.765 1.969-.687.218.422.25 1.515.046 2.047.5.593.766 1.39.766 2.203 0 1.922-1.453 3.375-3.547 3.64.531.344.89 1.094.89 1.954v1.625c0 .468.391.734.86.547C13.781 14.359 16 11.53 16 8.03 16 3.61 12.406 0 7.984 0 3.563 0 0 3.61 0 8.031a7.88 7.88 0 0 0 5.172 7.422c.422.156.828-.125.828-.547v-1.25c-.219.094-.5.156-.75.156-1.031 0-1.64-.562-2.078-1.609-.172-.422-.36-.672-.719-.719-.187-.015-.25-.093-.25-.187 0-.188.313-.328.625-.328.453 0 .844.281 1.25.86.313.452.64.655 1.031.655s.641-.14 1-.5c.266-.265.47-.5.657-.656"/></svg>'
HEART = '<svg viewBox="0 0 16 16" aria-hidden="true"><path fill="currentColor" d="M7.655 14.916v-.001h-.002l-.006-.003-.018-.01a22.066 22.066 0 0 1-3.744-2.584C2.045 10.731 0 8.35 0 5.5 0 2.836 2.086 1 4.25 1 5.797 1 7.153 1.802 8 3.02 8.847 1.802 10.203 1 11.75 1 13.914 1 16 2.836 16 5.5c0 2.85-2.044 5.231-3.886 6.818a22.094 22.094 0 0 1-3.433 2.414 7.152 7.152 0 0 1-.31.17l-.018.01-.008.004a.75.75 0 0 1-.69 0Z"/></svg>'
profile_items = "\n".join(f'          <li><a href="{u}">{n}</a></li>' for n, u in PROFILES)

fail_panel = """<div class="term-title">11 Bell state, and which bit is which</div>
                <div class="box bad"><span class="box-name">NOT YET</span>
                  <p>Your circuit does not prepare (|00&gt; + |11&gt;) / sqrt(2).</p>
                  <p class="kv"><span>Your probabilities:</span> {'00': 1.0000}</p>
                  <p class="kv"><span>Target probabilities:</span> {'00': 0.5000, '11': 0.5000}</p>
                  <p>Note: global phase is ignored, so a phase difference is not the problem here.</p>
                </div>
                <p class="next-step"><span>next</span> qx hint 11 for a nudge, or open exercises/11_bell_entanglement/exercise.py then run qx run</p>"""
pass_panel = """<div class="term-title">11 Bell state, and which bit is which</div>
                <div class="box"><span class="box-name">Your Bell state</span>
                  <table class="amps"><thead><tr><th scope="col">basis</th><th scope="col">amplitude</th><th scope="col">probability</th></tr></thead>
                  <tbody><tr><td>|00&gt;</td><td>0.707</td><td>0.5000</td></tr><tr><td>|01&gt;</td><td>0</td><td>0.0000</td></tr><tr><td>|10&gt;</td><td>0</td><td>0.0000</td></tr><tr><td>|11&gt;</td><td>0.707</td><td>0.5000</td></tr></tbody></table>
                </div>
                <div class="box"><span class="box-name">2048 shots: the two qubits always agree</span>
                  <p class="bar-row"><span>00</span><i style="--w: 90.3"></i><span>972</span><span>47.5%</span></p>
                  <p class="bar-row"><span>11</span><i style="--w: 100"></i><span>1076</span><span>52.5%</span></p>
                </div>
                <p class="pass"><b>PASS</b> 11_bell_entanglement</p>"""

page = f"""<!DOCTYPE html>
<html lang="en-US">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{TITLE}</title>
  <meta name="description" content="{esc(DESCRIPTION)}">
  <link rel="canonical" href="{SITE}">
  <meta name="robots" content="index, follow, max-image-preview:large, max-snippet:-1, max-video-preview:-1">
  <meta name="author" content="Țugui Dragoș">
  <meta name="application-name" content="quantum-exercises">
  <meta name="theme-color" content="#10121c">
  <meta name="color-scheme" content="dark">
  <link rel="icon" href="/favicon.ico" sizes="32x32">
  <link rel="icon" href="/favicon-96x96.png" type="image/png" sizes="96x96">
  <link rel="icon" href="/favicon.svg" type="image/svg+xml">
  <link rel="apple-touch-icon" href="/apple-touch-icon.png">
  <link rel="manifest" href="/site.webmanifest">

  <script>document.documentElement.classList.add("js")</script>
  <link rel="stylesheet" href="style.css">
  <script src="main.js" defer></script>

  <meta property="og:type" content="website">
  <meta property="og:site_name" content="quantum-exercises">
  <meta property="og:locale" content="en_US">
  <meta property="og:url" content="{SITE}">
  <meta property="og:title" content="quantum-exercises: learn Qiskit by doing">
  <meta property="og:description" content="{COUNT_WORD.capitalize()} hands-on Qiskit exercises, from an empty laptop to real IBM quantum hardware. One command tells you what is wrong, in quantum terms.">
  <meta property="og:image" content="{SITE}images/social.png">
  <meta property="og:image:type" content="image/png">
  <meta property="og:image:width" content="1200">
  <meta property="og:image:height" content="630">
  <meta property="og:image:alt" content="The words “From an empty laptop to a real QPU” beside qx explaining that a circuit does not prepare a Bell state">
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:title" content="quantum-exercises: learn Qiskit by doing">
  <meta name="twitter:description" content="{COUNT_WORD.capitalize()} hands-on Qiskit exercises, from an empty laptop to real IBM quantum hardware. One command tells you what is wrong, in quantum terms.">
  <meta name="twitter:image" content="{SITE}images/social.png">
  <meta name="twitter:image:alt" content="The words “From an empty laptop to a real QPU” beside qx explaining that a circuit does not prepare a Bell state">

  <script type="application/ld+json">
{ld_json}
  </script>
</head>
<body>
  <a class="skip" href="#main">Skip to content</a>

  <header class="nav">
    <div class="wrap">
      <a class="brand" href="#top" aria-label="quantum-exercises, back to the top">quantum-exercises</a>
      <nav aria-label="Sections">
        <ul class="nav-links">
          <li><a href="#exercises">Exercises</a></li>
          <li><a href="#checking">Checking</a></li>
          <li><a href="#hardware">Hardware</a></li>
          <li><a href="#install">Install</a></li>
          <li><a href="#tested">Tested</a></li>
          <li><a href="#questions">Questions</a></li>
        </ul>
      </nav>
      <div class="nav-actions">
        <a class="pill pill-small pill-ghost" href="{SPONSOR}" aria-label="Sponsor quantum-exercises on GitHub">{HEART}<span class="label">Sponsor</span></a>
        <a class="pill pill-small" href="{REPO}">{GITHUB_MARK}GitHub</a>
      </div>
    </div>
  </header>

  <main id="main">
    <section class="hero" id="top">
      <div class="wrap">
        <p class="badge">{COUNT} hands-on Qiskit exercises</p>
        <h1>From an empty laptop to a real&nbsp;QPU.</h1>
        <p class="tagline"><span class="gradient">One command tells you what’s wrong, in quantum terms.</span></p>
        <p class="lede">You edit a file, you run one command, and it tells you exactly what is wrong in the language of the problem rather than as a Python traceback. The course ends at the Bell inequality that no shared coin can reach.</p>
        <div class="command">
          <code>{INSTALL}</code>
          <button class="copy" type="button" data-copy="{INSTALL}">Copy</button>
        </div>
        <div class="actions">
          <a class="pill pill-large" href="{REPO}">{GITHUB_MARK}View on GitHub</a>
          <a class="more" href="#exercises">See the {COUNT_WORD} exercises</a>
        </div>
        <p class="requirements"><span>{PYTHON_RANGE}</span> · <span>No IBM account needed</span> · <span>Free, MIT License</span></p>
        <figure class="story">
          <div class="story-steps">
            <ul class="chips tabs" data-tabs aria-label="Exercise 11, before and after the fix">
              <li><button type="button" data-tab="step-wrong" aria-pressed="true" aria-controls="step-wrong">1 · Get it wrong</button></li>
              <li><button type="button" data-tab="step-fixed" aria-pressed="false" aria-controls="step-fixed">2 · Fix it</button></li>
            </ul>
          </div>
          <div class="panel story-pair active" id="step-wrong">
            <div class="code"><p class="file">exercise.py</p><pre><code>{COLORED["before"]}</code></pre></div>
            <div class="term" role="img" aria-label="qx run 11 answers NOT YET: your circuit does not prepare the Bell state; your probabilities are 00 at 1.0, the target is 00 and 11 at 0.5 each, and global phase is not the problem.">
              <p class="file" aria-hidden="true">Terminal</p>
              <p class="prompt-line" aria-hidden="true"><span>$</span> qx run 11</p>
              <div aria-hidden="true">{fail_panel}</div>
            </div>
          </div>
          <div class="panel story-pair" id="step-fixed">
            <div class="code"><p class="file">exercise.py</p><pre><code>{COLORED["after"]}</code></pre></div>
            <div class="term" role="img" aria-label="qx run 11 passes: the Bell state has amplitude 0.707 on 00 and on 11, and 2048 shots split 972 and 1076 between 00 and 11, the two qubits always agreeing.">
              <p class="file" aria-hidden="true">Terminal</p>
              <p class="prompt-line" aria-hidden="true"><span>$</span> qx run 11</p>
              <div aria-hidden="true">{pass_panel}</div>
            </div>
          </div>
          <figcaption>What qx {version} prints for exercise 11, before and after the fix. The checker samples with a fixed seed, so a correct answer gets these same counts.</figcaption>
        </figure>
      </div>
    </section>

    <section class="statement" aria-label="Why the course exists">
      <div class="wrap reveal">
        <p><strong>Nearly every quantum tutorial was written for Qiskit 0.x, and none of it runs any more.</strong> Beginners hit an ImportError on line 3 and conclude they are not smart enough. <strong>They were reading instructions for software that no longer exists.</strong></p>
      </div>
    </section>

    <section class="section" aria-labelledby="highlights-title">
      <div class="wrap">
        <h2 class="headline center reveal" id="highlights-title">Get the highlights.</h2>
        <div class="highlights">
          <article class="tile span-3 reveal">
            <div class="tile-art" aria-hidden="true"><span class="figure gradient">{COUNT}</span></div>
            <h3>{COUNT_WORD.capitalize()} exercises.</h3>
            <p>In {ACTS} acts, from a first circuit to the Bell inequality, each ending on something your own code produced.</p>
          </article>
          <article class="tile span-3 reveal">
            <div class="tile-art" aria-hidden="true"><span class="mini-box">NOT YET</span></div>
            <h3>Errors in quantum terms.</h3>
            <p>No traceback into library code: the runner knows which concept you tripped over, so it explains the concept.</p>
          </article>
          <article class="tile reveal">
            <div class="tile-art" aria-hidden="true"><span class="figure gradient">0</span></div>
            <h3>Accounts needed.</h3>
            <p>Every exercise runs on a local simulator. Real IBM hardware is optional.</p>
          </article>
          <article class="tile reveal">
            <div class="tile-art" aria-hidden="true"><span class="figure gradient">{tests:,}</span></div>
            <h3>Tests.</h3>
            <p>On {PYTHON_RANGE}, with every reference solution re-run and every notebook cell executed.</p>
          </article>
          <article class="tile reveal">
            <div class="tile-art" aria-hidden="true"><span class="figure gradient days">1 · 15</span></div>
            <h3>Checked twice a month.</h3>
            <p>On the 1st and the 15th, against the Qiskit that ships that day.</p>
          </article>
        </div>
      </div>
    </section>

    <section class="section" id="exercises" aria-labelledby="exercises-title">
      <div class="wrap center">
        <div class="feature-head center reveal">
          <p class="eyebrow">The exercises</p>
          <h2 class="headline" id="exercises-title">{COUNT_WORD.capitalize()} exercises, in {ACTS} acts.</h2>
          <p class="lede">You need basic Python and no quantum background. <strong>Act I takes well under an hour;</strong> the whole course is an afternoon or two, depending on how much you stop to poke at things.</p>
        </div>
        <div class="acts">
          {"".join(act_html)}
        </div>
      </div>
    </section>

    <hr class="divider">

    <section class="section" id="checking" aria-labelledby="checking-title">
      <div class="wrap center">
        <div class="feature-head center reveal">
          <p class="eyebrow">How answers are checked</p>
          <h2 class="headline" id="checking-title">It inspects what your code makes.</h2>
          <p class="lede">Not by comparing your code to the solution. <strong>An answer that is right for reasons the author did not anticipate still passes,</strong> and an answer that only looks right does not.</p>
        </div>
        <ul class="cards">
          <li class="reveal"><h3>States</h3><p>Compared with <code>Statevector.equiv</code>, which ignores global phase, because no experiment can detect it.</p></li>
          <li class="reveal"><h3>Gates</h3><p>Compared with <code>Operator.equiv</code>, for the same reason.</p></li>
          <li class="reveal"><h3>Counts</h3><p>Never for exact equality: sampling is random. Proportions are held to the binomial standard error, <code>sqrt(p(1-p)/N)</code>, at 4 sigma, and whole distributions to a chi-square test.</p></li>
          <li class="reveal"><h3>Its own process</h3><p>Your file runs in a separate process with a time limit, so an infinite loop or a crash costs one run, not your terminal session.</p></li>
        </ul>
      </div>
    </section>

    <section class="section" id="hardware" aria-labelledby="hardware-title">
      <div class="wrap center">
        <div class="feature-head center reveal">
          <p class="eyebrow">Real hardware</p>
          <h2 class="headline" id="hardware-title">A real QPU, when you want one.</h2>
          <p class="lede">Exercise {HW} is the only one that reaches out to IBM, and <strong>it asks before it sends anything.</strong> Answering no changes nothing and costs nothing.</p>
        </div>
        <ol class="fallback reveal">
          <li><b>A real QPU,</b> if you have an account and one is reachable.</li>
          <li><b>A local simulator with a noise model copied from real hardware,</b> so the lesson about noise still lands.</li>
          <li><b>A plain noiseless simulator.</b></li>
        </ol>
        <div class="queue reveal" role="img" aria-label="qx run {HW} shows that the least busy QPU is ibm_marrakesh with 1 job ahead of you, links to every computer, and asks: Send it now? Answering no changes nothing and costs nothing.">
          <pre aria-hidden="true"><span class="dim">  least busy  </span><b>ibm_marrakesh</b>   1 job(s) ahead of you
<span class="dim">  all of them </span><span class="link">https://quantum.cloud.ibm.com/computers</span>

  Send it now? Answering no changes nothing and costs nothing [y/N]:</pre>
        </div>
        <p class="note reveal">Say yes and qx waits up to three hours, what a real queue can take. Ctrl-C stops the waiting, not the job: its result stays in your IBM Quantum account. Nothing automated, not CI, a script or watch mode, ever reaches a QPU.</p>
        <figure class="wide-shot reveal">
          <a href="images/08-real-hardware-1600.webp">{picture("08-real-hardware", HARDWARE_ALT, SHOT_SIZES)}</a>
          <figcaption>Exercise {HW} on <code>ibm_marrakesh</code>: 1,024 shots, 49.0% <code>00</code> and 48.4% <code>11</code>. The 2.54% that disagree are noise, and exercise {HONEST} is about measuring it honestly.</figcaption>
        </figure>
      </div>
    </section>

    <hr class="divider">

    <section class="section" id="editor" aria-labelledby="editor-title">
      <div class="wrap center">
        <div class="feature-head center reveal">
          <p class="eyebrow">Where you work</p>
          <h2 class="headline" id="editor-title">Your editor, your terminal.</h2>
          <p class="lede">The exercise on one side, the verdict on the other. <strong>{NOTEBOOK_WORD} notebooks</strong> sit beside the exercises, ungraded and meant to be poked at, and every cell of every one runs in CI.</p>
        </div>
        <div class="gallery reveal">
          <ul class="chips tabs" data-tabs aria-label="Screenshots">{"".join(shot_tabs)}</ul>
          {"".join(shot_panels)}
        </div>
        <div class="table-wrap reveal">
          <table>
            <caption>The notebooks, opened with <code>uv run --with quantum-exercises --with jupyterlab jupyter lab</code></caption>
            <thead><tr><th scope="col">Notebook</th><th scope="col">What it is for</th></tr></thead>
            <tbody>{notebooks_html}</tbody>
          </table>
        </div>
      </div>
    </section>

    <section class="section" id="install" aria-labelledby="install-title">
      <div class="wrap center">
        <div class="feature-head center reveal">
          <p class="eyebrow">Install</p>
          <h2 class="headline" id="install-title">Start in five steps.</h2>
          <p class="lede"><strong>uv is the only thing you install.</strong> It fetches the right Python itself, so you don’t need Python first.</p>
        </div>
        <ol class="steps">
          <li class="reveal"><h3>Install uv</h3><p>On macOS and Linux:</p><div class="command"><code>{command_html(UV_INSTALL)}</code><button class="copy" type="button" data-copy="{esc(UV_INSTALL)}">Copy</button></div><p>On Windows, in PowerShell:</p><div class="command long"><code>{command_html(UV_WINDOWS)}</code><button class="copy" type="button" data-copy="{esc(UV_WINDOWS)}">Copy</button></div></li>
          <li class="reveal"><h3>Install the tool</h3><p>It puts <code>qx</code> on your PATH. The first run downloads Qiskit and its scientific stack, so give it a minute.</p><div class="command"><code>{INSTALL}</code><button class="copy" type="button" data-copy="{INSTALL}">Copy</button></div></li>
          <li class="reveal"><h3>Take a copy of the course</h3><p>Then <code>cd quantum-exercises</code>. Running it again never overwrites your answers.</p><div class="command"><code>qx init</code><button class="copy" type="button" data-copy="qx init">Copy</button></div></li>
          <li class="reveal"><h3>Check that it worked</h3><p>It never touches the network, and names the fix for anything wrong.</p><div class="command"><code>qx doctor</code><button class="copy" type="button" data-copy="qx doctor">Copy</button></div></li>
          <li class="reveal"><h3>Start</h3><p>It prints the first unfinished exercise: the lesson to read, and the file to edit.</p><div class="command"><code>qx next</code><button class="copy" type="button" data-copy="qx next">Copy</button></div></li>
        </ol>
        <div class="table-wrap reveal">
          <table>
            <caption>Every command. Leave the number off and it picks the first exercise you have not finished.</caption>
            <thead><tr><th scope="col">Command</th><th scope="col">What it does</th></tr></thead>
            <tbody>{commands_html}</tbody>
          </table>
        </div>
      </div>
    </section>

    <hr class="divider">

    <section class="section" id="tested" aria-labelledby="tested-title">
      <div class="wrap center">
        <div class="feature-head center reveal">
          <p class="eyebrow">Tested</p>
          <h2 class="headline" id="tested-title">Verified against today’s Qiskit.</h2>
          <p class="lede">Every reference solution is re-run on the 1st and the 15th of every month, <strong>and if a new Qiskit release breaks an exercise, the verify badge turns red.</strong></p>
        </div>
        <div class="stats">
          <div class="stat reveal"><h3>{tests:,} tests</h3><p>On Python {PYTHON_LIST}, with coverage held at 100%.</p></div>
          <div class="stat reveal"><h3>Three systems</h3><p>Ubuntu, macOS and Windows, on the 1st of every month.</p></div>
          <div class="stat reveal"><h3>The next Qiskit too</h3><p>On the 1st and the 15th, a fresh resolution of every dependency, and a probe of the next major version.</p></div>
          <div class="stat reveal"><h3>A locked stack</h3><p>{STACK_SENTENCE}, pinned in <code>uv.lock</code>.</p></div>
        </div>
      </div>
    </section>

    <section class="section" id="questions" aria-labelledby="questions-title">
      <div class="wrap">
        <h2 class="headline center reveal" id="questions-title">Questions.</h2>
        <div class="faq reveal">
{faq_html}
        </div>
      </div>
    </section>

    <section class="closing" aria-labelledby="get-title">
      <div class="wrap reveal">
        <h2 class="headline" id="get-title">Start with exercise {FIRST}.</h2>
        <p class="lede">Free and open source, under the MIT License.</p>
        <div class="command">
          <code>{INSTALL}</code>
          <button class="copy" type="button" data-copy="{INSTALL}">Copy</button>
        </div>
        <div class="actions">
          <a class="more" href="{PYPI}">PyPI</a>
          <a class="more" href="{UV}">uv</a>
          <a class="more" href="{ARTICLE[1]}">Why I built it</a>
        </div>
        <a class="pill pill-ghost sponsor" href="{SPONSOR}">{HEART}Sponsor on GitHub</a>
      </div>
    </section>
  </main>

  <footer>
    <div class="wrap">
      <nav aria-label="More about quantum-exercises">
        <ul>
          <li><a href="{REPO}">Source code</a></li>
          <li><a href="{PYPI}">PyPI</a></li>
          <li><a href="{REPO}/blob/main/CONTRIBUTING.md">Contributing</a></li>
          <li><a href="{REPO}/blob/main/SECURITY.md">Security</a></li>
          <li><a href="{REPO}/issues">Report an issue</a></li>
          <li><a href="{SPONSOR}">Sponsor</a></li>
        </ul>
      </nav>
      <p class="maker">Made by <a href="https://tuguidragos.com/">Țugui Dragoș</a>.</p>
      <nav aria-label="Țugui Dragoș elsewhere">
        <ul>
{profile_items}
        </ul>
      </nav>
      <p>Copyright © 2026 Țugui Dragoș. quantum-exercises is free software under the <a href="{REPO}/blob/main/LICENSE">MIT License</a>.</p>
      <p>Qiskit is a trademark of IBM. This project is not affiliated with or endorsed by IBM.</p>
    </div>
  </footer>
</body>
</html>
"""
page = "\n".join(line.rstrip() for line in page.split("\n"))
facts = {
    "count_word": COUNT_WORD,
    "hardware": HW,
    "qiskit_major": QISKIT_MAJOR,
    "pythons": PYTHON_RANGE,
    "stack": STACK_SENTENCE,
}
(WORK / "facts.json").write_text(json.dumps(facts))
# The page is dated by what it says, not by when it was built. When the published page says exactly the same, its date
# stands, so a push that changes nothing here does not tell search engines that the page changed.
DATED = re.compile(r'"dateModified": "\d{4}-\d\d-\d\d"')
modified = datetime.date.today().isoformat()
try:
    with urllib.request.urlopen(SITE, timeout=20) as response:
        published = response.read().decode()
    if DATED.sub("", published) == DATED.sub("", page):
        modified = re.search(r'"dateModified": "(\d{4}-\d\d-\d\d)"', published).group(1)
except (OSError, ValueError, AttributeError):
    pass
page = DATED.sub(f'"dateModified": "{modified}"', page)
(WORK / "modified.txt").write_text(modified)
out_dir.mkdir(parents=True, exist_ok=True)
(out_dir / "index.html").write_text(page, encoding="utf-8")
visible = re.sub(
    r"<[^>]+>",
    " ",
    re.sub(r"<pre.*?</pre>", "", page.replace(ARTICLE[0], "").replace(ARTICLE[1], ""), flags=re.S),
)
british = sorted(
    set(
        re.findall(
            r"\b(analyse|analysed|analyser\w*|behaviour|colour\w*|licence|modell\w*|labell\w*|cancell(?!ation)\w*|recognis\w*|organis\w*|optimis\w*|summaris\w*|initialis\w*|normalis\w*|characteris\w*|practise)\b",
            visible,
        )
    )
)
assert not british, f"American English on the page, but it reads {british}"
print(
    f"index.html: {COUNT} exercises in {len(acts)} acts, {tests:,} tests, qx {version}, Qiskit {STACK['qiskit']}"
)
