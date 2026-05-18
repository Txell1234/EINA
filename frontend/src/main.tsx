import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import App from './App'
import { CaseProvider } from './contexts/CaseContext'
import './index.css'

const queryClient = new QueryClient()

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <CaseProvider>
        <BrowserRouter>
          <App />
        </BrowserRouter>
      </CaseProvider>
    </QueryClientProvider>
  </StrictMode>,
)
