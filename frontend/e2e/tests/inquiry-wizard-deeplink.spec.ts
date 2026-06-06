import { test, expect } from '@playwright/test'
import { setupE2ePage, InquiryDashboardPage } from '../pages/inquiry.pages'

test.describe('Wizard deep link', () => {
  test.beforeEach(async ({ page }) => {
    await setupE2ePage(page)
  })

  test('navega des del dashboard al wizard morfològic amb inquiry', async ({ page }) => {
    const dashboard = new InquiryDashboardPage(page)
    await dashboard.goto()

    await dashboard.wizardLink().click()

    await expect(page).toHaveURL(/\/prospective\/morph\?project=7&inquiry=42/)
    await expect(page.getByTestId('inquiry-wizard-banner')).toBeVisible()
    await expect(page.getByText('Originat des de inquiry #42')).toBeVisible()
  })
})
