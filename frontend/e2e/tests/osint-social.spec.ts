import { test, expect } from '@playwright/test'
import { authenticatePage, MOCK_CASE } from '../fixtures/auth'

test.describe('OSINT social EnsembleData', () => {
  test.beforeEach(async ({ page }) => {
    await authenticatePage(page)
    await page.addInitScript((c) => {
      sessionStorage.setItem('eina_active_case', JSON.stringify(c))
    }, MOCK_CASE)
  })

  test('categoria xarxes socials i recollida TikTok keyword', async ({ page }) => {
    await page.goto('/osint-collection')
    await expect(page.locator('.osint-layout')).toBeVisible({ timeout: 20_000 })

    const caseSelect = page.locator('.osint-case-selector select.osint-select')
    await expect(caseSelect.locator(`option[value="${MOCK_CASE.id}"]`)).toBeAttached({
      timeout: 15_000,
    })
    await caseSelect.selectOption(String(MOCK_CASE.id))

    await page.getByRole('button', { name: /Xarxes socials/i }).click()
    await page
      .locator('.osint-source-list .osint-source-btn')
      .filter({ hasText: 'TikTok (paraula clau)' })
      .click()

    await page.locator('#field-keyword').fill('Hormuz blockade')
    const collectPromise = page.waitForResponse(
      (r) => r.url().includes('/api/osint/collect') && r.request().method() === 'POST',
    )
    await page.getByRole('button', { name: /Cercar amb/i }).click()
    const response = await collectPromise
    expect(response.ok()).toBeTruthy()

    await expect(page.locator('.osint-result-card, .osint-alert--info').first()).toBeVisible({
      timeout: 15_000,
    })
  })
})
