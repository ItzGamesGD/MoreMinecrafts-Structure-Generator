// Stage 24-C player simulation. Usage: node gameplay_bot.js <scenario.json> <result.json>
const mineflayer = require('mineflayer')
const { pathfinder, Movements, goals } = require('mineflayer-pathfinder')
const { Vec3 } = require('vec3')
const fs = require('fs')

const scenario = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'))
const resultPath = process.argv[3]
const results = { module: scenario.module, steps: [], events: [] }
const sleep = ms => new Promise(r => setTimeout(r, ms))
const v = a => new Vec3(a[0], a[1], a[2])
const fmt = p => [Math.floor(p.x), Math.floor(p.y), Math.floor(p.z)]

const bot = mineflayer.createBot({ host: '127.0.0.1', port: scenario.port, username: 'S24C_' + scenario.module.slice(0, 8), version: '26.1.2', hideErrors: false })
bot.loadPlugin(pathfinder)
bot.once('spawn', () => { bot.pathfinder.thinkTimeout = 30000; bot.pathfinder.tickTimeout = 100 })
bot.on('kicked', r => results.events.push('kicked: ' + JSON.stringify(r)))
bot.on('error', e => results.events.push('error: ' + e.message))
bot.on('death', () => results.events.push('death'))
bot.on('messagestr', m => results.events.push('chat: ' + m))
bot.on('actionBar', m => results.events.push('actionbar: ' + m.toString()))

function rcon(cmd) { return scenario.rcon(cmd) }
let tpq = Promise.resolve()

async function tp(pos) {
  bot.chat('/tp @s ' + pos[0] + ' ' + pos[1] + ' ' + pos[2]) // op bot executes
  await sleep(700)
}

let lastPathStatus = null
bot.on('path_update', r => { lastPathStatus = r.status })

async function gotoStep(step) {
  const movements = new Movements(bot)
  movements.canDig = false
  movements.allow1by1towers = false
  movements.scafoldingBlocks = []
  movements.canOpenDoors = true
  movements.allowSprinting = false
  bot.pathfinder.setMovements(movements)
  const t = step.target
  const goal = new goals.GoalBlock(t[0], t[1], t[2])
  const start = fmt(bot.entity.position)
  const tx = t[0] + 0.5, tz = t[2] + 0.5
  const near = () => { const p = bot.entity.position; return Math.hypot(p.x - tx, p.z - tz) < (step.xz_tol ?? 0.7) && Math.abs(p.y - t[1]) < 0.9 }
  let outcome = 'timeout', noPath = 0
  lastPathStatus = null
  bot.pathfinder.setGoal(goal)
  const t0 = Date.now()
  while (Date.now() - t0 < (step.timeout ?? 40) * 1000) {
    await sleep(200)
    if (near()) { outcome = 'reached'; break }
    if (lastPathStatus === 'noPath') { noPath++; lastPathStatus = null; if (noPath >= 3) { outcome = 'noPath'; break } }
  }
  bot.pathfinder.setGoal(null)
  bot.clearControlStates()
  await sleep(250)
  const end = bot.entity.position
  const d = Math.hypot(end.x - tx, end.z - tz)
  return { start, end: [+end.x.toFixed(2), +end.y.toFixed(2), +end.z.toFixed(2)], horizontal_error: +d.toFixed(2), outcome, seconds: +((Date.now() - t0) / 1000).toFixed(1), ok: outcome === 'reached' && near() }
}

async function manualWalk(step) {
  // hold a control for N ms toward a yaw; report displacement. yaw is in radians (mineflayer convention).
  await bot.look(step.yaw, 0, true)
  const p0 = bot.entity.position.clone()
  bot.setControlState('forward', true)
  await sleep(step.ms ?? 3000)
  bot.clearControlStates()
  await sleep(300)
  const p1 = bot.entity.position
  const moved = Math.hypot(p1.x - p0.x, p1.z - p0.z)
  const okMove = step.min_move !== undefined ? moved >= step.min_move : true
  return { start: [p0.x, p0.y, p0.z].map(n => +n.toFixed(2)), end: [p1.x, p1.y, p1.z].map(n => +n.toFixed(2)), dy: +(p1.y - p0.y).toFixed(2), moved: +moved.toFixed(2), ok: okMove && (step.min_end_y === undefined || p1.y >= step.min_end_y) && (step.expectFall ? p1.y < p0.y - 1 : p1.y > p0.y - 0.6) }
}

async function climb(step) {
  // Player-style ladder climb: stand in the base cell, hold forward (into the wall) + jump until top reached.
  const base = step.base, top = step.top
  await tp([base[0] + 0.5, base[1], base[2] + 0.5])
  await bot.look(step.yaw, 0, true)
  const startY = bot.entity.position.y
  const t0 = Date.now()
  bot.setControlState('forward', true)
  bot.setControlState('jump', true)
  let maxY = startY, stuck = 0, lastY = startY
  while (Date.now() - t0 < (step.timeout ?? 30) * 1000) {
    await sleep(100)
    const y = bot.entity.position.y
    maxY = Math.max(maxY, y)
    if (y >= top[1] - 0.01) break
    if (Math.abs(y - lastY) < 0.01) stuck++; else stuck = 0
    lastY = y
    if (stuck > 40) break
  }
  bot.clearControlStates()
  await sleep(300)
  const e = bot.entity.position
  return { start_y: startY, max_y: +maxY.toFixed(2), end: [e.x, e.y, e.z].map(n => +n.toFixed(2)), seconds: +((Date.now() - t0) / 1000).toFixed(1), onGround: bot.entity.onGround, ok: maxY >= top[1] - 0.01 }
}

async function doorStep(step) {
  const p = v(step.pos)
  const b = bot.blockAt(p)
  const before = b ? b.getProperties().open : null
  if (step.expect && String(before) === String(step.expect === 'open')) return { name: b.name, before, after: before, ok: true, note: 'already ' + step.expect }
  await bot.lookAt(p.offset(0.5, 0.5, 0.5), true)
  await bot.activateBlock(b)
  await sleep(500)
  const after = bot.blockAt(p).getProperties().open
  const want = step.expect ? String(after) === String(step.expect === 'open') : String(before) !== String(after)
  return { name: b.name, before, after, ok: want }
}

async function sleepStep(step) {
  const b = bot.blockAt(v(step.pos))
  try { await bot.sleep(b); const ok = bot.isSleeping; await bot.wake().catch(() => {}); return { ok, bed: b.name } } catch (e) { return { ok: false, error: e.message, bed: b && b.name } }
}

async function containerStep(step) {
  const b = bot.blockAt(v(step.pos))
  try {
    const c = await bot.openContainer(b)
    const items = c.containerItems().map(i => ({ name: i.name, count: i.count }))
    c.close()
    await sleep(300)
    return { ok: true, block: b.name, slots: c.inventoryStart, items }
  } catch (e) { return { ok: false, block: b && b.name, error: e.message } }
}

async function swimStep(step) {
  await tp(step.target)
  await sleep(1500)
  const inWater = bot.entity.isInWater
  const ydrift = bot.entity.position.y
  return { ok: !!inWater, isInWater: !!inWater, y: +ydrift.toFixed(2) }
}

async function runStep(step) {
  switch (step.type) {
    case 'tp': await tp(step.target); return { ok: true, at: fmt(bot.entity.position) }
    case 'goto': return gotoStep(step)
    case 'walk': return manualWalk(step)
    case 'climb': return climb(step)
    case 'door': return doorStep(step)
    case 'sleep': return sleepStep(step)
    case 'container': return containerStep(step)
    case 'swim': return swimStep(step)
    case 'wait': await sleep(step.ms); return { ok: true }
    case 'cmd': bot.chat('/' + step.cmd); await sleep(step.ms ?? 500); return { ok: true }
    default: return { ok: false, error: 'unknown step ' + step.type }
  }
}

bot.once('spawn', async () => {
  await sleep(2500)
  try {
    for (const step of scenario.steps) {
      let r
      try { r = await runStep(step) } catch (e) { r = { ok: false, error: String(e && e.stack || e) } }
      results.steps.push({ name: step.name, type: step.type, ...r })
      console.log(step.name, r.ok ? 'OK' : 'FAIL', JSON.stringify(r).slice(0, 200))
    }
  } finally {
    results.final_health = bot.health
    fs.writeFileSync(resultPath, JSON.stringify(results, null, 1))
    bot.quit()
    setTimeout(() => process.exit(0), 500)
  }
})
setTimeout(() => { results.events.push('global timeout'); fs.writeFileSync(resultPath, JSON.stringify(results, null, 1)); process.exit(1) }, (scenario.global_timeout ?? 600) * 1000)
