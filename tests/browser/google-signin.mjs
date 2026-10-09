// Pass this file's contents (without `export default`) as `code` to
// Playwright's browser_run_code tool, or import and call with a Playwright Page.
// Requires the frontend dev server. Google SDK and API traffic are mocked; no credentials needed.
export default async (page, baseURL = 'http://127.0.0.1:5173') => {
  const assert = {equal(actual, expected) {
    if (actual !== expected) throw new Error(`Expected ${expected}, got ${actual}`)
  }}
  const browser = page.context().browser()
  const sdk = `window.google = { accounts: { id: {
    initialize(config) { window.googleCallback = config.callback },
    renderButton(element) {
      const button = document.createElement('button');
      button.textContent = 'Mock Google sign-in';
      button.onclick = () => window.googleCallback({credential: 'mock-credential'});
      element.appendChild(button);
    }
  } } };`
  const cases = []
  for (const scenario of ['delayed SDK', 'failed SDK', 'timed out SDK', 'failed config', 'cached SDK']) {
    const context = await browser.newContext()
    try {
      const p = await context.newPage()
      if (scenario === 'timed out SDK') {
        await p.addInitScript(() => {
          const original = window.setTimeout
          window.setTimeout = (fn, delay, ...args) =>
            original(fn, delay === 15000 ? 100 : delay, ...args)
        })
      }
      let sdkRequests = 0
      let configRequests = 0
      let releaseSDK
      const gate = new Promise(resolve => { releaseSDK = resolve })
      const jwt = 'header.eyJleHAiOjQxMDI0NDQ4MDB9.signature' // Mock token expires in 2100.
      await p.route('**/api/**', async route => {
        const path = new URL(route.request().url()).pathname
        let body = {}
        let status = 200
        if (path === '/api/config') {
          configRequests++
          status = scenario === 'failed config' && configRequests === 1 ? 503 : 200
          body = {google_client_id: 'test-client'}
        } else if (path === '/api/auth') {
          assert.equal(route.request().postDataJSON().id_token, 'mock-credential')
          body = {jwt, user: {id: 1, email: 'test@example.com', name: 'Test', picture: ''}}
        } else if (path === '/api/jobs') body = []
        await route.fulfill({status, contentType: 'application/json', body: JSON.stringify(body)})
      })
      await p.route('https://accounts.google.com/gsi/client', async route => {
        sdkRequests++
        if (scenario === 'delayed SDK' || scenario === 'timed out SDK') await gate
        if (scenario === 'failed SDK' && sdkRequests === 1) await route.abort('failed')
        else await route.fulfill({contentType: 'application/javascript', body: sdk})
      })
      if (scenario === 'cached SDK') await p.addInitScript(sdk)
      await p.goto(`${baseURL}/signin`, {waitUntil: 'domcontentloaded'})
      if (scenario === 'delayed SDK') {
        await p.getByRole('status').waitFor()
        assert.equal(await p.getByRole('alert').count(), 0)
        assert.equal(await p.getByRole('button', {name: 'Mock Google sign-in'}).count(), 0)
        releaseSDK()
      } else if (scenario.startsWith('failed') || scenario === 'timed out SDK') {
        await p.getByRole('alert').waitFor()
        if (scenario === 'timed out SDK') {
          assert.equal((await p.getByRole('alert').textContent()).includes('taking too long'), true)
        }
        await p.getByRole('button', {name: 'Try again'}).click()
        // Restore the network. Retries may share the original in-flight HTTP request.
        if (scenario === 'timed out SDK') releaseSDK()
      }
      const button = p.getByRole('button', {name: 'Mock Google sign-in'})
      await button.waitFor()
      assert.equal(await p.getByRole('alert').count(), 0)
      if (scenario === 'cached SDK') assert.equal(sdkRequests, 0)
      // Exercise the actual callback and token exchange, not just script loading.
      await button.click()
      await p.waitForURL(`${baseURL}/`)
      assert.equal(await p.evaluate(() => localStorage.getItem('jwt')), jwt)
      cases.push(`${scenario}: passed`)
    } finally {
      await context.close()
    }
  }
  return cases
}
