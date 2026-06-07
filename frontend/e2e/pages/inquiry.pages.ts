import type { Page } from '@playwright/test'
import { expect } from '@playwright/test'
import { authenticatePage, MOCK_CASE } from '../fixtures/auth'

const MOCK_API = 'http://127.0.0.1:9321'

export class InquiryDashboardPage {
  constructor(readonly page: Page) {}

  async goto() {
    await this.page.goto('/prospective/inquiries?tab=all')
    await expect(this.root).toBeVisible({ timeout: 20_000 })
    await expect(this.page.getByText(/Total:/)).toBeVisible()
  }

  get root() {
    return this.page.getByTestId('inquiry-dashboard')
  }

  get exportButton() {
    return this.page.getByTestId('inquiry-dashboard-export')
  }

  get scheduleEnableButton() {
    return this.page.getByTestId('inquiry-dashboard-schedule-enable')
  }

  get scheduleInterval() {
    return this.page.getByTestId('inquiry-dashboard-schedule-interval')
  }

  get executiveButton() {
    return this.page.getByTestId('inquiry-dashboard-executive')
  }

  get searchInput() {
    return this.page.getByTestId('inquiry-dashboard-search')
  }

  get heading() {
    return this.page.getByTestId('inquiry-dashboard-heading')
  }

  rowCheckbox(index = 0) {
    return this.page.locator('.inquiry-dashboard__table tbody input[type="checkbox"]').nth(index)
  }

  wizardLink() {
    return this.page.getByRole('link', { name: 'Wizard' })
  }
}

export class MorphExplorerPage {
  constructor(readonly page: Page) {}

  async goto(projectId = 7, inquiryId?: number) {
    const qs = new URLSearchParams({ project: String(projectId) })
    if (inquiryId) qs.set('inquiry', String(inquiryId))
    await this.page.goto(`/prospective/morph?${qs.toString()}`)
    await expect(this.page.getByTestId('morph-box')).toBeVisible({ timeout: 20_000 })
  }

  get explorer() {
    return this.page.getByTestId('morph-explorer')
  }

  get filter() {
    return this.page.getByTestId('morph-explorer-filter')
  }

  get validCount() {
    return this.page.getByTestId('morph-explorer-valid-count')
  }
}

export class IntelligenceInquiryPage {
  constructor(readonly page: Page) {}

  async goto() {
    await this.page.goto('/intelligence')
    const select = this.page.locator('.intel-case-select')
    await select.waitFor({ state: 'visible' })
    await expect(select.locator(`option[value="${MOCK_CASE.id}"]`)).toBeAttached({ timeout: 20_000 })
    await Promise.all([
      this.page.waitForResponse((r) => r.url().includes('/status') && r.ok()),
      select.selectOption(String(MOCK_CASE.id)),
    ])
    await expect(this.page.getByTestId('intel-panels-ready')).toBeVisible({ timeout: 30_000 })
    await expect(this.page.getByTestId('prospective-inquiry-panel')).toBeVisible()
    await expect(this.page.getByTestId('inquiry-question')).toBeVisible()
  }

  async fillQuestion(text: string) {
    const field = this.page.getByTestId('inquiry-question')
    await expect(field).toBeVisible()
    await field.fill(text)
  }

  get panel() {
    return this.page.getByTestId('prospective-inquiry-panel')
  }

  get question() {
    return this.page.getByTestId('inquiry-question')
  }

  get mode() {
    return this.page.getByTestId('inquiry-mode')
  }

  get launch() {
    return this.page.getByTestId('inquiry-launch')
  }

  get steps() {
    return this.page.getByTestId('inquiry-steps')
  }

  get awaitingGodet() {
    return this.page.getByTestId('inquiry-awaiting-godet')
  }
}

export async function setInquiryMode(mode: 'lite' | 'full') {
  await fetch(`${MOCK_API}/__e2e/mode`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ mode }),
  })
}

export async function setupE2ePage(page: Page, options?: { inquiryMode?: 'lite' | 'full' }) {
  await authenticatePage(page)
  if (options?.inquiryMode) {
    await setInquiryMode(options.inquiryMode)
  } else {
    await setInquiryMode('lite')
  }
}
