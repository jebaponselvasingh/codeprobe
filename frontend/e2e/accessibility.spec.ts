import { test, expect } from '@playwright/test'
import AxeBuilder from '@axe-core/playwright'

test.describe('Accessibility Audit', () => {
  test('upload page has no critical a11y violations', async ({ page }) => {
    await page.goto('http://localhost:5173')
    const results = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa'])
      .exclude('#monaco-editor') // Monaco has its own a11y
      .analyze()

    const critical = results.violations.filter(v => v.impact === 'critical')
    expect(critical).toHaveLength(0)
  })

  test('profiles page has no critical a11y violations', async ({ page }) => {
    await page.goto('http://localhost:5173')
    await page.getByTitle('Profiles').click()

    const results = await new AxeBuilder({ page })
      .withTags(['wcag2a'])
      .analyze()

    const critical = results.violations.filter(v => v.impact === 'critical')
    expect(critical).toHaveLength(0)
  })
})
