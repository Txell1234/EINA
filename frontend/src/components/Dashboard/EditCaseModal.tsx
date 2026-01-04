import { useState, useEffect } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { casesService } from '../../services/api'
import './CreateCaseModal.css'

interface EditCaseModalProps {
  caseId: number
  isOpen: boolean
  onClose: () => void
  onSuccess?: () => void
}

export default function EditCaseModal({ caseId, isOpen, onClose, onSuccess }: EditCaseModalProps) {
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [caseType, setCaseType] = useState('general')
  const [error, setError] = useState<string | null>(null)
  const queryClient = useQueryClient()

  // Load case data
  const { data: caseData, isLoading } = useQuery({
    queryKey: ['case', caseId],
    queryFn: () => casesService.get(caseId),
    enabled: isOpen && !!caseId,
    onSuccess: (data) => {
      if (data) {
        setName(data.name || '')
        setDescription(data.description || '')
        setCaseType(data.case_type || 'general')
      }
    }
  })

  const updateMutation = useMutation({
    mutationFn: async (data: { name: string; description: string; case_type: string }) => {
      return casesService.update(caseId, data)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['cases'] })
      queryClient.invalidateQueries({ queryKey: ['case', caseId] })
      onClose()
      setName('')
      setDescription('')
      setCaseType('general')
      setError(null)
      if (onSuccess) onSuccess()
    },
    onError: (error: any) => {
      let errorMessage = 'Error al actualitzar el cas. Intenta-ho de nou.'
      
      if (error?.response?.data?.detail) {
        errorMessage = error.response.data.detail
      } else if (error?.message) {
        errorMessage = error.message
      }
      
      setError(errorMessage)
    },
  })

  const rerunMutation = useMutation({
    mutationFn: async () => {
      return casesService.rerun(caseId)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['cases'] })
      queryClient.invalidateQueries({ queryKey: ['case', caseId] })
      onClose()
      if (onSuccess) onSuccess()
      alert('Anàlisi rellançada. El cas està sent analitzat de nou.')
    },
    onError: (error: any) => {
      let errorMessage = 'Error al rellançar l\'anàlisi. Intenta-ho de nou.'
      
      if (error?.response?.data?.detail) {
        errorMessage = error.response.data.detail
      } else if (error?.message) {
        errorMessage = error.message
      }
      
      setError(errorMessage)
    },
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    
    if (!name.trim()) {
      setError('El nom del cas és obligatori.')
      return
    }

    updateMutation.mutate({
      name: name.trim(),
      description: description.trim(),
      case_type: caseType
    })
  }

  const handleRerun = () => {
    if (confirm('Estàs segur que vols rellançar l\'anàlisi d\'aquest cas? Això tornarà a executar totes les anàlisis.')) {
      setError(null)
      rerunMutation.mutate()
    }
  }

  const handleClose = () => {
    setName('')
    setDescription('')
    setCaseType('general')
    setError(null)
    updateMutation.reset()
    rerunMutation.reset()
    onClose()
  }

  if (!isOpen) return null

  return (
    <div className="modal-overlay" onClick={handleClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <h2>Editar Cas</h2>
        
        {isLoading ? (
          <p>Carregant dades del cas...</p>
        ) : (
          <form onSubmit={handleSubmit}>
            {error && (
              <div className="error-message" style={{
                padding: '10px',
                marginBottom: '15px',
                backgroundColor: '#fee',
                border: '1px solid #fcc',
                borderRadius: '4px',
                color: '#c33'
              }}>
                {error}
              </div>
            )}

            <div className="form-group">
              <label htmlFor="case-name">Nom del Cas:</label>
              <input
                id="case-name"
                type="text"
                value={name}
                onChange={(e) => {
                  setName(e.target.value)
                  setError(null)
                }}
                placeholder="Nom del cas"
                disabled={updateMutation.isPending}
                required
              />
            </div>

            <div className="form-group">
              <label htmlFor="case-description">Descripció:</label>
              <textarea
                id="case-description"
                value={description}
                onChange={(e) => {
                  setDescription(e.target.value)
                  setError(null)
                }}
                placeholder="Descripció del cas"
                rows={5}
                disabled={updateMutation.isPending}
              />
            </div>

            <div className="form-group">
              <label htmlFor="case-type">Tipus de Cas:</label>
              <select
                id="case-type"
                value={caseType}
                onChange={(e) => {
                  setCaseType(e.target.value)
                  setError(null)
                }}
                disabled={updateMutation.isPending}
              >
                <option value="general">General</option>
                <option value="business">Business</option>
                <option value="political">Political</option>
                <option value="geopolitical">Geopolitical</option>
                <option value="social">Social</option>
                <option value="investigation">Investigation</option>
              </select>
            </div>

            <div className="modal-actions">
              <button 
                type="button" 
                onClick={handleClose}
                disabled={updateMutation.isPending || rerunMutation.isPending}
              >
                Cancel·lar
              </button>
              <button 
                type="button"
                onClick={handleRerun}
                disabled={updateMutation.isPending || rerunMutation.isPending}
                style={{
                  backgroundColor: '#17a2b8',
                  color: 'white'
                }}
              >
                {rerunMutation.isPending ? 'Rellançant...' : '🔄 Rellançar Anàlisi'}
              </button>
              <button 
                type="submit" 
                disabled={!name.trim() || updateMutation.isPending || rerunMutation.isPending}
              >
                {updateMutation.isPending ? 'Actualitzant...' : 'Guardar Canvis'}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  )
}



