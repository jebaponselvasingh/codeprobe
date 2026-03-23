import { test, expect } from '@playwright/test'

test.describe('Upload Flow', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('http://localhost:5173')
  })

  test('shows upload page by default', async ({ page }) => {
    await expect(page.getByText('New Code Review')).toBeVisible()
  })

  test('shows profile selector', async ({ page }) => {
    await expect(page.locator('select')).toBeVisible()
  })

  test('start button disabled without file', async ({ page }) => {
    const button = page.getByRole('button', { name: /start code review/i })
    await expect(button).toBeDisabled()
  })

  test('can navigate to batch page', async ({ page }) => {
    await page.getByTitle('Batch Review').click()
    await expect(page.getByText('Batch Review')).toBeVisible()
  })

  test('can navigate to history page', async ({ page }) => {
    await page.getByTitle('History').click()
    await expect(page.getByText('Review History')).toBeVisible()
  })

  test('can navigate to profiles page', async ({ page }) => {
    await page.getByTitle('Profiles').click()
    await expect(page.getByText('Review Profiles')).toBeVisible()
  })
})

test.describe('Theme Toggle', () => {
  test('can toggle between dark and light themes', async ({ page }) => {
    await page.goto('http://localhost:5173')
    const html = page.locator('html')
    const initialTheme = await html.getAttribute('data-theme')

    await page.getByRole('button', { name: /theme/i }).click()
    const newTheme = await html.getAttribute('data-theme')
    expect(newTheme).not.toBe(initialTheme)
  })
})
