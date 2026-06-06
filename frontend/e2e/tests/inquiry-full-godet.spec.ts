import { test, expect } from '@playwright/test'
import { SAMPLE_QUESTION } from '../fixtures/auth'
import { setupE2ePage, IntelligenceInquiryPage } from '../pages/inquiry.pages'

test.describe('Inquiry full mode', () => {
  test.beforeEach(async ({ page }) => {
    await setupE2ePage(page, { inquiryMode: 'full' })
  })

  test('mode full pausa a awaiting_godet', async ({ page }) => {
    const inquiry = new IntelligenceInquiryPage(page)
    await inquiry.goto()
    await inquiry.fillQuestion(SAMPLE_QUESTION)
    await inquiry.mode.selectOption('full')
    await inquiry.launch.click()

    await expect(inquiry.steps.getByText('morph_bootstrap')).toBeVisible({ timeout: 20_000 })
    await expect(inquiry.awaitingGodet).toBeVisible()
    await expect(page.getByText('Completa Godet al wizard')).toBeVisible()
  })
})
