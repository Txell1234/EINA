import { createContext, useContext, useState, type ReactNode } from 'react'

export interface ActiveProject {
  id: number
  title: string
  case_id: number
}

interface ProjectContextType {
  activeProject: ActiveProject | null
  setActiveProject: (p: ActiveProject | null) => void
  clearActiveProject: () => void
}

const STORAGE_KEY = 'eina_active_project'

const ProjectContext = createContext<ProjectContextType>({
  activeProject: null,
  setActiveProject: () => {},
  clearActiveProject: () => {},
})

function readStoredProject(): ActiveProject | null {
  try {
    const saved = sessionStorage.getItem(STORAGE_KEY)
    return saved ? (JSON.parse(saved) as ActiveProject) : null
  } catch {
    return null
  }
}

export function ProjectProvider({ children }: { children: ReactNode }) {
  const [activeProject, setActiveProjectState] = useState<ActiveProject | null>(readStoredProject)

  const setActiveProject = (p: ActiveProject | null) => {
    setActiveProjectState(p)
    if (p) {
      sessionStorage.setItem(STORAGE_KEY, JSON.stringify(p))
    } else {
      sessionStorage.removeItem(STORAGE_KEY)
    }
  }

  return (
    <ProjectContext.Provider
      value={{
        activeProject,
        setActiveProject,
        clearActiveProject: () => setActiveProject(null),
      }}
    >
      {children}
    </ProjectContext.Provider>
  )
}

export const useProject = () => useContext(ProjectContext)

/** Append ?project= when an active Godet project is set. */
export function withActiveProject(path: string, projectId: number | null | undefined): string {
  if (!projectId) return path
  const sep = path.includes('?') ? '&' : '?'
  return `${path}${sep}project=${projectId}`
}

/** Godet wizard routes keyed by checklist step. */
export const GODET_STEP_ROUTES: Record<string, string> = {
  project: '/prospective/project',
  variables: '/prospective/variables',
  micmac: '/prospective/micmac',
  actors: '/prospective/actors',
  mactor: '/prospective/mactor',
  morph: '/prospective/morph',
  smic: '/prospective/morph',
  scenarios: '/prospective-analysis',
}

export const GODET_STEP_ORDER = [
  'project',
  'variables',
  'micmac',
  'actors',
  'mactor',
  'morph',
  'smic',
  'scenarios',
] as const

export function resumeGodetPath(
  checklist: Record<string, boolean>,
  projectId: number,
): string {
  for (const step of GODET_STEP_ORDER) {
    if (!checklist[step]) {
      return withActiveProject(GODET_STEP_ROUTES[step] ?? '/prospective/project', projectId)
    }
  }
  return withActiveProject('/prospective-analysis', projectId)
}
