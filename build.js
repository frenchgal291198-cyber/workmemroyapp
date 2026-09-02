#!/usr/bin/env node
// Inlines data/projects.json into src/template.html and writes index.html.
// Usage: node build.js
const fs = require("fs");
const path = require("path");

const root = __dirname;
const data = JSON.parse(fs.readFileSync(path.join(root, "data/projects.json"), "utf8"));
const template = fs.readFileSync(path.join(root, "src/template.html"), "utf8");

// Basic validation so a bad edit fails loudly instead of rendering blank.
const STAGES = ["open", "construction", "approved", "proposed", "stalled", "dead"];
const LEAGUES = ["NFL", "MLB", "NBA", "NHL", "MLS", "NWSL", "WNBA"];
const ids = new Set();
for (const p of data.projects) {
  for (const k of ["id", "league", "team", "venue", "city", "state", "stage", "headline"]) {
    if (!p[k]) throw new Error(`Project missing "${k}": ${JSON.stringify(p).slice(0, 80)}`);
  }
  if (ids.has(p.id)) throw new Error(`Duplicate id: ${p.id}`);
  ids.add(p.id);
  if (!STAGES.includes(p.stage)) throw new Error(`${p.id}: bad stage "${p.stage}"`);
  for (const l of [].concat(p.league)) {
    if (!LEAGUES.includes(l)) throw new Error(`${p.id}: bad league "${l}"`);
  }
  for (const e of p.recent || []) {
    if (!/^\d{4}-\d{2}(-\d{2})?$/.test(e.date)) throw new Error(`${p.id}: bad recent date "${e.date}"`);
  }
}

const json = JSON.stringify(data).replace(/<\/script/gi, "<\\/script");
const out = template.replace("/*__DATA__*/null", json);
fs.writeFileSync(path.join(root, "index.html"), out);
console.log(`Built index.html with ${data.projects.length} projects (as of ${data.asOf}).`);
