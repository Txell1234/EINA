import { createContext, useContext, useState, type ReactNode } from 'react'

export interface ActiveCase {
  id: number
  name: string
  type: string
  status: string
  osint_count?: number
  extraction_count?: number
}

interface CaseContextType {
  activeCase: ActiveCase | null
  setActiveCase: (c: ActiveCase | null) => void
}

const CaseContext = createContext<CaseContextType>({
  activeCase: null,
  setActiveCase: () => {},
})

export function CaseProvider({ children }: { children: ReactNode }) {
  const [activeCase, setActiveCase] = useState<ActiveCase | null>(null)
  return (
    <CaseContext.Provider value={{ activeCase, setActiveCase }}>
      {children}
    </CaseContext.Provider>
  )
}

export const useCase = () => useContext(CaseContext)
