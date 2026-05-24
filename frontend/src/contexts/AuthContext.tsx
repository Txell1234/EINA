import React, { createContext, useContext, useState, useEffect, type ReactNode } from 'react'
import { Navigate, useLocation } from 'react-router-dom'
import { authService } from '../services/api'
import { AUTH_LOGOUT_EVENT } from '../utils/authEvents'

interface AuthContextType {
  isAuthenticated: boolean
  token: string | null
  login: (email: string, password: string) => Promise<void>
  logout: () => void
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

function readStoredToken(): string | null {
  const token = localStorage.getItem('token')
  if (!token) return null
  if (isTokenExpired(token)) {
    localStorage.removeItem('token')
    localStorage.removeItem('user')
    return null
  }
  return token
}

function isTokenExpired(token: string): boolean {
  try {
    const payload = JSON.parse(atob(token.split('.')[1])) as { exp?: number }
    if (!payload.exp) return false
    return payload.exp * 1000 < Date.now()
  } catch {
    return true
  }
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [token, setToken] = useState<string | null>(() => readStoredToken())

  useEffect(() => {
    if (token) {
      localStorage.setItem('token', token)
    } else {
      localStorage.removeItem('token')
      localStorage.removeItem('user')
    }
  }, [token])

  useEffect(() => {
    const onSessionExpired = () => setToken(null)
    window.addEventListener(AUTH_LOGOUT_EVENT, onSessionExpired)
    return () => window.removeEventListener(AUTH_LOGOUT_EVENT, onSessionExpired)
  }, [])

  const login = async (email: string, password: string) => {
    const response = await authService.login(email, password)
    setToken(response.access_token)
  }

  const logout = () => {
    setToken(null)
  }

  return (
    <AuthContext.Provider
      value={{
        isAuthenticated: !!token,
        token,
        login,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}

/** Route guard — lives in the same module as AuthContext to survive Vite HMR. */
export function ProtectedRoute({ children }: { children: ReactNode }) {
  const { isAuthenticated } = useAuth()
  const location = useLocation()
  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location.pathname }} replace />
  }
  return <>{children}</>
}
