import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../../contexts/AuthContext'
import './Login.css'

export default function Login() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const { login } = useAuth()
  const navigate = useNavigate()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      await login(email, password)
      navigate('/')
    } catch (err: any) {
      let errorMessage = 'Error al iniciar sessió'
      if (err.response?.data) {
        if (typeof err.response.data.detail === 'string') {
          errorMessage = err.response.data.detail
        } else if (Array.isArray(err.response.data.detail)) {
          errorMessage = err.response.data.detail.map((d: any) => d.msg || d.message || JSON.stringify(d)).join(', ')
        } else if (err.response.data.detail) {
          errorMessage = JSON.stringify(err.response.data.detail)
        }
      } else if (err.message) {
        errorMessage = err.message
      }
      setError(errorMessage)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="login-container">
      <div className="login-box">
        <h1>OSINT Intelligence Platform</h1>
        <p>Iniciar Sessió</p>
        {error && <div className="error-message">{error}</div>}
        <form onSubmit={handleSubmit}>
          <input
            type="email"
            placeholder="Email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />
          <input
            type="password"
            placeholder="Contrasenya"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />
          <button type="submit" disabled={loading}>
            {loading ? 'Carregant...' : 'Iniciar Sessió'}
          </button>
        </form>
      </div>
    </div>
  )
}

