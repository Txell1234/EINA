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
    await expect(page.getByText('#42')).toBeVisible()
    await expect(page.getByRole('link', { name: 'Hormuz E2E' })).toBeVisible()
  })

  test('filtra per estat completed', async ({ page }) => {
    const dashboard = new InquiryDashboardPage(page)
    await dashboard.goto()

    await page.locator('.inquiry-dashboard__filters select').first().selectOption('completed')
    await expect(page.locator('.inquiry-dashboard__table tbody tr').first()).toBeVisible()
    await expect(page.locator('.inquiry-dashboard__table').getByText('completed')).toBeVisible()
  })

  test('cerca per text de pregunta', async ({ page }) => {
    const dashboard = new InquiryDashboardPage(page)
    await dashboard.goto()

    await dashboard.searchInput.fill('Hormuz')
    await expect(page.locator('.inquiry-dashboard__table tbody tr')).toHaveCount(1)

    await dashboard.searchInput.fill('inexistent xyz')
    await expect(page.locator('.inquiry-dashboard__empty')).toBeVisible()
  })

  test('batch schedule amb interval seleccionat', async ({ page }) => {
    const dashboard = new InquiryDashboardPage(page)
    await dashboard.goto()

    await dashboard.rowCheckbox(0).check()
    await dashboard.scheduleInterval.selectOption('48')
    const responsePromise = page.waitForResponse(
      (r) => r.url().includes('/batch-schedule') && r.request().method() === 'PATCH',
    )
    await dashboard.scheduleEnableButton.click()
    const response = await responsePromise
    const body = await response.json()
    expect(body.ok_count).toBe(1)
    expect(body.interval_hours).toBe(48)
    await expect(page.getByTestId('inquiry-dashboard-batch-result')).toBeVisible()
  })
})
