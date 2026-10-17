// Contract-driven UI verification only: all API/Auth replies are intercepted.
// No paid AI calls, real credentials, or shared database writes.
// node tests/community-flows-smoke.cjs <playwright module> <browser exe> <site URL> <screenshot>
const assert = require('node:assert/strict')
const { chromium } = require(process.argv[2])
const reportId = '00000000-0000-4000-8000-000000000001'
const clearId = '00000000-0000-4000-8000-000000000002'
const userId = '00000000-0000-4000-8000-000000000003'
const time = '2026-10-16T01:00:00Z'
const user = { id: userId, aud: 'authenticated', role: 'authenticated', email: 'fixture@example.com', app_metadata: {}, user_metadata: {}, created_at: time }
const encode = value => Buffer.from(JSON.stringify(value)).toString('base64url')
const token = `${encode({ alg: 'HS256', typ: 'JWT' })}.${encode({ sub: userId, exp: Math.floor(Date.now() / 1000) + 3600, role: 'authenticated' })}.test-only`
const report = { id: reportId, place_id: 'hub', campus_id: 'iium-gombak', barrier_type: 'blocked_ramp', description: 'Fictional blocked ramp', observed_at: time, submitted_at: time, evidence_urls: [], status: 'community_corroborated', community: { supporters: 3, disputes: 0 }, clearance_observations: [] }
let addedReport = null
const warning = () => [report, ...(addedReport ? [addedReport] : [])]
  .filter(item => item.status !== 'resolved')
  .map(item => ({ report_id: item.id, description: item.description, status: item.status }))
const place = (id, name, toilet, category) => ({ id, name, campus_id: 'iium-gombak', category, coordinates: { latitude: 3.25, longitude: 101.73 }, facilities: { step_free_entrance: 'yes', accessible_toilet: toilet, designated_parking: 'unknown' }, active_warnings: id === 'hub' ? warning() : [], is_demo: true, description: 'Fictional browser fixture', entrances: [], observations: [{ facility: 'accessible_toilet', value: toilet, source: 'Fictional fixture', observed_at: null, evidence_urls: [], notes: null }] })
const hub = () => place('hub', 'Fictional Study Hub', 'yes', 'study')
const library = () => place('library', 'Fictional Library', 'no', 'library')
let chatCount = 0, clearingCount = 0, voteCount = 0, historyCount = 0
const chatRequests = [], clearingRequests = []
const history = Array.from({ length: 21 }, (_, i) => ({ id: `event-${i === 0 ? 99 : i}`, report_id: reportId, occurred_at: time, action: i === 0 ? 'report_created' : i === 1 ? 'clearance_submitted' : 'vote_updated', previous_status: i ? 'unverified' : null, new_status: 'unverified', community: { supporters: 0, disputes: 0 } }))

async function main() {
  const browser = await chromium.launch({ executablePath: process.argv[3], headless: true })
  try {
    const page = await browser.newPage({ viewport: { width: 1280, height: 960 } })
    const errors = []
    page.on('pageerror', error => errors.push(error.message))
    await page.route('**/auth/v1/**', async route => {
      await route.fulfill({ json: { access_token: token, token_type: 'bearer', expires_in: 3600, refresh_token: 'fixture-refresh', user } })
    })
    await page.route('**/api/**', async route => {
      const request = route.request(), url = new URL(request.url()), path = url.pathname
      const reply = (json, status = 200) => route.fulfill({ status, json })
      if (path === '/api/chat') {
        chatRequests.push(request.postDataJSON())
        if (++chatCount === 1) return reply({ error: { code: 'service_unavailable', message: 'AI server is unavailable.' } }, 503)
        if (chatCount > 2) return reply({ answer: 'Which building do you mean?', status: 'clarification', data_mode: 'demo', applied_filters: null, total_matches: null, sources: [], places: [] })
        return reply({ answer: 'Fictional demo: the hub matches. The library does not have the required toilet.', status: 'answered', data_mode: 'demo', applied_filters: { q: null, category: 'study', step_free_entrance: true, accessible_toilet: true, designated_parking: false }, total_matches: 1, places: [hub()], sources: [hub(), library()] })
      }
      if (path.endsWith('/history')) {
        if (++historyCount === 1) return reply({ error: { message: 'History unavailable.' } }, 503)
        const offset = Number(url.searchParams.get('offset') || 0)
        return reply({ items: history.slice(offset, offset + 20), total: history.length, offset, limit: 20 })
      }
      if (path.endsWith('/clearance-observations')) {
        assert.ok(request.headers().authorization, 'Contribution sends session token')
        clearingRequests.push({ body: request.postDataJSON(), key: request.headers()['idempotency-key'] })
        if (++clearingCount === 1) return reply({ error: { message: 'Community service unavailable.' } }, 503)
        const claim = { id: clearId, ...request.postDataJSON(), submitted_at: time, status: 'unverified', community: { supporters: 0, disputes: 0 } }
        report.clearance_observations = [claim]
        return reply(claim, 201)
      }
      if (path.endsWith(`/clearance-observations/${clearId}/votes`)) {
        if (++voteCount === 1) return reply({ error: { message: 'You cannot vote on your own clearing observation.' } }, 403)
        const stance = request.postDataJSON().stance
        report.status = stance === 'corroborate' ? 'resolved' : 'community_corroborated'
        report.clearance_observations[0].status = stance === 'corroborate' ? 'community_corroborated' : 'disputed'
        report.clearance_observations[0].community = { supporters: stance === 'corroborate' ? 3 : 2, disputes: stance === 'corroborate' ? 0 : 1 }
        return reply(report)
      }
      if (path === '/api/places') return reply({ items: [hub(), library()], total: 2, limit: 100, offset: 0 })
      if (path === '/api/places/hub') return reply(hub())
      if (path === '/api/places/library') return reply(library())
      if (path === '/api/reports' && request.method() === 'POST') {
        addedReport = { ...request.postDataJSON(), id: '00000000-0000-4000-8000-000000000004', campus_id: 'iium-gombak', submitted_at: time, status: 'unverified', community: { supporters: 0, disputes: 0 }, clearance_observations: [] }
        return reply(addedReport, 201)
      }
      if (path === '/api/reports') return reply({ items: url.searchParams.get('place_id') === 'hub' ? [...(addedReport ? [addedReport] : []), report] : [], total: addedReport ? 2 : 1, limit: 20, offset: 0 })
      return reply({ error: { message: `Unexpected test request ${path}` } }, 404)
    })
    await page.goto(process.argv[4])
    await page.getByRole('heading', { name: 'Ask about campus access' }).waitFor()
    const question = page.getByLabel('Your question')
    await question.fill('Find a study space with an accessible toilet')
    await page.getByRole('button', { name: 'Ask assistant' }).click()
    await page.getByText('AI server is unavailable.', { exact: true }).waitFor()
    assert.equal(await question.inputValue(), 'Find a study space with an accessible toilet')
    await page.getByRole('button', { name: 'Retry question' }).click()
    await page.getByText('Fictional local demo data', { exact: true }).waitFor()
    const buildings = page.getByRole('region', { name: 'Buildings', exact: true })
    assert.equal(await buildings.getByRole('button', { name: 'Fictional Library', exact: true }).count(), 0)
    await buildings.getByRole('button', { name: /^Fictional Study Hub/ }).waitFor()
    assert.equal(await page.getByRole('button', { name: 'Open Fictional Library', exact: true }).count(), 1)
    await question.fill('What about that building?')
    await page.getByRole('button', { name: 'Ask assistant' }).click()
    await page.getByText('Which building do you mean?', { exact: false }).waitFor()
    assert.equal(chatRequests[2].history.length, 2, 'Only successful turns enter bounded history')
    await page.getByRole('button', { name: 'Open Fictional Study Hub', exact: true }).click()
    await page.getByRole('heading', { name: /^Fictional Study Hub/ }).waitFor()
    assert.equal(await page.getByRole('button', { name: 'Submit clearing observation' }).count(), 0, 'Signed-out visitor cannot submit')
    await page.getByRole('link', { name: 'Log in', exact: true }).first().click()
    await page.getByLabel('Username or email').fill('fixture@example.com')
    await page.getByLabel('Password', { exact: true }).fill('fixture-password')
    await page.getByRole('button', { name: 'Log in', exact: true }).click()
    await page.getByRole('button', { name: /^Fictional Study Hub/ }).click()
    const card = page.getByRole('article', { name: 'Barrier report: Fictional blocked ramp' })
    await card.locator('summary').filter({ hasText: 'Report history' }).click()
    await card.getByText('History unavailable.', { exact: true }).waitFor()
    assert.equal(await card.getByText('No history recorded.', { exact: true }).count(), 0)
    await card.getByRole('button', { name: 'Retry history' }).click()
    await card.getByRole('list', { name: 'Report timeline' }).waitFor()
    let timeline = card.getByRole('list', { name: 'Report timeline' }).getByRole('listitem')
    assert.match(await timeline.nth(0).innerText(), /Barrier reported/)
    assert.match(await timeline.nth(1).innerText(), /Clearing observation submitted/)
    assert.equal(await timeline.count(), 20)
    await card.getByRole('button', { name: 'Load more history' }).click()
    await page.waitForFunction(() => document.querySelectorAll('[aria-label="Report timeline"] > li').length === 21)
    await card.locator('summary').filter({ hasText: 'Report that this barrier has cleared' }).click()
    await card.getByLabel('What has changed?').fill('Fictional ramp is clear now')
    await card.getByRole('button', { name: 'Submit clearing observation' }).click()
    await card.getByText('Community service unavailable.', { exact: true }).waitFor()
    assert.equal(await card.getByLabel('What has changed?').inputValue(), 'Fictional ramp is clear now')
    const clearingTime = await card.getByLabel('When did you observe it? (your local time)').inputValue()
    // A separate successful barrier must not remount this card or discard its
    // failed clearing submission's draft, timestamp, open history or retry UUID.
    await page.getByLabel('A temporary barrier', { exact: true }).check()
    await page.getByLabel('Describe the barrier', { exact: true }).fill('Fictional separate barrier')
    await page.getByRole('button', { name: 'Send information', exact: true }).click()
    await page.getByRole('article', { name: 'Barrier report: Fictional separate barrier' }).waitFor()
    assert.equal(await card.getByLabel('What has changed?').inputValue(), 'Fictional ramp is clear now', 'Separate barrier preserves clearing draft')
    assert.equal(await card.getByLabel('When did you observe it? (your local time)').inputValue(), clearingTime)
    assert.equal(await card.getByRole('list', { name: 'Report timeline' }).isVisible(), true, 'Open history survives refresh')
    await page.getByRole('button', { name: /Fictional Study Hub.*2 active barrier/ }).waitFor()
    await card.getByRole('button', { name: 'Submit clearing observation' }).click()
    await card.getByText('Fictional ramp is clear now', { exact: true }).waitFor()
    assert.deepEqual(clearingRequests[0], clearingRequests[1], 'Retries preserve complete body, timestamp and UUID')
    await card.getByRole('button', { name: 'Corroborate clearing' }).click()
    await card.getByText('You cannot vote on your own clearing observation.', { exact: true }).waitFor()
    await card.getByRole('button', { name: 'Corroborate clearing' }).click()
    await card.getByRole('heading', { name: 'Resolved', exact: true }).waitFor()
    await page.waitForFunction(() => {
      const warnings = document.querySelector('[aria-label="Active building warnings"]')
      return warnings && !warnings.textContent.includes('Fictional blocked ramp') && warnings.textContent.includes('Fictional separate barrier')
    })
    await card.getByRole('button', { name: 'Dispute clearing' }).click()
    await page.getByLabel('Active building warnings').getByText('Fictional blocked ramp', { exact: false }).waitFor()
    await page.setViewportSize({ width: 390, height: 844 })
    assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true, 'Mobile layout does not overflow')
    assert.deepEqual(errors, [], 'No browser runtime exceptions')
    await page.screenshot({ path: process.argv[5], fullPage: true })
    console.log('UI contract checks passed: chat outage/retry, result/source separation, history order/pagination/error, clearing retry/auth/voting and warning refresh. No live services used.')
  } finally { await browser.close() }
}
main().catch(error => { console.error(error); process.exitCode = 1 })
