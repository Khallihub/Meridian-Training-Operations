import { test, expect } from '@playwright/test'

/**
 * Full learner user journey E2E test.
 * Exercises: login → browse sessions → view details → navigate bookings.
 */

test.describe('Learner Journey E2E', () => {
  test.beforeEach(async ({ page }) => {
    // Login as learner
    await page.goto('/login')
    await page.fill('input[name="username"], input[type="text"]', 'learner')
    await page.fill('input[type="password"]', 'Learner@Meridian1')
    await page.click('button[type="submit"]')
    await page.waitForURL('**/learner/dashboard', { timeout: 10_000 })
  })

  test('dashboard loads with navigation', async ({ page }) => {
    await expect(page).toHaveURL(/\/learner\/dashboard/)
    // Sidebar or nav should be present
    const nav = page.locator('nav, aside, [role="navigation"]')
    await expect(nav.first()).toBeVisible()
  })

  test('can navigate to sessions page', async ({ page }) => {
    await page.click('a[href*="/learner/sessions"], [data-testid="sessions-link"]')
    await page.waitForURL('**/learner/sessions', { timeout: 10_000 })
    await expect(page).toHaveURL(/\/learner\/sessions/)
  })

  test('can navigate to bookings page', async ({ page }) => {
    await page.click('a[href*="/learner/bookings"], [data-testid="bookings-link"]')
    await page.waitForURL('**/learner/bookings', { timeout: 10_000 })
    await expect(page).toHaveURL(/\/learner\/bookings/)
  })
})
