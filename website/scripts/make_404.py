"""Writes the 404 page from what `qx run 404` really prints and returns."""

import html
import json
from pathlib import Path

WEB = Path(__file__).resolve().parents[1]
out = WEB / "_site/404.html"
missing = (WEB / "_build/missing.txt").read_text().splitlines()
MESSAGE = "  There is no exercise number 404."
assert MESSAGE in missing and missing[-1] == "exit 2", missing
count_word = json.loads((WEB / "_build/facts.json").read_text())["count_word"]
page = """<!DOCTYPE html>
<html lang="en-US">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Page not found: quantum-exercises</title>
  <meta name="description" content="This page isn’t part of the course site. All COUNT_WORD exercises are on the home page.">
  <meta name="robots" content="noindex">
  <meta name="theme-color" content="#10121c">
  <meta name="color-scheme" content="dark">
  <link rel="icon" href="/favicon.ico" sizes="32x32">
  <link rel="icon" href="/favicon-96x96.png" type="image/png" sizes="96x96">
  <link rel="icon" href="/favicon.svg" type="image/svg+xml">
  <link rel="apple-touch-icon" href="/apple-touch-icon.png">
  <style>
    :root {
      color-scheme: dark;
    }

    body {
      display: grid;
      place-items: center;
      min-height: 100vh;
      min-height: 100dvh;
      box-sizing: border-box;
      margin: 0;
      padding: 32px 16px;
      background: radial-gradient(ellipse 70% 55% at 50% 0%, rgba(145, 132, 217, 0.18), rgba(145, 132, 217, 0)) #10121c;
      color: #eeeef4;
      font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
      text-align: center;
      -webkit-font-smoothing: antialiased;
    }

    main {
      width: min(620px, 100%);
    }

    .terminal {
      overflow: hidden;
      border-radius: 14px;
      background: #0b0e1a;
      box-shadow: 0 0 0 1px rgba(255, 255, 255, 0.09), 0 30px 70px rgba(0, 0, 0, 0.55);
      text-align: left;
    }

    .bar {
      position: relative;
      display: flex;
      gap: 8px;
      align-items: center;
      height: 36px;
      padding: 0 14px;
      background: #151a2a;
      box-shadow: inset 0 -1px 0 rgba(255, 255, 255, 0.06);
    }

    .bar i {
      width: 12px;
      height: 12px;
      border-radius: 50%;
      background: #ff5f57;
      box-shadow: inset 0 0 0 0.5px rgba(0, 0, 0, 0.3);
    }

    .title {
      position: absolute;
      inset: 0;
      display: grid;
      place-items: center;
      color: #a9abc0;
      font-size: 13px;
      font-weight: 500;
      letter-spacing: 0.01em;
    }

    .bar i:nth-child(2) {
      background: #febc2e;
    }

    .bar i:nth-child(3) {
      background: #28c840;
    }

    pre {
      margin: 0;
      padding: 18px 22px 22px;
      color: #c8d3f5;
      font-family: ui-monospace, "SF Mono", SFMono-Regular, Menlo, Consolas, "Liberation Mono", monospace;
      font-size: 14px;
      line-height: 1.6;
      white-space: pre-wrap;
      overflow-wrap: anywhere;
    }

    pre > span {
      position: relative;
      display: block;
    }

    .typed {
      display: inline-block;
      vertical-align: top;
    }

    .caret {
      display: none;
    }

    .prompt {
      color: #a89ce4;
    }

    .exit {
      color: #ff9f45;
      font-weight: 600;
    }

    .cursor,
    .caret {
      width: 1ch;
      height: 1.2em;
      background: #a89ce4;
    }

    .cursor {
      display: inline-block;
      vertical-align: -0.22em;
    }

    h1 {
      margin: 36px 0 0;
      font-size: clamp(30px, 6vw, 44px);
      font-weight: 700;
      letter-spacing: -0.015em;
      text-wrap: balance;
    }

    p {
      margin: 14px auto 30px;
      color: #a9abc0;
      font-size: 19px;
      line-height: 1.45;
      text-wrap: balance;
    }

    a {
      display: inline-block;
      padding: 13px 26px;
      border-radius: 999px;
      background: #a89ce4;
      color: #10121c;
      font-size: 17px;
      font-weight: 600;
      text-decoration: none;
      transition: background-color 0.2s;
    }

    a:hover {
      background: #cbc3f3;
    }

    a:focus-visible {
      outline: 3px solid #a89ce4;
      outline-offset: 3px;
    }

    /* The session plays once, as it would in a terminal: each command is typed a key at a time, its answer printed
       whole, and the cursor then blinks for a few seconds and stays. */
    @media (prefers-reduced-motion: no-preference) {
      pre > span {
        animation: print 0.01s both;
      }

      pre > span:nth-child(1) {
        animation-delay: 0.3s;
      }

      pre > span:nth-child(2) {
        animation-delay: 1.35s;
      }

      pre > span:nth-child(3) {
        animation-delay: 1.65s;
      }

      pre > span:nth-child(4) {
        animation-delay: 2.5s;
      }

      pre > span:nth-child(5) {
        animation-delay: 2.7s;
      }

      .caret {
        position: absolute;
        top: 0.2em;
        left: 2ch;
        display: block;
      }

      pre > span:nth-child(1) .typed {
        animation: type 0.55s 0.55s steps(10, end) both;
      }

      pre > span:nth-child(1) .caret {
        animation: key-10 0.55s 0.55s steps(10, end) both, enter 0.01s 1.25s forwards;
      }

      pre > span:nth-child(3) .typed {
        animation: type 0.39s 1.9s steps(7, end) both;
      }

      pre > span:nth-child(3) .caret {
        animation: key-7 0.39s 1.9s steps(7, end) both, enter 0.01s 2.4s forwards;
      }

      .cursor {
        animation: blink 1.1s 2.7s steps(1) 4;
      }

      @keyframes print {
        from {
          visibility: hidden;
        }
      }

      @keyframes type {
        from {
          clip-path: inset(0 100% 0 0);
        }

        to {
          clip-path: inset(0);
        }
      }

      @keyframes key-10 {
        to {
          transform: translateX(10ch);
        }
      }

      @keyframes key-7 {
        to {
          transform: translateX(7ch);
        }
      }

      @keyframes enter {
        to {
          visibility: hidden;
        }
      }

      @keyframes blink {
        50% {
          opacity: 0;
        }
      }
    }

    @media (max-height: 640px) {
      h1 {
        margin-top: 22px;
      }

      p {
        margin: 10px 0 20px;
      }
    }

    /* A phone held sideways: the terminal and the way home matter more than the icon. */
    @media (max-height: 460px) {
      body {
        padding: 16px;
      }

      pre {
        padding: 12px 18px 14px;
        line-height: 1.6;
      }

      h1 {
        margin-top: 16px;
        font-size: 28px;
      }

      p {
        margin: 8px 0 16px;
        font-size: 16px;
      }

      a {
        padding: 10px 22px;
      }
    }

    @media (max-width: 640px) {
      pre {
        font-size: 13px;
      }

      p {
        font-size: 17px;
      }
    }
  </style>
</head>
<body>
  <main>
    <div class="terminal" role="img" aria-label="qx run 404 answers: There is no exercise number 404, and exits with code 2">
      <div class="bar" aria-hidden="true"><i></i><i></i><i></i><span class="title">quantum-exercises</span></div>
      <pre aria-hidden="true"><span><span class="prompt">$</span> <span class="typed">qx run 404</span><i class="caret"></i></span><span>MISSING</span><span><span class="prompt">$</span> <span class="typed">echo $?</span><i class="caret"></i></span><span class="exit">EXIT</span><span><span class="prompt">$</span> <i class="cursor"></i></span></pre>
    </div>
    <h1>There is no exercise&nbsp;404.</h1>
    <p>This page isn’t part of the course site. All COUNT_WORD exercises are on the home page.</p>
    <a href="/">Go to the home page</a>
  </main>
</body>
</html>
"""
message, exit_code = html.escape(MESSAGE), missing[-1].split()[-1]
page = page.replace("COUNT_WORD", count_word).replace("MISSING", message).replace("EXIT", exit_code)
out.write_text(page)
print("404.html:", missing[0].strip())
