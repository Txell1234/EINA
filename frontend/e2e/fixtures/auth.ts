/** Fake JWT for E2E — valid exp, no signature verification on frontend. */
export function makeFakeJwt(expiresInSeconds = 86400 * 365): string {
  const header = Buffer.from(JSON.stringify({ alg: 'HS256', typ: 'JWT' })).toString('base64url')
  const payload = Buffer.from(
    JSON.stringify({
      sub: 'e2e-user',
      exp: Math.floor(Date.now() / 1000) + expiresInSeconds,
    }),
  ).toString('base64url')
  return `${header}.${payload}.e2e-signature`
}

export const SAMPLE_QUESTION =
  'Trump announces US blockade of Hormuz lifted by December 2026?'

export const MOCK_CASE = {
  id: 1,
  name: 'Hormuz E2E',
  description: 'Cas de prova E2E',
  case_type: 'geopolitical',
  status: 'active',
  created_at: '2026-01-01T00:00:00Z',
}

export const MOCK_INQUIRY_ID = 42

export async function authenticatePage(page: import('@playwright/test').Page) {
  await page.addInitScript((token) => {
    localStorage.setItem('token', token)
  }, makeFakeJwt())
}
