// Renders the share image: 1200x630 for the site, 1280x640 for GitHub's social preview. Run from the repository root:
// npm install --no-save --prefix website playwright@1, npx --prefix website playwright install chromium, then
// node website/tools/make_card.mjs
import { chromium } from "playwright";
const card = (w, h) => `<!DOCTYPE html><html><head><style>
  body { margin: 0; width: ${w}px; height: ${h}px; display: grid; grid-template-columns: 1fr 1.05fr; align-items: center; gap: 44px; box-sizing: border-box; padding: 0 70px 0 80px;
    background: radial-gradient(ellipse 70% 80% at 80% 50%, rgba(145,132,217,.2), rgba(145,132,217,0)), #10121c; color: #eeeef4;
    font-family: Inter, system-ui, sans-serif; -webkit-font-smoothing: antialiased; }
  .badge { display: inline-block; padding: 8px 16px; border-radius: 999px; background: rgba(168,156,228,.14); box-shadow: inset 0 0 0 1.5px rgba(168,156,228,.35); color: #cbc3f3; font-size: 22px; font-weight: 600; }
  h1 { margin: 26px 0 0; font-size: 64px; text-wrap: balance; line-height: 1.03; letter-spacing: -0.03em; font-weight: 700; }
  p { margin: 22px 0 0; color: #a9abc0; font-size: 26px; line-height: 1.35; }
  code { color: #eeeef4; font-family: "DejaVu Sans Mono", monospace; font-size: 24px; }
  .term { padding: 26px 28px; border-radius: 22px; background: #0b0e1a; box-shadow: 0 0 0 1.5px rgba(255,255,255,.1), 0 30px 70px rgba(0,0,0,.5); color: #c8d3f5; font-family: "DejaVu Sans Mono", monospace; font-size: 19px; line-height: 1.55; }
  .term .p { color: #a89ce4; }
  .title { margin-top: 14px; color: #eeeef4; font-weight: 700; }
  .box { position: relative; margin-top: 22px; padding: 18px 18px 14px; border: 1.5px solid rgba(255,123,123,.6); border-radius: 6px; }
  .box span.name { position: absolute; top: -0.8em; left: 50%; transform: translateX(-50%); padding: 0 10px; background: #0b0e1a; color: #ff9f9f; font-weight: 700; }
  .box div + div { margin-top: 8px; }
  .dim { color: #a9abc0; }
</style></head><body>
  <div>
    <span class="badge">Hands-on Qiskit exercises</span>
    <h1>From an empty laptop to a real QPU.</h1>
    <p><code>uv tool install quantum-exercises</code></p>
  </div>
  <div class="term">
    <div><span class="p">$</span> qx run 11</div>
    <div class="title">11 Bell state, and which bit is which</div>
    <div class="box"><span class="name">NOT YET</span>
      <div>Your circuit does not prepare (|00&gt; + |11&gt;) / sqrt(2).</div>
      <div><span class="dim">Your probabilities:</span> {'00': 1.0000}</div>
      <div><span class="dim">Target probabilities:</span> {'00': 0.5000, '11': 0.5000}</div>
    </div>
  </div>
</body></html>`;
const browser = await chromium.launch();
for (const [w, h, out] of [[1200, 630, new URL("../static/images/social.png", import.meta.url)], [1280, 640, new URL("../_build/github-social-preview.png", import.meta.url)]]) {
  const page = await browser.newPage({ viewport: { width: w, height: h } });
  await page.setContent(card(w, h));
  await page.screenshot({ path: out.pathname });
  await page.close();
}
await browser.close();
