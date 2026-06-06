import { startE2eMockServer } from './mock-server'

export default async function globalSetup() {
  const stop = await startE2eMockServer()
  return async () => {
    await stop()
  }
}
