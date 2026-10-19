// Minecraft Java block-model renderer: blockstates + models + textures come from the vanilla client jar (served at /assets).
// Entity-rendered blocks (bed, chest, skull) have no block model in the jar and are rebuilt from the entity textures with
// the standard ModelPart box UV unwrap. Lighting is flat "studio" shading (vanilla per-face factors), NOT in-game light.
import * as THREE from 'three'

const A = '/assets/minecraft/'
const jsonCache = new Map(), texCache = new Map(), modelCache = new Map(), stateCache = new Map()
const getJSON = async p => { if (!jsonCache.has(p)) jsonCache.set(p, fetch(A + p).then(r => r.ok ? r.json() : null)); return jsonCache.get(p) }
const strip = id => id.replace(/^minecraft:/, '')

function loadImage(url) { return new Promise((res, rej) => { const i = new Image(); i.onload = () => res(i); i.onerror = () => rej(new Error('img ' + url)); i.src = url }) }
async function getTex(name, entity) {
  const key = (entity ? 'e:' : 'b:') + name
  if (!texCache.has(key)) texCache.set(key, (async () => {
    const img = await loadImage(A + 'textures/' + (entity ? name : strip(name)) + '.png')
    const w = img.width, h = entity ? img.height : img.width // animated strips: first frame only
    const c = document.createElement('canvas'); c.width = w; c.height = h
    c.getContext('2d').drawImage(img, 0, 0, w, h, 0, 0, w, h)
    const t = new THREE.CanvasTexture(c); t.magFilter = THREE.NearestFilter; t.minFilter = THREE.NearestFilter
    t.colorSpace = THREE.SRGBColorSpace; t.generateMipmaps = false
    const px = c.getContext('2d').getImageData(0, 0, w, h).data
    let translucent = false; for (let i = 3; i < px.length; i += 4) if (px[i] > 0 && px[i] < 250) { translucent = true; break }
    return { tex: t, w, h, translucent }
  })())
  return texCache.get(key)
}

async function resolveModel(id) {
  id = strip(id)
  if (modelCache.has(id)) return modelCache.get(id)
  const p = (async () => {
    const m = await getJSON('models/' + id + '.json')
    if (!m) return { textures: {}, elements: [] }
    let parent = m.parent ? await resolveModel(m.parent) : { textures: {}, elements: null }
    return { textures: { ...parent.textures, ...(m.textures || {}) }, elements: m.elements || parent.elements, ao: m.ambientocclusion }
  })()
  modelCache.set(id, p); return p
}
const sprite = r => (r && typeof r === 'object') ? r.sprite : r // 26.x texture entries may be {sprite, force_translucent}
const texRef = (ref, tex) => { let n = 0; ref = sprite(ref); while (ref && ref[0] === '#' && n++ < 20) ref = sprite(tex[ref.slice(1)]); return ref }

const DIRS = { down: [0, -1, 0], up: [0, 1, 0], north: [0, 0, -1], south: [0, 0, 1], west: [-1, 0, 0], east: [1, 0, 0] }
const FACEV = (f, t) => { const [x0, y0, z0] = f, [x1, y1, z1] = t; return {
  down: [[x0, y0, z1], [x0, y0, z0], [x1, y0, z0], [x1, y0, z1]], up: [[x0, y1, z0], [x0, y1, z1], [x1, y1, z1], [x1, y1, z0]],
  north: [[x1, y1, z0], [x1, y0, z0], [x0, y0, z0], [x0, y1, z0]], south: [[x0, y1, z1], [x0, y0, z1], [x1, y0, z1], [x1, y1, z1]],
  west: [[x0, y1, z0], [x0, y0, z0], [x0, y0, z1], [x0, y1, z1]], east: [[x1, y1, z1], [x1, y0, z1], [x1, y0, z0], [x1, y1, z0]] } }
const defUV = (d, f, t) => { const [x1, y1, z1] = f, [x2, y2, z2] = t; return {
  down: [x1, 16 - z2, x2, 16 - z1], up: [x1, z1, x2, z2], north: [16 - x2, 16 - y2, 16 - x1, 16 - y1],
  south: [x1, 16 - y2, x2, 16 - y1], west: [z1, 16 - y2, z2, 16 - y1], east: [16 - z2, 16 - y2, 16 - z1, 16 - y1] }[d] }

function rotAxis(p, axis, deg, o) {
  const r = deg * Math.PI / 180, c = Math.cos(r), s = Math.sin(r)
  let [x, y, z] = [p[0] - o[0], p[1] - o[1], p[2] - o[2]]
  if (axis === 'y') [x, z] = [x * c - z * s, x * s + z * c]
  else if (axis === 'x') [y, z] = [y * c - z * s, y * s + z * c]
  else [x, y] = [x * c - y * s, x * s + y * c]
  return [x + o[0], y + o[1], z + o[2]]
}
const nearest = n => { const a = [Math.abs(n[0]), Math.abs(n[1]), Math.abs(n[2])]; const i = a.indexOf(Math.max(...a)); return i === 1 ? (n[1] > 0 ? 'up' : 'down') : i === 0 ? (n[0] > 0 ? 'east' : 'west') : (n[2] > 0 ? 'south' : 'north') }
const SHADE = { up: 1, down: 0.5, north: 0.8, south: 0.8, east: 0.6, west: 0.6 }

// a quad: {v:[4][3] (block-local 0..16), uv:[4][2] (0..1 three-space), tex:{name,entity}, tint, cull, dir}
async function modelQuads(modelId, rx, ry) {
  const m = await resolveModel(modelId)
  const quads = []
  for (const el of m.elements || []) {
    const fv = FACEV(el.from, el.to)
    for (const [d, face] of Object.entries(el.faces || {})) {
      let v = fv[d].map(p => p.slice())
      if (el.rotation) {
        const { origin, axis, angle, rescale } = el.rotation
        v = v.map(p => { let q = rotAxis(p, axis, angle, origin)
          if (rescale) { const k = 1 / Math.cos(angle * Math.PI / 180); const idx = axis === 'x' ? [1, 2] : axis === 'y' ? [0, 2] : [0, 1]
            for (const i of idx) q[i] = origin[i] + (q[i] - origin[i]) * k } return q })
      }
      let uv = face.uv || defUV(d, el.from, el.to)
      const [u0, v0, u1, v1] = uv
      let c = [[u0, v0], [u0, v1], [u1, v1], [u1, v0]]
      const rot = ((face.rotation || 0) / 90) % 4
      for (let i = 0; i < rot; i++) c.unshift(c.pop())
      c = c.map(([u, vv]) => [u / 16, 1 - vv / 16])
      let dirv = DIRS[d].slice(), cull = face.cullface
      const rotAll = p => { let q = p; if (rx) q = rotAxis(q, 'x', rx, [8, 8, 8]); if (ry) q = rotAxis(q, 'y', ry, [8, 8, 8]); return q }
      v = v.map(rotAll)
      if (rx || ry) {
        dirv = rotAll([8 + dirv[0], 8 + dirv[1], 8 + dirv[2]]).map(x => x - 8)
        if (cull) { const t = rotAll([8 + DIRS[cull][0], 8 + DIRS[cull][1], 8 + DIRS[cull][2]]).map(x => Math.round(x - 8)); cull = nearest(t) }
      }
      const tn = texRef(face.texture, m.textures)
      if (!tn || tn[0] === '#') continue
      quads.push({ v, uv: c, tex: { name: tn }, tint: face.tintindex, cull, dir: nearest(dirv), shade: el.shade !== false })
    }
  }
  return quads
}

function matches(when, props) {
  if (!when) return true
  if (when.OR) return when.OR.some(w => matches(w, props))
  if (when.AND) return when.AND.every(w => matches(w, props))
  return Object.entries(when).every(([k, val]) => String(val).split('|').includes(String(props[k])))
}
async function stateQuads(name, props) {
  const key = name + JSON.stringify(props)
  if (stateCache.has(key)) return stateCache.get(key)
  const p = (async () => {
    const bs = await getJSON('blockstates/' + strip(name) + '.json')
    if (!bs) return { quads: [], opaque: false }
    let applies = []
    if (bs.variants) {
      for (const [k, v] of Object.entries(bs.variants)) {
        const ok = k === '' || k.split(',').every(pair => { const [a, b] = pair.split('='); return String(props[a]) === b })
        if (ok) { applies = [Array.isArray(v) ? v[0] : v]; break }
      }
    } else if (bs.multipart) {
      for (const part of bs.multipart) if (matches(part.when, props)) applies.push(Array.isArray(part.apply) ? part.apply[0] : part.apply)
    }
    let quads = []
    for (const a of applies) quads = quads.concat(await modelQuads(a.model, a.x || 0, a.y || 0))
    let opaque = false
    if (applies.length === 1) {
      const m = await resolveModel(applies[0].model)
      const e = m.elements || []
      opaque = e.length === 1 && !e[0].rotation && e[0].from.every(x => x === 0) && e[0].to.every(x => x === 16) &&
        Object.keys(e[0].faces).length === 6 && !/glass|ice|leaves|slime|honey/.test(strip(name))
    }
    return { quads, opaque }
  })()
  stateCache.set(key, p); return p
}

// ---- entity-style boxes (bed, chest, skull, figure) ----
function boxQuads(min, max, uvFor, tex) { // uvFor(dir)->[u0,v0,u1,v1] in texture pixels, or null; coords in 0..16 block units
  const fv = FACEV(min, max), out = []
  for (const d of Object.keys(fv)) {
    const r = uvFor(d); if (!r) continue
    out.push({ v: fv[d], uvpx: r, tex, tint: undefined, cull: null, dir: d, shade: true })
  }
  return out
}
function ucube(u, v, w, h, d) { // ModelPart.Cube unwrap: returns dir -> [u0,v0,u1,v1] (north=front, -z)
  return { up: [u + d, v, u + d + w, v + d], down: [u + d + w, v, u + d + 2 * w, v + d], west: [u, v + d, u + d, v + d + h],
    north: [u + d, v + d, u + d + w, v + d + h], east: [u + d + w, v + d, u + 2 * d + w, v + d + h], south: [u + 2 * d + w, v + d, u + 2 * d + 2 * w, v + d + h] }
}
const yrot = (qs, deg, c = [8, 8]) => qs.map(q => ({ ...q, v: q.v.map(p => { const r = deg * Math.PI / 180, x = p[0] - c[0], z = p[2] - c[1]
  return [c[0] + x * Math.cos(r) - z * Math.sin(r), p[1], c[1] + x * Math.sin(r) + z * Math.cos(r)] }), dir: q.dir }))
const FACING_Y = { south: 0, west: 90, north: 180, east: 270 }

function bedQuads(props) {
  const head = props.part === 'head', face = props.facing // facing = direction foot -> head
  const T = { name: 'entity/bed/gray', entity: true }
  // build facing south (+z = head direction), then rotate to the real facing
  const sx = [[0, 6], [22, 6]] // west/east long-side regions
  const top = head ? [6, 6, 22, 22] : [6, 28, 22, 44]
  const side = h => head ? [0, 6, 6, 22] : [0, 28, 6, 44]
  const side2 = head ? [22, 6, 28, 22] : [22, 28, 28, 44]
  const endOuter = head ? [6, 0, 22, 6] : [6, 22, 22, 28]
  const uvs = { up: top, west: side(), east: side2, north: head ? [22, 22, 38, 28] : endOuter, south: head ? endOuter : [22, 22, 38, 28] }
  // texture v grows toward the foot end in the unwrap, so flip: head end is +z => v small at +z
  const qs = boxQuads([0, 3, 0], [16, 9, 16], d => uvs[d], T)
  for (const q of qs) { // orient pillow/blanket toward head (+z): swap v direction by reversing corner order for top/sides
    if (['up', 'west', 'east'].includes(q.dir)) { q.flipV = true }
  }
  const legMin = [[0, 0, 0], [13, 0, 0], [0, 0, 13], [13, 0, 13]]
  const legs = legMin.flatMap(m => boxQuads(m, [m[0] + 3, 3, m[2] + 3], () => [50, 6, 53, 9], T))
  return yrot(qs.concat(legs), FACING_Y[face])
}
function chestQuads(props) {
  const T = { name: 'entity/chest/normal', entity: true }
  const lid = ucube(0, 0, 14, 5, 14), body = ucube(0, 19, 14, 10, 14)
  const q = boxQuads([1, 0, 1], [15, 10, 15], d => body[d], T).concat(boxQuads([1, 9, 1], [15, 14, 15], d => lid[d], T))
  q.push(...boxQuads([7, 7, 0], [9, 11, 1], d => ucube(0, 0, 2, 4, 1)[d], T))
  return yrot(q, { north: 0, east: 90, south: 180, west: 270 }[props.facing || 'south'])
}
function skullQuads(props) {
  const T = { name: 'entity/skeleton/skeleton', entity: true }
  const c = ucube(0, 0, 8, 8, 8)
  return yrot(boxQuads([4, 0, 4], [12, 8, 12], d => c[d], T), 180 - (+props.rotation || 0) * 22.5)
}
const SPECIAL = { bed: bedQuads, chest: chestQuads, skeleton_skull: skullQuads }

// ---- scene assembly ----
let renderer
const waterTint = [0.247, 0.463, 0.894]
const key = (x, y, z) => x + ',' + y + ',' + z

async function buildScene(scene, spec) {
  const pal = scene.palette
  const grid = new Map()
  const keep = (x, y, z) => {
    const f = spec.filter || {}
    if (f.ymax !== undefined && y > f.ymax) return false
    if (f.ymin !== undefined && y < f.ymin) return false
    for (const r of f.remove || []) { const val = { x, y, z }[r.axis]; if (r.lt !== undefined && val < r.lt) return false; if (r.gt !== undefined && val > r.gt) return false; if (r.eq !== undefined && val === r.eq) return false }
    return true
  }
  for (const [x, y, z, i] of scene.blocks) if (keep(x, y, z)) grid.set(key(x, y, z), pal[i])
  const sq = {}
  for (const [k, b] of grid) sq[k] = await stateQuads(b.name, b.props || {})
  const groups = new Map() // material key -> {positions, uvs, colors, tex, translucent}
  const add = async (q, bx, by, bz, extraTint) => {
    const t = await getTex(q.tex.name, q.tex.entity)
    const mk = q.tex.name + (q.tex.entity ? ':e' : '')
    if (!groups.has(mk)) groups.set(mk, { p: [], u: [], c: [], tex: t, translucent: t.translucent || /glass|water_still/.test(q.tex.name) && !/pane_top/.test(q.tex.name) })
    const g = groups.get(mk)
    const sh = q.shade ? SHADE[q.dir] : 1
    let col = [sh, sh, sh]
    if (extraTint) col = [col[0] * extraTint[0], col[1] * extraTint[1], col[2] * extraTint[2]]
    const uv = q.uvpx ? (() => { const [u0, v0, u1, v1] = q.uvpx; const W = t.w, H = t.h
      const a = [[u0, v0], [u0, v1], [u1, v1], [u1, v0]]
      let c = a.map(([u, v]) => [u / W, 1 - v / H])
      if (q.flipV) c = [c[1], c[0], c[3], c[2]]
      return c })() : q.uv
    const idx = [0, 1, 2, 0, 2, 3]
    for (const i of idx) { const v = q.v[i]; g.p.push(bx + v[0] / 16, by + v[1] / 16, bz + v[2] / 16); g.u.push(uv[i][0], uv[i][1]); g.c.push(...col) }
  }
  const NB = { down: [0, -1, 0], up: [0, 1, 0], north: [0, 0, -1], south: [0, 0, 1], west: [-1, 0, 0], east: [1, 0, 0] }
  for (const [k, b] of grid) {
    const [x, y, z] = k.split(',').map(Number)
    const name = strip(b.name), props = b.props || {}
    if (name === 'air' || name === 'cave_air' || name === 'structure_void') continue
    if (name === 'water') {
      const top = 14.2
      const h = 'water_still'
      for (const d of Object.keys(NB)) {
        const nb = grid.get(key(x + NB[d][0], y + NB[d][1], z + NB[d][2]))
        if (nb && (strip(nb.name) === 'water' || (sq[key(x + NB[d][0], y + NB[d][1], z + NB[d][2])] || {}).opaque)) continue
        const above = grid.get(key(x, y + 1, z))
        const hh = above && strip(above.name) === 'water' ? 16 : top
        const fv = FACEV([0, 0, 0], [16, hh, 16])[d]
        await add({ v: fv, uv: [[0, 1], [0, 0], [1, 0], [1, 1]], tex: { name: 'block/water_still' }, dir: d, shade: true }, x, y, z, waterTint)
      }
      continue
    }
    let quads
    if (SPECIAL[name]) quads = SPECIAL[name](props)
    else quads = (sq[k] || { quads: [] }).quads
    for (const q of quads) {
      if (q.cull) { const n = NB[q.cull]; const nk = key(x + n[0], y + n[1], z + n[2]); if ((sq[nk] || {}).opaque) continue }
      await add(q, x, y, z, q.tint !== undefined && /grass|leaves|vine|water/.test(name) ? [0.55, 0.75, 0.35] : null)
    }
  }
  return groups
}

function addBox(grp, min, max, color, wire) {
  const g = new THREE.BoxGeometry(max[0] - min[0], max[1] - min[1], max[2] - min[2])
  g.translate((min[0] + max[0]) / 2, (min[1] + max[1]) / 2, (min[2] + max[2]) / 2)
  if (wire) { const l = new THREE.LineSegments(new THREE.EdgesGeometry(g), new THREE.LineBasicMaterial({ color, depthTest: false })); l.renderOrder = 10; grp.add(l) }
  else { const m = new THREE.Mesh(g, new THREE.MeshBasicMaterial({ color })); grp.add(m) }
}
function figure(grp, pos, facingDeg) { // ~1.875-block human reference (flat colours, deliberately not a skin)
  const k = 0.9375 / 16, [px, py, pz] = pos
  const f = new THREE.Group()
  const part = (w, h, d, x, y, z, col) => { const g = new THREE.Mesh(new THREE.BoxGeometry(w * k, h * k, d * k), new THREE.MeshBasicMaterial({ color: col })); g.position.set(x * k, (y + h / 2) * k, z * k); f.add(g) }
  part(4, 12, 4, -2, 0, 0, 0x3b3b9a); part(4, 12, 4, 2, 0, 0, 0x3b3b9a)
  part(8, 12, 4, 0, 12, 0, 0x14a0a0); part(4, 12, 4, -6, 12, 0, 0xc69774); part(4, 12, 4, 6, 12, 0, 0xc69774)
  part(8, 8, 8, 0, 24, 0, 0xc69774)
  f.position.set(px + 0.5, py, pz + 0.5); f.rotation.y = facingDeg * Math.PI / 180; grp.add(f)
}

async function render(job) {
  const scene3 = new THREE.Scene()
  const W = job.w, H = job.h, SS = job.ss || 2
  if (!renderer) { renderer = new THREE.WebGLRenderer({ antialias: true, preserveDrawingBuffer: true }); renderer.outputColorSpace = THREE.SRGBColorSpace; document.body.appendChild(renderer.domElement) }
  renderer.setPixelRatio(1); renderer.setSize(W * SS, H * SS, false)
  renderer.setClearColor(job.bg || '#2b3038', 1)
  const groups = await buildScene(job.scene, job)
  const gain = job.gain || 1.35
  const root = new THREE.Group(); scene3.add(root)
  let min = [1e9, 1e9, 1e9], max = [-1e9, -1e9, -1e9]
  for (const [, g] of groups) {
    const geo = new THREE.BufferGeometry()
    geo.setAttribute('position', new THREE.Float32BufferAttribute(g.p, 3)); geo.setAttribute('uv', new THREE.Float32BufferAttribute(g.u, 2)); geo.setAttribute('color', new THREE.Float32BufferAttribute(g.c, 3))
    const mat = new THREE.MeshBasicMaterial({ map: g.tex.tex, vertexColors: true, side: THREE.DoubleSide, alphaTest: g.translucent ? 0.01 : 0.5, transparent: g.translucent, opacity: /water/.test('') ? 1 : (g.translucent && g.tex.w === 16 && g.tex.h === 16 && false ? 1 : 1), depthWrite: !g.translucent })
    mat.color.setScalar(gain)
    if (g.translucent) mat.opacity = 0.78
    const mesh = new THREE.Mesh(geo, mat); mesh.renderOrder = g.translucent ? 5 : 0; root.add(mesh)
    for (let i = 0; i < g.p.length; i += 3) for (let a = 0; a < 3; a++) { min[a] = Math.min(min[a], g.p[i + a]); max[a] = Math.max(max[a], g.p[i + a]) }
  }
  if (job.bounds) { min = job.bounds[0]; max = job.bounds[1] }
  const ctr = job.target || [(min[0] + max[0]) / 2, (min[1] + max[1]) / 2, (min[2] + max[2]) / 2]
  if (job.pad !== false) { // neutral reference pad
    const pad = new THREE.Mesh(new THREE.PlaneGeometry(max[0] - min[0] + 8, max[2] - min[2] + 8), new THREE.MeshBasicMaterial({ color: 0x3a404a, side: THREE.DoubleSide }))
    pad.rotation.x = -Math.PI / 2; pad.position.set((min[0] + max[0]) / 2, min[1] - 0.02, (min[2] + max[2]) / 2); root.add(pad)
    const grid = new THREE.GridHelper(Math.max(max[0] - min[0], max[2] - min[2]) + 8, Math.round(Math.max(max[0] - min[0], max[2] - min[2]) + 8), 0x4b525d, 0x4b525d)
    grid.position.set((min[0] + max[0]) / 2, min[1] - 0.015, (min[2] + max[2]) / 2); root.add(grid)
  }
  for (const e of job.extras || []) {
    if (e.type === 'box') addBox(root, e.min, e.max, e.color || '#ff3355', e.wire !== false)
    if (e.type === 'figure') figure(root, e.pos, e.facing || 0)
  }
  const az = (job.az || 0) * Math.PI / 180, el = (job.el === undefined ? 30 : job.el) * Math.PI / 180
  const dir = new THREE.Vector3(Math.sin(az) * Math.cos(el), Math.sin(el), Math.cos(az) * Math.cos(el))
  const cam = new THREE.OrthographicCamera(-1, 1, 1, -1, -500, 500)
  const target = new THREE.Vector3(...ctr)
  cam.position.copy(target).addScaledVector(dir, 200)
  cam.up.set(0, 1, 0); if (job.el >= 89) cam.up.set(-Math.sin(az), 0, -Math.cos(az))
  cam.lookAt(target); cam.updateMatrixWorld(); cam.updateProjectionMatrix()
  const right = new THREE.Vector3().setFromMatrixColumn(cam.matrixWorld, 0), up = new THREE.Vector3().setFromMatrixColumn(cam.matrixWorld, 1)
  let hw, hh
  if (job.scale) { hw = W / (2 * job.scale); hh = H / (2 * job.scale) }
  else {
    let rmin = 1e9, rmax = -1e9, umin = 1e9, umax = -1e9
    for (const x of [min[0], max[0]]) for (const y of [min[1], max[1]]) for (const z of [min[2], max[2]]) {
      const p = new THREE.Vector3(x, y, z).sub(target); const r = p.dot(right), u = p.dot(up)
      rmin = Math.min(rmin, r); rmax = Math.max(rmax, r); umin = Math.min(umin, u); umax = Math.max(umax, u) }
    const wr = (rmax - rmin) * (1 + (job.margin ?? 0.1)), wu = (umax - umin) * (1 + (job.margin ?? 0.1)), asp = W / H
    hw = Math.max(wr / 2, wu / 2 * asp); hh = hw / asp
    const cr = (rmax + rmin) / 2, cu = (umax + umin) / 2
    cam.position.addScaledVector(right, cr).addScaledVector(up, cu); target.addScaledVector(right, cr).addScaledVector(up, cu)
  }
  cam.left = -hw; cam.right = hw; cam.top = hh; cam.bottom = -hh; cam.updateProjectionMatrix()
  renderer.render(scene3, cam)
  const out = renderer.domElement.toDataURL('image/png')
  root.traverse(o => { if (o.geometry) o.geometry.dispose() })
  return { png: out, pxPerBlock: (W * SS) / (2 * hw) / SS, blocks: job.scene.blocks.length }
}
window.renderJob = render
window.ready = true
