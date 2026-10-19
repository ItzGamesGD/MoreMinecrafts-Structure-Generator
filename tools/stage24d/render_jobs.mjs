// usage: node render_jobs.mjs <assetsRoot> <jobs.json>   (jobs: [{out, scene, w, h, az, el, ...}])
import http from 'http'
import fs from 'fs'
import path from 'path'
import { createRequire } from 'module'
const require = createRequire(import.meta.url)
const { chromium } = require('playwright-core')
const here = path.dirname(new URL(import.meta.url).pathname)
const [assetsRoot, jobsPath] = process.argv.slice(2)
const MIME = { '.html': 'text/html', '.js': 'text/javascript', '.json': 'application/json', '.png': 'image/png', '.mcmeta': 'application/json' }
const server = http.createServer((req, res) => {
  const u = decodeURIComponent(req.url.split('?')[0])
  let f
  if (u === '/' || u === '/viewer.html') f = path.join(here, 'viewer.html')
  else if (u === '/viewer.js') f = path.join(here, 'viewer.js')
  else if (u.startsWith('/three/')) f = path.join(here, 'node_modules/three', u.slice(7))
  else if (u.startsWith('/assets/minecraft/')) f = path.join(assetsRoot, u.slice(8))
  else { res.writeHead(404); return res.end() }
  fs.readFile(f, (e, d) => { if (e) { res.writeHead(404); return res.end() } res.writeHead(200, { 'content-type': MIME[path.extname(f)] || 'application/octet-stream' }); res.end(d) })
}).listen(0)
const port = server.address().port
const jobs = JSON.parse(fs.readFileSync(jobsPath, 'utf8'))
const browser = await chromium.launch({ args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] })
const page = await browser.newPage()
page.on('pageerror', e => console.error('pageerror', e.message))
page.on('console', m => { if (m.type() === 'error') console.error('console', m.text()) })
await page.goto(`http://127.0.0.1:${port}/viewer.html`)
await page.waitForFunction('window.ready === true', null, { timeout: 30000 })
const sceneCache = new Map()
let n = 0, failed = 0
for (const job of jobs) {
  try {
    if (!sceneCache.has(job.scene)) sceneCache.set(job.scene, JSON.parse(fs.readFileSync(job.scene, 'utf8')))
    const j = { ...job, scene: sceneCache.get(job.scene) }
    const r = await page.evaluate(j => window.renderJob(j), j)
    fs.mkdirSync(path.dirname(job.out), { recursive: true })
    fs.writeFileSync(job.out, Buffer.from(r.png.split(',')[1], 'base64'))
    n++
    if (n % 10 === 0) console.log('rendered', n, '/', jobs.length)
  } catch (e) { failed++; console.error('FAILED', job.out, e.message) }
}
console.log('done', n, 'failed', failed)
await browser.close(); server.close()
process.exit(failed ? 2 : 0)
