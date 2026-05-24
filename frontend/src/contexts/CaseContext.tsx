import { createContext, useContext, useState, type ReactNode } from 'react'

export interface ActiveCase {
  id: number
  name: string
  case_type: string
  status: string
  description?: string
  osint_count?: number
  extraction_count?: number
  has_micmac?: boolean
  has_mactor?: boolean
  has_scenarios?: boolean
}

interface CaseContextType {
  activeCase: ActiveCase | null
  setActiveCase: (c: ActiveCase | null) => void
  clearActiveCase: () => void
}

const STORAGE_KEY = 'eina_active_case'

const CaseContext = createContext<CaseContextType>({
  activeCase: null,
  setActiveCase: () => {},
  clearActiveCase: () => {},
})

function readStoredCase(): ActiveCase | null {
  try {
    const saved = sessionStorage.getItem(STORAGE_KEY)
    return saved ? (JSON.parse(saved) as ActiveCase) : null
  } catch {
    return null
  }
}

export function CaseProvider({ children }: { children: ReactNode }) {
  const [activeCase, setActiveCaseState] = useState<ActiveCase | null>(readStoredCase)

  const setActiveCase = (c: ActiveCase | null) => {
    setActiveCaseState(c)
    if (c) {
      sessionStorage.setItem(STORAGE_KEY, JSON.stringify(c))
    } else {
      sessionStorage.removeItem(STORAGE_KEY)
    }
  }

  return (
    <CaseContext.Provider
      value={{
        activeCase,
        setActiveCase,
        clearActiveCase: () => setActiveCase(null),
      }}
    >
      {children}
    </CaseContext.Provider>
  )
}

export const useCase = () => useContext(CaseContext)
