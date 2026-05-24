import React, { useState } from 'react'
import { Eye, EyeOff } from 'lucide-react'

const GoogleIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" viewBox="0 0 48 48" aria-hidden>
    <path
      fill="#FFC107"
      d="M43.611 20.083H42V20H24v8h11.303c-1.649 4.657-6.08 8-11.303 8-6.627 0-12-5.373-12-12s12-5.373 12-12c3.059 0 5.842 1.154 7.961 3.039l5.657-5.657C34.046 6.053 29.268 4 24 4 12.955 4 4 12.955 4 24s8.955 20 20 20 20-8.955 20-20c0-2.641-.21-5.236-.611-7.743z"
    />
    <path
      fill="#FF3D00"
      d="M6.306 14.691l6.571 4.819C14.655 15.108 18.961 12 24 12c3.059 0 5.842 1.154 7.961 3.039l5.657-5.657C34.046 6.053 29.268 4 24 4 16.318 4 9.656 8.337 6.306 14.691z"
    />
    <path
      fill="#4CAF50"
      d="M24 44c5.166 0 9.86-1.977 13.409-5.192l-6.19-5.238C29.211 35.091 26.715 36 24 36c-5.202 0-9.619-3.317-11.283-7.946l-6.522 5.025C9.505 39.556 16.227 44 24 44z"
    />
    <path
      fill="#1976D2"
      d="M43.611 20.083H42V20H24v8h11.303c-.792 2.237-2.231 4.166-4.087 5.571l6.19 5.238C42.022 35.026 44 30.038 44 24c0-2.641-.21-5.236-.611-7.743z"
    />
  </svg>
)

interface SignInPageProps {
  title?: React.ReactNode
  description?: React.ReactNode
  heroImageSrc?: string
  heroTitle?: string
  heroSubtitle?: string
  error?: string | null
  loading?: boolean
  submitLabel?: string
  emailLabel?: string
  passwordLabel?: string
  rememberLabel?: string
  resetPasswordLabel?: string
  googleLabel?: string
  createAccountLabel?: string
  createAccountPrompt?: string
  showGoogle?: boolean
  showCreateAccount?: boolean
  onSignIn?: (event: React.FormEvent<HTMLFormElement>) => void
  onGoogleSignIn?: () => void
  onResetPassword?: () => void
  onCreateAccount?: () => void
}

const GlassInputWrapper = ({ children }: { children: React.ReactNode }) => (
  <div className="rounded-2xl border border-border bg-foreground/5 backdrop-blur-sm transition-colors focus-within:border-violet-400/70 focus-within:bg-violet-500/10">
    {children}
  </div>
)

export const SignInPage: React.FC<SignInPageProps> = ({
  title = <span className="font-light text-foreground tracking-tighter">Welcome</span>,
  description = 'Access your account and continue your journey with us',
  heroImageSrc,
  heroTitle = 'Intelligence Unit',
  heroSubtitle = 'OSINT · Anàlisi prospectiva · Intel·ligència geopolítica',
  error,
  loading = false,
  submitLabel = 'Sign In',
  emailLabel = 'Email Address',
  passwordLabel = 'Password',
  rememberLabel = 'Keep me signed in',
  resetPasswordLabel = 'Reset password',
  googleLabel = 'Continue with Google',
  createAccountLabel = 'Create Account',
  createAccountPrompt = 'New to our platform?',
  showGoogle = true,
  showCreateAccount = false,
  onSignIn,
  onGoogleSignIn,
  onResetPassword,
  onCreateAccount,
}) => {
  const [showPassword, setShowPassword] = useState(false)

  return (
    <div className="sign-in-page h-[100dvh] flex flex-col md:flex-row font-geist w-[100dvw] bg-background text-foreground">
      <section className="flex-1 flex items-center justify-center p-8 md:p-12">
        <div className="w-full max-w-md">
          <div className="flex flex-col gap-6">
            <div className="animate-element animate-delay-100">
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[var(--color-accent)] mb-2">
                EINA
              </p>
              <h1 className="text-4xl md:text-5xl font-semibold leading-tight">{title}</h1>
            </div>
            <p className="animate-element animate-delay-200 text-muted-foreground">{description}</p>

            {error ? (
              <div
                className="animate-element animate-delay-250 rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700"
                role="alert"
              >
                {error}
              </div>
            ) : null}

            <form className="space-y-5" onSubmit={onSignIn}>
              <div className="animate-element animate-delay-300">
                <label htmlFor="signin-email" className="text-sm font-medium text-muted-foreground">
                  {emailLabel}
                </label>
                <GlassInputWrapper>
                  <input
                    id="signin-email"
                    name="email"
                    type="email"
                    autoComplete="email"
                    placeholder="admin@osint.local"
                    defaultValue="admin@osint.local"
                    required
                    disabled={loading}
                    className="w-full bg-transparent text-sm p-4 rounded-2xl focus:outline-none disabled:opacity-60"
                  />
                </GlassInputWrapper>
              </div>

              <div className="animate-element animate-delay-400">
                <label htmlFor="signin-password" className="text-sm font-medium text-muted-foreground">
                  {passwordLabel}
                </label>
                <GlassInputWrapper>
                  <div className="relative">
                    <input
                      id="signin-password"
                      name="password"
                      type={showPassword ? 'text' : 'password'}
                      autoComplete="current-password"
                      placeholder="admin123"
                      defaultValue={import.meta.env.DEV ? 'admin123' : undefined}
                      required
                      disabled={loading}
                      className="w-full bg-transparent text-sm p-4 pr-12 rounded-2xl focus:outline-none disabled:opacity-60"
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword(!showPassword)}
                      className="absolute inset-y-0 right-3 flex items-center"
                      aria-label={showPassword ? 'Amagar contrasenya' : 'Mostrar contrasenya'}
                    >
                      {showPassword ? (
                        <EyeOff className="w-5 h-5 text-muted-foreground hover:text-foreground transition-colors" />
                      ) : (
                        <Eye className="w-5 h-5 text-muted-foreground hover:text-foreground transition-colors" />
                      )}
                    </button>
                  </div>
                </GlassInputWrapper>
              </div>

              <div className="animate-element animate-delay-500 flex items-center justify-between text-sm gap-4">
                <label className="flex items-center gap-3 cursor-pointer">
                  <input type="checkbox" name="rememberMe" className="custom-checkbox" disabled={loading} />
                  <span className="text-foreground/90">{rememberLabel}</span>
                </label>
                {onResetPassword ? (
                  <button
                    type="button"
                    onClick={onResetPassword}
                    className="hover:underline text-violet-400 transition-colors shrink-0"
                  >
                    {resetPasswordLabel}
                  </button>
                ) : null}
              </div>

              <button
                type="submit"
                disabled={loading}
                className="animate-element animate-delay-600 w-full rounded-2xl bg-primary py-4 font-medium text-primary-foreground hover:bg-primary/90 transition-colors disabled:opacity-70 disabled:cursor-not-allowed"
              >
                {loading ? 'Carregant…' : submitLabel}
              </button>
            </form>

            {showGoogle ? (
              <>
                <div className="animate-element animate-delay-700 relative flex items-center justify-center">
                  <span className="w-full border-t border-border" />
                  <span className="px-4 text-sm text-muted-foreground bg-background absolute">Or continue with</span>
                </div>

                <button
                  type="button"
                  onClick={onGoogleSignIn}
                  disabled={loading}
                  className="animate-element animate-delay-800 w-full flex items-center justify-center gap-3 border border-border rounded-2xl py-4 hover:bg-secondary transition-colors disabled:opacity-60"
                >
                  <GoogleIcon />
                  {googleLabel}
                </button>
              </>
            ) : null}

            {showCreateAccount && onCreateAccount ? (
              <p className="animate-element animate-delay-900 text-center text-sm text-muted-foreground">
                {createAccountPrompt}{' '}
                <button
                  type="button"
                  onClick={onCreateAccount}
                  className="text-violet-400 hover:underline transition-colors"
                >
                  {createAccountLabel}
                </button>
              </p>
            ) : null}
          </div>
        </div>
      </section>

      {heroImageSrc ? (
        <section className="hidden md:block flex-1 relative p-4 bg-[#0a1525]">
          <div
            className="animate-slide-right animate-delay-300 absolute inset-4 rounded-3xl bg-cover bg-center overflow-hidden"
            style={{ backgroundImage: `url(${heroImageSrc})` }}
          >
            <div className="absolute inset-0 bg-gradient-to-t from-[#0a1525] via-[#0a1525]/40 to-transparent" />
            <div className="absolute bottom-10 left-10 right-10 text-white">
              <p className="text-xs font-semibold uppercase tracking-[0.2em] text-[var(--color-accent)] mb-2">
                {heroTitle}
              </p>
              <p className="font-serif text-2xl font-bold leading-snug max-w-md">{heroSubtitle}</p>
            </div>
          </div>
        </section>
      ) : null}
    </div>
  )
}

export default SignInPage
