/**
 * Certificate issuance: binary POST with refresh-and-retry, 19 August 2026.
 *
 * This exercises the candidate's own lib/eilps-http.ts — compiled from the
 * source that ships, not a reimplementation of it — against a stub server that
 * plays the exact sequences the acceptance test names.
 *
 * A stub is the right instrument here and not a shortcut. The real route is
 * POST /api/certificates/:level, which is authRequired plus a premium
 * entitlement, so exercising it live would mean either holding a real paid
 * entitlement or buying one, and the instruction is explicit that no live
 * purchase may be made to turn evidence green. What has to be proven is the
 * client contract: that an expired bearer is refreshed once and the retry
 * yields a PDF Blob, and that nothing else is ever mistaken for a download.
 * A stub proves that precisely, because it can produce a 401-then-200 sequence
 * and a 402 on demand, which a live server will not do to order.
 */
import http from 'node:http'

// The module reads its base URL once, at load, so the environment has to be set
// before the import rather than after it.
process.env.NEXT_PUBLIC_IELPS_API_BASE = 'http://127.0.0.1:4891'
const { ielpsFetchBlob, IelpsHttpError, clearIelpsSession } =
  await import('./cert-build/eilps-http.js')

const PDF = Buffer.from('%PDF-1.4\n%stub certificate\n%%EOF\n')

let script = {}
const log = []

const server = http.createServer(async (req, res) => {
  const chunks = []
  for await (const c of req) chunks.push(c)
  log.push(`${req.method} ${req.url} auth=${req.headers.authorization || 'none'}`)

  if (req.url === '/api/auth/refresh') {
    script.refreshes = (script.refreshes || 0) + 1
    if (script.refreshFails) {
      res.writeHead(401, { 'content-type': 'application/json' })
      return res.end('{"error":"unauthorized"}')
    }
    res.writeHead(200, { 'content-type': 'application/json' })
    return res.end(JSON.stringify({ accessToken: `token-${script.refreshes}` }))
  }

  script.certCalls = (script.certCalls || 0) + 1
  const step = script.responses[Math.min(script.certCalls - 1, script.responses.length - 1)]
  if (step.pdf) {
    res.writeHead(200, { 'content-type': 'application/pdf' })
    return res.end(PDF)
  }
  res.writeHead(step.status, { 'content-type': step.type || 'application/json' })
  res.end(step.body || '{}')
})

await new Promise((r) => server.listen(4891, '127.0.0.1', r))

const results = []

async function scenario(name, setup, expectation) {
  script = { ...setup, certCalls: 0, refreshes: 0 }
  clearIelpsSession()
  log.length = 0
  let outcome
  try {
    const blob = await ielpsFetchBlob('/api/certificates/B1', { method: 'POST' })
    outcome = {
      downloaded: true,
      type: blob.type,
      size: blob.size,
      head: Buffer.from(await blob.arrayBuffer()).subarray(0, 8).toString(),
    }
  } catch (error) {
    outcome = {
      downloaded: false,
      status: error instanceof IelpsHttpError ? error.status : null,
      state: error instanceof IelpsHttpError ? error.state : null,
      message: String(error.message).slice(0, 90),
    }
  }
  const pass = expectation(outcome, script)
  results.push({ name, pass, outcome, certCalls: script.certCalls, refreshes: script.refreshes, log: [...log] })
  console.log(`${pass ? 'PASS' : 'FAIL'}  ${name}`)
  console.log(`      ${JSON.stringify(outcome)}  certCalls=${script.certCalls} refreshes=${script.refreshes}`)
}

// The named acceptance case: the access token has expired, the refresh
// succeeds, and the single retry returns the PDF.
await scenario(
  'expired token -> refresh -> retry returns a PDF Blob',
  { responses: [{ status: 401, body: '{"error":"unauthorized"}' }, { pdf: true }] },
  (o, s) => o.downloaded && o.type.includes('pdf') && o.head.startsWith('%PDF') && s.certCalls === 2,
)

// Exactly once. A second 401 after a fresh bearer is an authentication
// failure, not something to keep retrying.
await scenario(
  'still 401 after refresh -> one retry only, no download',
  { responses: [{ status: 401, body: '{"error":"unauthorized"}' }] },
  (o, s) => !o.downloaded && o.status === 401 && o.state === 'authentication' && s.certCalls === 2,
)

// Everything below must not be mistaken for a file.
await scenario(
  '402 entitlement is not a download',
  { responses: [{ status: 402, body: '{"error":"payment required"}' }] },
  (o) => !o.downloaded && o.status === 402 && o.state === 'entitlement',
)
await scenario(
  '403 permission is not a download',
  { responses: [{ status: 403, body: '{"error":"forbidden"}' }] },
  (o) => !o.downloaded && o.status === 403 && o.state === 'permission',
)
await scenario(
  '403 administrator is classified as admin',
  { responses: [{ status: 403, body: '{"message":"Admin access required."}' }] },
  (o) => !o.downloaded && o.state === 'admin',
)
await scenario(
  '422 validation is not a download',
  { responses: [{ status: 422, body: '{"error":"invalid_level"}' }] },
  (o) => !o.downloaded && o.status === 422,
)
await scenario(
  '500 server error is not a download',
  { responses: [{ status: 500, body: '{"error":"server_error"}' }] },
  (o) => !o.downloaded && o.status === 500,
)
// A 200 carrying JSON instead of a PDF would otherwise reach the browser as a
// corrupt download, so the content type is checked as well as the status.
await scenario(
  '200 with a JSON body is refused, not saved as a PDF',
  { responses: [{ status: 200, type: 'application/json', body: '{"error":"not_a_pdf"}' }] },
  (o) => !o.downloaded && o.status === 200 && o.message.includes('Expected a PDF'),
)

server.close()
const passed = results.filter((r) => r.pass).length
console.log(`\n${passed}/${results.length} certificate binary-path checks passed`)
const fs = await import('node:fs')
fs.writeFileSync(
  '/var/lib/freelancer/projects/40470800/cert-blob-19b.json',
  JSON.stringify({ passed, total: results.length, results }, null, 2),
)
process.exit(passed === results.length ? 0 : 1)
