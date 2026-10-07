// Writes the favicon set into website/static from favicon-source.svg. The 96 px PNG is for Google, which takes no SVG;
// home-screen icons are full bleed because the OS rounds the corners. Run from the repository root:
// npm install --no-save --prefix website playwright@1, npx --prefix website playwright install chromium, then
// node website/tools/make_favicons.mjs
import { chromium } from "playwright";
import fs from "node:fs";
const TILE = "#0b0d18";
const svg = fs.readFileSync(new URL("favicon-source.svg", import.meta.url));
const out = (name) => new URL(`../static/${name}`, import.meta.url);
const data = "data:image/svg+xml;base64," + svg.toString("base64");
fs.writeFileSync(out("favicon.svg"), svg);
const browser = await chromium.launch();
const draw = async (size, bleed) => {
  const page = await browser.newPage({ viewport: { width: size, height: size } });
  await page.setContent(`<body style="margin:0;background:${bleed ? TILE : "transparent"}"><img src="${data}" width="${size}" height="${size}" style="display:block"></body>`);
  const png = await page.screenshot({ omitBackground: !bleed });
  await page.close();
  return png;
};
fs.writeFileSync(out("favicon-96x96.png"), await draw(96, false));
for (const [name, size] of [["apple-touch-icon.png", 180], ["icon-192.png", 192], ["icon-512.png", 512]]) {
  fs.writeFileSync(out(name), await draw(size, true));
}
// ICO entries are embedded PNGs, which every current browser reads.
const sizes = [16, 32, 48];
const pngs = [];
for (const size of sizes) pngs.push(await draw(size, false));
await browser.close();
const head = Buffer.alloc(6 + 16 * sizes.length);
head.writeUInt16LE(1, 2);
head.writeUInt16LE(sizes.length, 4);
let offset = head.length;
sizes.forEach((size, i) => {
  const at = 6 + 16 * i;
  head.writeUInt8(size, at);
  head.writeUInt8(size, at + 1);
  head.writeUInt16LE(1, at + 4);
  head.writeUInt16LE(32, at + 6);
  head.writeUInt32LE(pngs[i].length, at + 8);
  head.writeUInt32LE(offset, at + 12);
  offset += pngs[i].length;
});
fs.writeFileSync(out("favicon.ico"), Buffer.concat([head, ...pngs]));
console.log("favicons made");
