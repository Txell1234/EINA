import React from 'react'
import ReactDOM from 'react-dom/client'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import App from './App'
import './index.css'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: true, // Refrescar quan la finestra recupera el focus
      refetchOnMount: true, // Refrescar quan el component es munta
      staleTime: 0, // Les dades són immediatament "stale" per forçar refresc
      retry: 1, // Reintentar 1 vegada en cas d'error
    },
  },
})

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <App />
    </QueryClientProvider>
  </React.StrictMode>,
)


