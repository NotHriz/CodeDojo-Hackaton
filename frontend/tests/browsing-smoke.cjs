// Run against real local API/Vite servers backed by disposable SQL fixtures.
// node tests/browsing-smoke.cjs <playwright module path> <browser exe> <site URL> <screenshot>
const assert = require('node:assert/strict')
const { chromium } = require(process.argv[2])

async function main() {
  const browser = await chromium.launch({ executablePath: process.argv[3], headless: true })
  try {
    const page = await browser.newPage({ viewport: { width: 1280, height: 960 } })
    const errors = []
    page.on('pageerror', error => errors.push(error.message))
    await page.goto(process.argv[4])
    for (let attempt = 0; attempt < 2; attempt++) {
      await page.getByRole('button', { name: /Fictional integration building/ }).click()
      await page.getByRole('heading', { name: 'Fictional integration building', exact: true }).waitFor()
      await page.getByRole('heading', { name: 'Access features' }).waitFor()
      await page.getByLabel('Active building warnings').getByText('Fictional preserved report', { exact: false }).waitFor()
      await page.getByRole('button', { name: 'Try reports again' }).waitFor()
      assert.equal(await page.getByText('No reports have been submitted.', { exact: true }).count(), 0)
      if (attempt === 0) await page.reload()
    }
    await page.getByRole('button', { name: 'Try reports again' }).click()
    await page.getByRole('button', { name: 'Try reports again' }).waitFor()
    await page.getByRole('heading', { name: 'Access features' }).waitFor()
    await page.locator('summary').filter({ hasText: 'Filter by access features' }).click()
    await page.locator('input[type=checkbox][value=step_free_entrance]').check()
    await page.getByText('0 building(s) found', { exact: true }).waitFor()
    await page.getByRole('button', { name: 'Clear filters' }).click()
    await page.getByRole('button', { name: /Fictional integration building/ }).waitFor()
    assert.deepEqual(errors, [], 'No browser runtime exceptions')
    await page.screenshot({ path: process.argv[5], fullPage: true })
    console.log('Browser checks passed: SQL-backed list/details, warnings despite reports 503, retry, refresh persistence and unknown-facility filtering.')
    console.log(`Screenshot: ${process.argv[5]}`)
  } finally {
    await browser.close()
  }
}
main().catch(error => { console.error(error); process.exitCode = 1 })
