import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { casesService, researchService } from '../../services/api'
import ResearchPlanReview from '../Research/ResearchPlanReview'
import './CreateCaseModal.css'

export default function CreateCaseModal() {
  const [isOpen, setIsOpen] = useState(false)
  const [prompt, setPrompt] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [createdCaseId, setCreatedCaseId] = useState<number | null>(null)
  const [showResearchPlan, setShowResearchPlan] = useState(false)
  const [researchPlan, setResearchPlan] = useState<any>(null)
  const queryClient = useQueryClient()

  const createMutation = useMutation({
    mutationFn: async (prompt: string) => {
      // Intentar crear el caso directamente (el error de conexión se manejará automáticamente)
      return casesService.createFromPrompt(prompt)
    },
    onSuccess: async (data) => {
      queryClient.invalidateQueries({ queryKey: ['cases'] })
      const caseId = data.id || data.case_id
      if (caseId) {
        setCreatedCaseId(caseId)
        // Generate research plan automatically (optional - don't block if it fails)
        try {
          const plan = await researchService.generatePlan(caseId)
          if (plan && plan.research_phases && plan.research_phases.length > 0) {
            setResearchPlan(plan)
            setShowResearchPlan(true)
          } else {
            // No research plan generated, just close modal
            setIsOpen(false)
            setPrompt('')
            setError(null)
          }
        } catch (err) {
          console.warn('Research plan generation failed (non-critical):', err)
          // Continue without research plan - case is already created and analysis is running
          setIsOpen(false)
          setPrompt('')
          setError(null)
        }
      } else {
      setIsOpen(false)
      setPrompt('')
      setError(null)
      }
    },
    onError: (error: any) => {
      // Logging detallado para debugging
      console.error('=== ERROR CREANDO CASO ===')
      console.error('Error completo:', error)
      console.error('Error code:', error?.code)
      console.error('Error message:', error?.message)
      console.error('Response:', error?.response)
      console.error('Response data:', error?.response?.data)
      console.error('Response status:', error?.response?.status)
      console.error('Request:', error?.request)
      console.error('Config:', error?.config)
      
      // Extraer mensaje de error según el tipo
      let errorMessage = 'Error al crear el caso. Por favor, intenta de nuevo.'
      
      if (error?.code === 'ECONNABORTED' || error?.message?.includes('timeout')) {
        errorMessage = 'Timeout: El servidor tardó demasiado en responder. Verifica que el backend esté corriendo correctamente.'
      } else if (error?.code === 'ERR_NETWORK' || error?.message?.includes('Network Error')) {
        errorMessage = 'Error de red: No se pudo conectar con el servidor. Verifica que el backend esté corriendo en http://localhost:8000'
      } else if (error?.response) {
        // Error con respuesta del servidor
        const status = error.response.status
        const detail = error.response.data?.detail
        
        if (status === 401 || status === 403) {
          errorMessage = 'Error de autenticación. Por favor, inicia sesión nuevamente.'
        } else if (status === 404) {
          errorMessage = 'Endpoint no encontrado. El servidor puede no estar actualizado.'
        } else if (status === 500) {
          errorMessage = detail || 'Error interno del servidor. Revisa los logs del backend.'
        } else if (status === 422) {
          errorMessage = detail || 'Error de validación. Verifica que el prompt no esté vacío.'
        } else {
          errorMessage = detail || `Error ${status}: ${error.response.statusText || 'Error desconocido'}`
        }
      } else if (error?.request) {
        // Petición enviada pero sin respuesta
        errorMessage = 'No se recibió respuesta del servidor. Verifica que el backend esté corriendo y accesible.'
      } else if (error?.message) {
        errorMessage = error.message
      } else if (typeof error === 'string') {
        errorMessage = error
      }
      
      setError(errorMessage)
    },
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    setError(null) // Limpiar error anterior
    if (prompt.trim()) {
      createMutation.mutate(prompt)
    } else {
      setError('Por favor, introduce un prompt válido.')
    }
  }

  const handleClose = () => {
    setIsOpen(false)
    setPrompt('')
    setError(null)
    setCreatedCaseId(null)
    setShowResearchPlan(false)
    setResearchPlan(null)
    createMutation.reset()
  }

  const handleResearchPlanApprove = () => {
    // Research plan approved, close modal
    setIsOpen(false)
    setPrompt('')
    setError(null)
    setCreatedCaseId(null)
    setShowResearchPlan(false)
    setResearchPlan(null)
  }

  return (
    <>
      <button className="btn-create-case" onClick={() => setIsOpen(true)}>
        + Crear Cas amb IA
      </button>

      {isOpen && !showResearchPlan && (
        <div className="modal-overlay" onClick={handleClose}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <h2>Crear Cas amb IA</h2>
            <p>Introdueix un prompt per crear un cas. La IA analitzarà el prompt i generarà un pla d'acció automàtic.</p>
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
              <textarea
                value={prompt}
                onChange={(e) => {
                  setPrompt(e.target.value)
                  setError(null) // Limpiar error al escribir
                }}
                placeholder="Ex: Anàlisi de comerç India-UAE amb empreses X, Y, Z"
                rows={5}
                className="prompt-input"
                disabled={createMutation.isPending}
              />
              <div className="modal-actions">
                <button 
                  type="button" 
                  onClick={handleClose}
                  disabled={createMutation.isPending}
                >
                  Cancel·lar
                </button>
                <button 
                  type="submit" 
                  disabled={!prompt.trim() || createMutation.isPending}
                >
                  {createMutation.isPending ? 'Creant...' : 'Crear Cas'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {showResearchPlan && createdCaseId && researchPlan && (
        <ResearchPlanReview
          caseId={createdCaseId}
          isOpen={showResearchPlan}
          onClose={() => {
            setShowResearchPlan(false)
            handleClose()
          }}
          onApprove={handleResearchPlanApprove}
          researchPlan={researchPlan}
        />
      )}
    </>
  )
}

