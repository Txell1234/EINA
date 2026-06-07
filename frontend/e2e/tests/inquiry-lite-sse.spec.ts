import { test, expect } from '@playwright/test'
import { SAMPLE_QUESTION } from '../fixtures/auth'
import { setupE2ePage, IntelligenceInquiryPage } from '../pages/inquiry.pages'

test.describe('Inquiry lite + SSE', () => {
  test.beforeEach(async ({ page }) => {
    await setupE2ePage(page, { inquiryMode: 'lite' })
  })

  test('executa inquiry lite i mostra passos SSE', async ({ page }) => {
    const inquiry = new IntelligenceInquiryPage(page)
    await inquiry.goto()
    await inquiry.fillQuestion(SAMPLE_QUESTION)
    await inquiry.mode.selectOption('lite')
    await inquiry.launch.click()

    await expect(inquiry.steps).toBeVisible({ timeout: 20_000 })
    await expect(inquiry.steps.getByText('parse')).toBeVisible()
    await expect(inquiry.steps.getByText('osint')).toBeVisible()
    await expect(inquiry.steps.locator('.step-progress__label', { hasText: 'monitors' })).toBeVisible()
    await expect(page.getByText('Blocatge parcialment')).toBeVisible()
  })

  test('resilient davant SSE fragmentat (chunks petits)', async ({ page }) => {
    await page.route(/\/api\/prospective\/inquiries\/\d+\/run/, async (route) => {
      const body =
        'data: {"event":"step","step":"parse","status":"ok"}\n\n' +
        'data: {"event":"step","step":"osint","status":"ok"}\n\n' +
        'data: {"event":"done","answer":{"conclusions":["Chunk OK"]}}\n\n'
      await route.fulfill({
        status: 200,
        headers: { 'Content-Type': 'text/event-stream' },
        body,
      })
    })

    const inquiry = new IntelligenceInquiryPage(page)
    await inquiry.goto()
    await inquiry.question.fill(SAMPLE_QUESTION)
    await inquiry.launch.click()

    await expect(inquiry.steps.getByText('parse')).toBeVisible()
    await expect(page.getByText('Chunk OK')).toBeVisible()
  })
})
