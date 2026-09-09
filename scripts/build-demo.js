/* Inline the shared engine modules into the demo template → dist/index.html (one self-contained file). */
const fs = require('node:fs');
const path = require('node:path');
const root = path.join(__dirname, '..');
const read = (p) => fs.readFileSync(path.join(root, p), 'utf8');
const engine = ['src/matching.js', 'src/seed.js', 'src/metrics.js'].map(read).join('\n');
const html = read('demo/template.html').replace('/*__KYN_ENGINE__*/', () => engine);
fs.mkdirSync(path.join(root, 'dist'), { recursive: true });
fs.writeFileSync(path.join(root, 'dist/index.html'), html);
console.log('dist/index.html', (html.length / 1024).toFixed(0), 'KB');
