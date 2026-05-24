import { useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { SignInPage } from '@/components/ui/sign-in'
import { useAuth } from '@/contexts/AuthContext'
import '@/styles/tailwind.css'

const HERO_IMAGE =
  'https://images.unsplash.com/photo-1451187580459-43490279c0fa?auto=format&fit=crop&w=2160&q=80'

export default function Login() {
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const { login } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const from = (location.state as { from?: string } | null)?.from ?? '/'

  const handleSignIn = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setError('')
    setLoading(true)

    const formData = new FormData(event.currentTarget)
    const email = String(formData.get('email') ?? '').trim()
    const password = String(formData.get('password') ?? '')

    try {
      await login(email, password)
      navigate(from, { replace: true })
    } catch (err: unknown) {
      let errorMessage = 'Error al iniciar sessió'
      const axiosErr = err as {
        response?: { data?: { detail?: unknown } }
        message?: string
      }
      const detail = axiosErr.response?.data?.detail
      if (typeof detail === 'string') {
        errorMessage = detail
      } else if (Array.isArray(detail)) {
        errorMessage = detail
          .map((d: { msg?: string; message?: string }) => d.msg || d.message || JSON.stringify(d))
          .join(', ')
      } else if (detail) {
        errorMessage = JSON.stringify(detail)
      } else if (axiosErr.message) {
        errorMessage = axiosErr.message
      }
      setError(errorMessage)
    } finally {
      setLoading(false)
    }
  }

  return (
    <SignInPage
      title={
        <>
          <span className="font-serif font-bold">Benvingut</span>
          <span className="font-light"> de nou</span>
        </>
      }
      description="Accedeix a la plataforma d'intel·ligència OSINT i continua el teu anàlisi prospectiu."
      heroImageSrc={HERO_IMAGE}
      heroTitle="Intelligence Unit"
      heroSubtitle="Recollida OSINT, anàlisi geopolítica i escenaris prospectius en un sol entorn."
      error={error}
      loading={loading}
      emailLabel="Correu electrònic"
      passwordLabel="Contrasenya"
      rememberLabel="Mantenir la sessió"
      resetPasswordLabel="Recuperar contrasenya"
      submitLabel="Iniciar sessió"
      googleLabel="Continuar amb Google"
      showGoogle={false}
      showCreateAccount={false}
      onSignIn={handleSignIn}
      onResetPassword={() =>
        setError("Contacta amb l'administrador per restablir la contrasenya.")
      }
    />
  )
}
