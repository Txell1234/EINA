import { test, expect } from '@playwright/test'
import { setupE2ePage, MorphExplorerPage } from '../pages/inquiry.pages'

test.describe('MorphBox explorer', () => {
  test.beforeEach(async ({ page }) => {
    await setupE2ePage(page)
  })

  test('mostra explorador de combinacions vàlides i filtre live', async ({ page }) => {
    const morph = new MorphExplorerPage(page)
    await morph.goto(7, 42)

    await expect(morph.explorer).toBeVisible()
    await expect(morph.validCount).toBeVisible()
    await expect(morph.validCount).not.toHaveText('0')

    await morph.filter.fill('C1:Opció A')
    await expect(morph.explorer.locator('.morph-explorer__item').first()).toBeVisible()
  })

  test('toggle incompatibilitat redueix combinacions vàlides', async ({ page }) => {
    const morph = new MorphExplorerPage(page)
    await morph.goto(7)

    const before = await morph.validCount.textContent()
    const checkbox = page.locator('.morph-compat-table input[type="checkbox"]').first()
    await checkbox.uncheck()
    await expect(morph.validCount).not.toHaveText(before || '')
  })
})
