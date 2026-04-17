import { test, expect } from '@playwright/test'

/**
 * Browser-level E2E tests for Meridian Training Operations System.
 *
 * These tests exercise real FE ↔ BE flows through a browser,
 * validating that the full stack works end-to-end.
 *
 * Requires: `docker-compose up --build -d` (full stack running)
 */

test.describe('Authentication E2E', () => {
  test('login page renders', async ({ page }) => {
    await page.goto('/login')
    await expect(page.locator('form')).toBeVisible()
  })

  test('admin can log in and see dashboard', async ({ page }) => {
    await page.goto('/login')
    await page.fill('input[name="username"], input[type="text"]', 'admin')
    await page.fill('input[type="password"]', 'Admin@Meridian1')
    await page.click('button[type="submit"]')

    // Should redirect to admin dashboard
    await page.waitForURL('**/admin/dashboard', { timeout: 10_000 })
    await expect(page).toHaveURL(/\/admin\/dashboard/)
  })

  test('learner can log in and browse sessions', async ({ page }) => {
    await page.goto('/login')
    await page.fill('input[name="username"], input[type="text"]', 'learner')
    await page.fill('input[type="password"]', 'Learner@Meridian1')
    await page.click('button[type="submit"]')

    await page.waitForURL('**/learner/dashboard', { timeout: 10_000 })
    await expect(page).toHaveURL(/\/learner\/dashboard/)
  })

  test('invalid credentials show error', async ({ page }) => {
    await page.goto('/login')
    await page.fill('input[name="username"], input[type="text"]', 'admin')
    await page.fill('input[type="password"]', 'WrongPassword@123')
    await page.click('button[type="submit"]')

    // Should stay on login and show error
    await expect(page.locator('[role="alert"], .text-red-500, .error')).toBeVisible({ timeout: 5_000 })
  })

  test('403 page renders for forbidden routes', async ({ page }) => {
    await page.goto('/403')
    const text = await page.textContent('body')
    expect(text).toContain('403')
  })

  test('404 page renders for unknown routes', async ({ page }) => {
    await page.goto('/this-route-does-not-exist')
    const text = await page.textContent('body')
    expect(text).toContain('404')
  })
})
