/* Inline the shared engine into the demo template. Produces three self-contained files:
 *   dist/index.html     both audiences, with a role switch (shared demo state)
 *   dist/employee.html  employee-facing app only
 *   dist/admin.html     pilot console only
 */
const fs = require('node:fs');
const path = require('node:path');
const root = path.join(__dirname, '..');
const read = (p) => fs.readFileSync(path.join(root, p), 'utf8');
const engine = ['src/matching.js', 'src/seed.js', 'src/metrics.js'].map(read).join('\n');
const template = read('demo/template.html').replace('/*__KYN_ENGINE__*/', () => engine);
fs.mkdirSync(path.join(root, 'dist'), { recursive: true });
const out = {
  'index.html': template,
  'employee.html': template.replace("const LOCKED_MODE = null; /*__KYN_LOCK__*/", "const LOCKED_MODE = 'employee';").replace('<title>Know Your Neighbors</title>', '<title>Know Your Neighbors</title>'),
  'admin.html': template.replace("const LOCKED_MODE = null; /*__KYN_LOCK__*/", "const LOCKED_MODE = 'admin';").replace('<title>Know Your Neighbors</title>', '<title>Know Your Neighbors Pilot Console</title>'),
};
for (const [name, html] of Object.entries(out)) {
  fs.writeFileSync(path.join(root, 'dist', name), html);
  console.log('dist/' + name, (html.length / 1024).toFixed(0), 'KB');
}
