import { test, expect } from '@playwright/test'
import { setupE2ePage, InquiryDashboardPage } from '../pages/inquiry.pages'

test.describe('Inquiry export', () => {
  test.beforeEach(async ({ page }) => {
    await setupE2ePage(page)
  })

  test('export batch ZIP des del dashboard', async ({ page }) => {
    const dashboard = new InquiryDashboardPage(page)
    await dashboard.goto()

    await dashboard.rowCheckbox(0).check()
    await expect(dashboard.exportButton).toBeEnabled()

    const downloadPromise = page.waitForEvent('download')
    await dashboard.exportButton.click()
    const download = await downloadPromise

    expect(download.suggestedFilename()).toMatch(/\.zip$/i)
  })
})
