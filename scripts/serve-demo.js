/* Serve dist/index.html locally: npm run demo → http://localhost:4173 */
const http = require('node:http');
const fs = require('node:fs');
const path = require('node:path');
const file = path.join(__dirname, '..', 'dist', 'index.html');
const port = Number(process.env.PORT) || 4173;
http.createServer((req, res) => {
  res.writeHead(200, { 'content-type': 'text/html; charset=utf-8' });
  fs.createReadStream(file).pipe(res);
}).listen(port, () => console.log(`Know Your Neighbors demo → http://localhost:${port}`));
