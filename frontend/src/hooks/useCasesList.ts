import { useQuery, type UseQueryOptions } from '@tanstack/react-query'
import { useCase, type ActiveCase } from '../contexts/CaseContext'
import { casesService } from '../services/api'

export interface CaseListItem {
  id: number
  name: string
  case_type?: string
  status?: string
  description?: string
}

/** Assegura que el cas actiu aparegui al desplegable encara que l'API no el retorni. */
export function mergeActiveCaseIntoList(
  cases: CaseListItem[] | undefined,
  activeCase: ActiveCase | null,
): CaseListItem[] {
  const list = cases ?? []
  if (!activeCase?.id) return list
  if (list.some((c) => c.id === activeCase.id)) return list
  return [
    {
      id: activeCase.id,
      name: activeCase.name,
      case_type: activeCase.case_type,
      status: activeCase.status,
      description: activeCase.description,
    },
    ...list,
  ]
}

type CasesListOptions = Omit<
  UseQueryOptions<CaseListItem[], Error, CaseListItem[], readonly unknown[]>,
  'queryKey' | 'queryFn' | 'select'
>

export function useCasesList(options?: CasesListOptions) {
  const { activeCase } = useCase()

  return useQuery({
    queryKey: ['cases-list', activeCase?.id],
    queryFn: async () => {
      const data = await casesService.list()
      return Array.isArray(data) ? data : []
    },
    staleTime: 0,
    refetchOnWindowFocus: true,
    select: (data) => mergeActiveCaseIntoList(data as CaseListItem[], activeCase),
    ...options,
  })
}
