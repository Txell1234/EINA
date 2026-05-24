const AUTH_LOGOUT_EVENT = 'auth:session-expired'

export function notifySessionExpired() {
  localStorage.removeItem('token')
  localStorage.removeItem('user')
  window.dispatchEvent(new Event(AUTH_LOGOUT_EVENT))
}

export { AUTH_LOGOUT_EVENT }
