const { chromium } = require('playwright')

;(async () => {
  const browser = await chromium.launch({ headless: true })
  console.log('ok')
  await browser.close()
})().catch((error) => {
  console.error(error)
  process.exit(1)
})
