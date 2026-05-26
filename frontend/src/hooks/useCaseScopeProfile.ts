import { useQuery } from '@tanstack/react-query'
import { casesService } from '../services/api'
import type { CaseScopeProfile } from '../types/analysisScope'

export function useCaseScopeProfile(caseId: number | null) {
  return useQuery<CaseScopeProfile>({
    queryKey: ['case-scope-profile', 'v2', caseId],
    queryFn: () => casesService.getScopeProfile(caseId!),
    enabled: caseId !== null,
    staleTime: 0,
    refetchOnMount: 'always',
  })
}
