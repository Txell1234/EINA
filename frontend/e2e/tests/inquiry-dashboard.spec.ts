import { test, expect } from '@playwright/test'
import { setupE2ePage, InquiryDashboardPage } from '../pages/inquiry.pages'

test.describe('Inquiry dashboard', () => {
  test.beforeEach(async ({ page }) => {
    await setupE2ePage(page)
  })

  test('carrega estadístiques i taula global', async ({ page }) => {
    const dashboard = new InquiryDashboardPage(page)
    await dashboard.goto()

    await expect(dashboard.root).toBeVisible()
    await expect(dashboard.heading).toBeVisible()
    await expect(page.getByText('Total: 1')).toBeVisible()
    await expect(page.getByText('#42')).toBeVisible()
    await expect(page.getByText('Hormuz E2E')).toBeVisible()
  })

  test('filtra per estat completed', async ({ page }) => {
    const dashboard = new InquiryDashboardPage(page)
    await dashboard.goto()

    await page.locator('.inquiry-dashboard__filters select').selectOption('completed')
    await expect(page.locator('.inquiry-dashboard__table tbody tr').first()).toBeVisible()
    await expect(page.locator('.inquiry-dashboard__table').getByText('completed')).toBeVisible()
  })
})
