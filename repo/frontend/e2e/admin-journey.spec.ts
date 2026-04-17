import { test, expect } from '@playwright/test'

/**
 * Admin user journey E2E test.
 * Exercises: login → dashboard → sessions → users → monitoring.
 */

test.describe('Admin Journey E2E', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/login')
    await page.fill('input[name="username"], input[type="text"]', 'admin')
    await page.fill('input[type="password"]', 'Admin@Meridian1')
    await page.click('button[type="submit"]')
    await page.waitForURL('**/admin/dashboard', { timeout: 10_000 })
  })

  test('admin dashboard renders', async ({ page }) => {
    await expect(page).toHaveURL(/\/admin\/dashboard/)
  })

  test('can navigate to sessions management', async ({ page }) => {
    await page.click('a[href*="/admin/sessions"]')
    await page.waitForURL('**/admin/sessions', { timeout: 10_000 })
    await expect(page).toHaveURL(/\/admin\/sessions/)
  })

  test('can navigate to user management', async ({ page }) => {
    await page.click('a[href*="/admin/users"]')
    await page.waitForURL('**/admin/users', { timeout: 10_000 })
    await expect(page).toHaveURL(/\/admin\/users/)
  })

  test('can navigate to monitoring', async ({ page }) => {
    await page.click('a[href*="/admin/monitoring"]')
    await page.waitForURL('**/admin/monitoring', { timeout: 10_000 })
    await expect(page).toHaveURL(/\/admin\/monitoring/)
  })

  test('can view audit logs', async ({ page }) => {
    await page.click('a[href*="/admin/audit"]')
    await page.waitForURL('**/admin/audit', { timeout: 10_000 })
    await expect(page).toHaveURL(/\/admin\/audit/)
  })
})
