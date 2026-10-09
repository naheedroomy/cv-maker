// Import and call with a Playwright Page, or pass without `export default` to browser_run_code.
// Requires the frontend dev server. Providers and long model variants are synthetic fixtures.
export default async (page, baseURL = 'http://127.0.0.1:5173') => {
  const context = await page.context().browser().newContext({ reducedMotion: 'reduce' })
  const modelId = 'provider/long-model-variant-with-version-' + 'long-name-'.repeat(15)
  await context.addInitScript(() => {
    localStorage.setItem('jwt', 'header.eyJleHAiOjQxMDI0NDQ4MDB9.signature')
    localStorage.setItem('theme', 'dark')
  })
  const p = await context.newPage()
  await p.route('**/api/**', route => {
    const path = new URL(route.request().url()).pathname
    let data = []
    if (path === '/api/config') {
      data = { gemini_available: true, claude_api_available: true, openai_available: true,
        gemini_web_available: true }
    } else if (path === '/api/settings') {
      data = { gemini_model: modelId, claude_api_model: modelId, openai_model: modelId,
        gemini_web_model: modelId }
    } else if (path === '/api/settings/models') {
      data = { models: [{ id: modelId, label: 'Long model variant ' + modelId }] }
    }
    return route.fulfill({ contentType: 'application/json', body: JSON.stringify(data) })
  })
  try {
    await p.goto(baseURL)
    await p.getByRole('heading', { name: 'Create a CV', exact: true }).waitFor()
    let checks = 0
    for (const width of [1280, 390, 320]) {
      await p.setViewportSize({ width, height: 900 })
      for (const theme of ['light', 'dark']) {
        await p.evaluate(value => { document.documentElement.dataset.theme = value }, theme)
        for (const provider of ['Claude API', 'Gemini', 'OpenAI', 'Gemini Web']) {
          await p.locator('.model-selector').getByRole('button', { name: provider, exact: true }).click()
          const variant = p.locator('.detail-select').first()
          await variant.locator('option').filter({ hasText: 'Long model variant' }).waitFor({ state: 'attached' })
          await variant.selectOption(modelId)
          const fits = await p.evaluate(() =>
            document.documentElement.scrollWidth <= innerWidth &&
            [...document.querySelectorAll('.detail-select')].every(element =>
              element.getBoundingClientRect().width <= element.parentElement.getBoundingClientRect().width + .5))
          if (!fits) throw new Error(`Overflow: ${provider}, ${theme}, ${width}px`)
          if (await variant.inputValue() !== modelId) throw new Error('Model ID changed')
          if (await variant.getAttribute('title') !== modelId) throw new Error('Full model ID unavailable')
          checks++
        }
      }
    }
    const icon = await p.locator('link[rel="icon"]').getAttribute('href')
    if (icon !== '/favicon.svg') throw new Error('Wrong tab icon')
    const response = await p.request.get(baseURL + icon)
    if (!response.ok()) throw new Error('Tab icon unavailable')
    return { checks, allContained: true }
  } finally {
    await context.close()
  }
}
