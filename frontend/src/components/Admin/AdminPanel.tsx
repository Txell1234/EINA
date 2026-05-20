import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { adminService, casesService } from '../../services/api'
import './AdminPanel.css'

export default function AdminPanel() {
  const [activeTab, setActiveTab] = useState<
    'classifications' | 'categories' | 'feedback' | 'stats' | 'users'
  >('classifications')
  const [selectedCaseId, setSelectedCaseId] = useState<number | null>(null)
  const [selectedClassification, setSelectedClassification] = useState<number | null>(null)
  const [showCategoryModal, setShowCategoryModal] = useState(false)
  const [editingCategory, setEditingCategory] = useState<any>(null)
  const [showCreateForm, setShowCreateForm] = useState(false)
  const [newEmail, setNewEmail] = useState('')
  const [newFullName, setNewFullName] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [newIsSuperuser, setNewIsSuperuser] = useState(false)
  const [changingPasswordFor, setChangingPasswordFor] = useState<number | null>(null)
  const [newPasswordValue, setNewPasswordValue] = useState('')
  const queryClient = useQueryClient()

  // Get all cases for selector
  const { data: cases } = useQuery({
    queryKey: ['cases'],
    queryFn: () => casesService.list(),
  })

  // Classifications - filtered by case if selected
  const { data: classifications, isLoading: classificationsLoading } = useQuery({
    queryKey: ['admin-classifications', selectedCaseId],
    queryFn: () => adminService.listClassifications(selectedCaseId || undefined),
  })

  // Categories
  const { data: categories, isLoading: categoriesLoading } = useQuery({
    queryKey: ['admin-categories'],
    queryFn: () => adminService.listCategories(),
  })

  // Statistics - filtered by case if selected
  const { data: stats } = useQuery({
    queryKey: ['admin-stats', selectedCaseId],
    queryFn: () => adminService.getClassificationStats(selectedCaseId || undefined),
  })

  const { data: users = [] } = useQuery({
    queryKey: ['admin-users'],
    queryFn: () => adminService.listUsers(),
    enabled: activeTab === 'users',
  })

  const createUserMutation = useMutation({
    mutationFn: () =>
      adminService.createUser({
        email: newEmail,
        full_name: newFullName,
        password: newPassword,
        is_superuser: newIsSuperuser,
      }),
    onSuccess: () => {
      setShowCreateForm(false)
      setNewEmail('')
      setNewFullName('')
      setNewPassword('')
      setNewIsSuperuser(false)
      queryClient.invalidateQueries({ queryKey: ['admin-users'] })
    },
  })

  const toggleActiveMutation = useMutation({
    mutationFn: (userId: number) => adminService.toggleUserActive(userId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['admin-users'] }),
  })

  const changePwdMutation = useMutation({
    mutationFn: ({ id, pwd }: { id: number; pwd: string }) =>
      adminService.changePassword(id, pwd),
    onSuccess: () => {
      setChangingPasswordFor(null)
      setNewPasswordValue('')
    },
  })

  // Feedback mutation
  const feedbackMutation = useMutation({
    mutationFn: (feedbackData: any) => adminService.addFeedback(feedbackData),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin-classifications'] })
      queryClient.invalidateQueries({ queryKey: ['admin-stats'] })
      setSelectedClassification(null)
    },
  })

  // Category mutations
  const createCategoryMutation = useMutation({
    mutationFn: (categoryData: any) => adminService.createCategory(categoryData),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin-categories'] })
      setShowCategoryModal(false)
    },
  })

  const updateCategoryMutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: any }) => adminService.updateCategory(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin-categories'] })
      setEditingCategory(null)
      setShowCategoryModal(false)
    },
  })

  const deleteCategoryMutation = useMutation({
    mutationFn: (id: number) => adminService.deleteCategory(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin-categories'] })
    },
  })

  const handleFeedback = (classificationId: number, feedbackType: string, correctData?: any) => {
    feedbackMutation.mutate({
      classification_id: classificationId,
      feedback_type: feedbackType,
      ...correctData,
    })
  }

  return (
    <div className="admin-panel">
      <div className="admin-header">
        <h1>⚙️ Panell d'Administració</h1>
        <p>Gestiona la classificació d'IA, categories i feedback per entrenar el sistema</p>
        
        {/* Case Selector */}
        <div className="case-selector">
          <label htmlFor="case-select">
            <strong>Filtrar per Cas:</strong>
          </label>
          <select
            id="case-select"
            value={selectedCaseId || ''}
            onChange={(e) => setSelectedCaseId(e.target.value ? parseInt(e.target.value) : null)}
            className="case-select"
          >
            <option value="">Tots els casos</option>
            {cases && cases.map((caseItem: any) => (
              <option key={caseItem.id} value={caseItem.id}>
                {caseItem.name} ({caseItem.case_type})
              </option>
            ))}
          </select>
          {selectedCaseId && (
            <button
              className="btn-clear-filter"
              onClick={() => setSelectedCaseId(null)}
            >
              ✕ Netejar filtre
            </button>
          )}
        </div>
      </div>

      <div className="admin-tabs">
        <button
          className={activeTab === 'classifications' ? 'active' : ''}
          onClick={() => setActiveTab('classifications')}
        >
          Classificacions
        </button>
        <button
          className={activeTab === 'categories' ? 'active' : ''}
          onClick={() => setActiveTab('categories')}
        >
          Categories (KPIs)
        </button>
        <button
          className={activeTab === 'feedback' ? 'active' : ''}
          onClick={() => setActiveTab('feedback')}
        >
          Feedback
        </button>
        <button
          className={activeTab === 'stats' ? 'active' : ''}
          onClick={() => setActiveTab('stats')}
        >
          Estadístiques
        </button>
        <button
          className={activeTab === 'users' ? 'active' : ''}
          onClick={() => setActiveTab('users')}
        >
          Usuaris
        </button>
      </div>

      <div className="admin-content">
        {activeTab === 'classifications' && (
          <div className="classifications-tab">
            <div className="classifications-header">
              <div>
                <h2>Classificacions d'IA</h2>
                <p>
                  {selectedCaseId 
                    ? `Classificacions per al cas seleccionat (${classifications?.length || 0} trobades)`
                    : `Totes les classificacions (${classifications?.length || 0} trobades)`
                  }
                </p>
              </div>
              {selectedCaseId && (
                <button
                  className="btn-reclassify"
                  onClick={async () => {
                    if (confirm('Vols reclassificar tots els resultats OSINT d\'aquest cas?')) {
                      try {
                        await adminService.reclassifyCase(selectedCaseId)
                        queryClient.invalidateQueries({ queryKey: ['admin-classifications'] })
                        alert('Reclassificació iniciada')
                      } catch (error) {
                        alert('Error en la reclassificació')
                      }
                    }
                  }}
                >
                  🔄 Reclassificar Cas
                </button>
              )}
            </div>
            
            {classificationsLoading ? (
              <p>Carregant...</p>
            ) : (
              <div className="classifications-list">
                {classifications && classifications.length > 0 ? (
                  classifications.slice(0, 100).map((classification: any) => (
                    <div key={classification.id} className="classification-card">
                      <div className="classification-header">
                        <div className="header-left">
                          <span className={`sentiment-badge sentiment-${classification.sentiment}`}>
                            {classification.sentiment}
                          </span>
                          <span className="confidence-score">
                            Confiança: {Math.round(classification.confidence_score * 100)}%
                          </span>
                          <span className="content-type-badge">
                            {classification.content_type}
                          </span>
                        </div>
                        <div className="header-right">
                          {classification.case_id && (
                            <span className="case-id-badge">
                              Cas #{classification.case_id}
                            </span>
                          )}
                        </div>
                      </div>
                      <div className="classification-content">
                        <p>{classification.content_text.substring(0, 200)}...</p>
                      </div>
                      <div className="classification-meta">
                        <div className="categories">
                          {classification.categories && classification.categories.length > 0 ? (
                            classification.categories.map((cat: string, idx: number) => (
                              <span key={idx} className="category-tag">{cat}</span>
                            ))
                          ) : (
                            <span className="no-categories">Sense categories</span>
                          )}
                        </div>
                        <div className="concepts">
                          {classification.concepts && classification.concepts.length > 0 && (
                            <span>Conceptes: {classification.concepts.join(', ')}</span>
                          )}
                        </div>
                      </div>
                      <div className="classification-actions">
                        {!classification.has_feedback ? (
                          <>
                            <button
                              className="btn-correct"
                              onClick={() => handleFeedback(classification.id, 'correct')}
                              disabled={feedbackMutation.isPending}
                            >
                              ✅ Correcte
                            </button>
                            <button
                              className="btn-incorrect"
                              onClick={() => setSelectedClassification(classification.id)}
                            >
                              ❌ Incorrecte
                            </button>
                          </>
                        ) : (
                          <span className="feedback-badge">
                            {classification.feedback_correct ? '✅ Correcte' : '❌ Incorrecte'}
                          </span>
                        )}
                      </div>
                    </div>
                  ))
                ) : (
                  <p>No hi ha classificacions disponibles</p>
                )}
              </div>
            )}
          </div>
        )}

        {activeTab === 'categories' && (
          <div className="categories-tab">
            <div className="categories-header">
              <h2>Categories de Classificació (KPIs)</h2>
              <button
                className="btn-create"
                onClick={() => {
                  setEditingCategory(null)
                  setShowCategoryModal(true)
                }}
              >
                + Nova Categoria
              </button>
            </div>
            
            {categoriesLoading ? (
              <p>Carregant...</p>
            ) : (
              <div className="categories-list">
                {categories && categories.length > 0 ? (
                  categories.map((category: any) => (
                    <div key={category.id} className="category-card">
                      <div className="category-header">
                        <h3>{category.name}</h3>
                        <span className={`status-badge ${category.is_active ? 'active' : 'inactive'}`}>
                          {category.is_active ? 'Activa' : 'Inactiva'}
                        </span>
                      </div>
                      <p className="category-description">{category.description || 'Sense descripció'}</p>
                      <div className="category-details">
                        <div><strong>Tipus:</strong> {category.category_type}</div>
                        <div><strong>Prioritat:</strong> {category.priority}</div>
                        <div><strong>Paraules clau:</strong> {category.keywords?.join(', ') || 'Cap'}</div>
                        <div><strong>Exemples positius:</strong> {category.examples_positive?.length || 0}</div>
                        <div><strong>Exemples negatius:</strong> {category.examples_negative?.length || 0}</div>
                      </div>
                      <div className="category-actions">
                        <button
                          className="btn-edit"
                          onClick={() => {
                            setEditingCategory(category)
                            setShowCategoryModal(true)
                          }}
                        >
                          ✏️ Editar
                        </button>
                        <button
                          className="btn-delete"
                          onClick={() => {
                            if (confirm(`Estàs segur que vols eliminar la categoria "${category.name}"?`)) {
                              deleteCategoryMutation.mutate(category.id)
                            }
                          }}
                        >
                          🗑️ Eliminar
                        </button>
                      </div>
                    </div>
                  ))
                ) : (
                  <p>No hi ha categories. Crea una per començar.</p>
                )}
              </div>
            )}
          </div>
        )}

        {activeTab === 'stats' && (
          <div className="stats-tab">
            <h2>Estadístiques de Classificació</h2>
            {stats ? (
              <div className="stats-grid">
                <div className="stat-card">
                  <h3>Total Classificacions</h3>
                  <div className="stat-value">{stats.total_classifications || 0}</div>
                </div>
                <div className="stat-card">
                  <h3>Amb Feedback</h3>
                  <div className="stat-value">{stats.with_feedback || 0}</div>
                  <div className="stat-percentage">
                    {stats.feedback_percentage ? `${stats.feedback_percentage.toFixed(1)}%` : '0%'}
                  </div>
                </div>
                <div className="stat-card">
                  <h3>Precisió</h3>
                  <div className="stat-value">{stats.accuracy ? `${stats.accuracy.toFixed(1)}%` : '0%'}</div>
                  <div className="stat-detail">
                    {stats.correct_classifications || 0} correctes / {stats.with_feedback || 0} amb feedback
                  </div>
                </div>
                <div className="stat-card">
                  <h3>Distribució de Sentiment</h3>
                  <div className="sentiment-distribution">
                    {stats.sentiment_distribution ? (
                      Object.entries(stats.sentiment_distribution).map(([sentiment, count]: [string, any]) => (
                        <div key={sentiment} className="sentiment-item">
                          <span className={`sentiment-badge sentiment-${sentiment}`}>{sentiment}</span>
                          <span>{count}</span>
                        </div>
                      ))
                    ) : (
                      <p>No hi ha dades</p>
                    )}
                  </div>
                </div>
              </div>
            ) : (
              <p>Carregant estadístiques...</p>
            )}
          </div>
        )}

        {activeTab === 'users' && (
          <div className="admin-section">
            <div
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                marginBottom: 'var(--spacing-lg)',
              }}
            >
              <h3 style={{ margin: 0 }}>Gestió d&apos;usuaris</h3>
              <button
                type="button"
                className="btn btn-primary"
                onClick={() => setShowCreateForm((v) => !v)}
              >
                {showCreateForm ? 'Cancel·lar' : '+ Nou usuari'}
              </button>
            </div>

            {showCreateForm && (
              <div
                style={{
                  background: 'var(--color-gray-50)',
                  border: '1px solid var(--color-gray-200)',
                  borderRadius: 'var(--radius-md)',
                  padding: 'var(--spacing-lg)',
                  marginBottom: 'var(--spacing-lg)',
                }}
              >
                <h4 style={{ margin: '0 0 var(--spacing-md)', fontSize: 'var(--font-size-sm)' }}>
                  Crear usuari nou
                </h4>
                {[
                  {
                    label: 'Email',
                    val: newEmail,
                    set: setNewEmail,
                    type: 'email',
                    placeholder: 'usuari@domini.cat',
                  },
                  {
                    label: 'Nom complet',
                    val: newFullName,
                    set: setNewFullName,
                    type: 'text',
                    placeholder: 'Nom Cognoms',
                  },
                  {
                    label: 'Contrasenya',
                    val: newPassword,
                    set: setNewPassword,
                    type: 'password',
                    placeholder: 'Mínim 8 caràcters',
                  },
                ].map(({ label, val, set, type, placeholder }) => (
                  <div key={label} style={{ marginBottom: 'var(--spacing-sm)' }}>
                    <label
                      style={{
                        display: 'block',
                        fontSize: 'var(--font-size-xs)',
                        fontWeight: 600,
                        color: 'var(--color-gray-600)',
                        marginBottom: 4,
                      }}
                    >
                      {label}
                    </label>
                    <input
                      type={type}
                      value={val}
                      placeholder={placeholder}
                      onChange={(e) => set(e.target.value)}
                      style={{
                        width: '100%',
                        maxWidth: 360,
                        padding: '8px 12px',
                        border: '1px solid var(--color-gray-300)',
                        borderRadius: 'var(--radius-sm)',
                        fontSize: 'var(--font-size-sm)',
                      }}
                    />
                  </div>
                ))}
                <label
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: 8,
                    fontSize: 'var(--font-size-sm)',
                    marginBottom: 'var(--spacing-md)',
                    cursor: 'pointer',
                  }}
                >
                  <input
                    type="checkbox"
                    checked={newIsSuperuser}
                    onChange={(e) => setNewIsSuperuser(e.target.checked)}
                  />
                  Superusuari (accés al panel admin)
                </label>
                <button
                  type="button"
                  className="btn btn-accent"
                  disabled={
                    !newEmail ||
                    !newFullName ||
                    !newPassword ||
                    createUserMutation.isPending
                  }
                  onClick={() => createUserMutation.mutate()}
                >
                  {createUserMutation.isPending ? 'Creant...' : 'Crear usuari'}
                </button>
                {createUserMutation.isError && (
                  <p
                    style={{
                      color: 'var(--color-danger)',
                      fontSize: 'var(--font-size-xs)',
                      marginTop: 'var(--spacing-sm)',
                    }}
                  >
                    {(createUserMutation.error as Error)?.message ?? 'Error creant usuari'}
                  </p>
                )}
              </div>
            )}

            <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--spacing-sm)' }}>
              {(
                users as {
                  id: number
                  email: string
                  full_name: string
                  is_active: boolean
                  is_superuser: boolean
                  created_at: string | null
                }[]
              ).map((user) => (
                <div
                  key={user.id}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: 'var(--spacing-md)',
                    padding: 'var(--spacing-sm) var(--spacing-md)',
                    border: '1px solid var(--color-gray-200)',
                    borderRadius: 'var(--radius-sm)',
                    opacity: user.is_active ? 1 : 0.55,
                    flexWrap: 'wrap',
                  }}
                >
                  <div style={{ flex: 1, minWidth: 180 }}>
                    <p
                      style={{
                        margin: 0,
                        fontWeight: 500,
                        fontSize: 'var(--font-size-sm)',
                        color: 'var(--color-gray-800)',
                      }}
                    >
                      {user.full_name}
                    </p>
                    <p
                      style={{
                        margin: '2px 0 0',
                        fontSize: 'var(--font-size-xs)',
                        color: 'var(--color-gray-500)',
                      }}
                    >
                      {user.email}
                    </p>
                  </div>
                  <div style={{ display: 'flex', gap: 'var(--spacing-xs)', flexWrap: 'wrap' }}>
                    {user.is_superuser && (
                      <span className="status-badge user-badge-admin">Admin</span>
                    )}
                    <span
                      className={`status-badge ${user.is_active ? 'user-badge-active' : 'user-badge-inactive'}`}
                    >
                      {user.is_active ? 'Actiu' : 'Inactiu'}
                    </span>
                  </div>
                  <button
                    type="button"
                    className="btn"
                    style={{ fontSize: 'var(--font-size-xs)', padding: '4px 10px' }}
                    disabled={toggleActiveMutation.isPending}
                    onClick={() => toggleActiveMutation.mutate(user.id)}
                  >
                    {user.is_active ? 'Desactivar' : 'Activar'}
                  </button>
                  {changingPasswordFor === user.id ? (
                    <div style={{ display: 'flex', gap: 4, alignItems: 'center', marginTop: 4, width: '100%' }}>
                      <input
                        type="password"
                        placeholder="Nova contrasenya (mínim 8)"
                        value={newPasswordValue}
                        onChange={(e) => setNewPasswordValue(e.target.value)}
                        style={{
                          padding: '4px 8px',
                          border: '1px solid var(--color-gray-300)',
                          borderRadius: 'var(--radius-sm)',
                          fontSize: 'var(--font-size-xs)',
                          width: 180,
                        }}
                      />
                      <button
                        type="button"
                        className="btn"
                        style={{ fontSize: 'var(--font-size-xs)', padding: '4px 8px' }}
                        disabled={newPasswordValue.length < 8 || changePwdMutation.isPending}
                        onClick={() =>
                          changePwdMutation.mutate({ id: user.id, pwd: newPasswordValue })
                        }
                      >
                        Desar
                      </button>
                      <button
                        type="button"
                        className="btn"
                        style={{ fontSize: 'var(--font-size-xs)', padding: '4px 8px' }}
                        onClick={() => {
                          setChangingPasswordFor(null)
                          setNewPasswordValue('')
                        }}
                      >
                        ✕
                      </button>
                    </div>
                  ) : (
                    <button
                      type="button"
                      className="btn"
                      style={{ fontSize: 'var(--font-size-xs)', padding: '4px 10px' }}
                      onClick={() => setChangingPasswordFor(user.id)}
                    >
                      Canviar contrasenya
                    </button>
                  )}
                </div>
              ))}
              {(users as unknown[]).length === 0 && (
                <div className="empty-state">
                  <div className="empty-state-icon">◉</div>
                  <h3 className="empty-state-title">Cap usuari</h3>
                  <p className="empty-state-desc">
                    Crea el primer usuari amb el botó &quot;Nou usuari&quot;.
                  </p>
                </div>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Feedback Modal */}
      {selectedClassification && (
        <FeedbackModal
          classificationId={selectedClassification}
          onClose={() => setSelectedClassification(null)}
          onSave={(feedbackData: Record<string, unknown>) => {
            handleFeedback(selectedClassification, 'incorrect', feedbackData)
            setSelectedClassification(null)
          }}
        />
      )}

      {/* Category Modal */}
      {showCategoryModal && (
        <CategoryModal
          category={editingCategory}
          onClose={() => {
            setShowCategoryModal(false)
            setEditingCategory(null)
          }}
          onSave={(categoryData: Record<string, unknown>) => {
            if (editingCategory) {
              updateCategoryMutation.mutate({ id: editingCategory.id, data: categoryData })
            } else {
              createCategoryMutation.mutate(categoryData)
            }
          }}
        />
      )}
    </div>
  )
}

function FeedbackModal({ classificationId, onClose, onSave }: any) {
  const [feedbackType, setFeedbackType] = useState('incorrect')
  const [correctSentiment, setCorrectSentiment] = useState('')
  const [correctCategories, setCorrectCategories] = useState<string[]>([])
  const [notes, setNotes] = useState('')

  const { data: classification } = useQuery({
    queryKey: ['admin-classification', classificationId],
    queryFn: () => adminService.getClassification(classificationId),
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    onSave({
      correct_sentiment: correctSentiment || undefined,
      correct_categories: correctCategories.length > 0 ? correctCategories : undefined,
      feedback_notes: notes || undefined,
    })
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <h2>Proporcionar Feedback</h2>
        {classification && (
          <div className="classification-preview">
            <p><strong>Classificació actual:</strong></p>
            <p>Sentiment: {classification.sentiment} (score: {classification.sentiment_score})</p>
            <p>Categories: {classification.categories?.join(', ') || 'Cap'}</p>
            <p>Text: {classification.content_text.substring(0, 200)}...</p>
          </div>
        )}
        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label>Sentiment Correcte:</label>
            <select
              value={correctSentiment}
              onChange={(e) => setCorrectSentiment(e.target.value)}
            >
              <option value="">-- Mantenir actual --</option>
              <option value="positive">Positiu</option>
              <option value="negative">Negatiu</option>
              <option value="neutral">Neutral</option>
            </select>
          </div>
          <div className="form-group">
            <label>Notes:</label>
            <textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              rows={4}
              placeholder="Explica què està malament i com hauria de ser..."
            />
          </div>
          <div className="modal-actions">
            <button type="button" onClick={onClose}>Cancel·lar</button>
            <button type="submit">Guardar Feedback</button>
          </div>
        </form>
      </div>
    </div>
  )
}

function CategoryModal({ category, onClose, onSave }: any) {
  const [name, setName] = useState(category?.name || '')
  const [description, setDescription] = useState(category?.description || '')
  const [categoryType, setCategoryType] = useState(category?.category_type || 'topic')
  const [keywords, setKeywords] = useState(category?.keywords?.join('\n') || '')
  const [priority, setPriority] = useState(category?.priority || 0)
  const [isActive, setIsActive] = useState(category?.is_active !== false)

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    onSave({
      name,
      description,
      category_type: categoryType,
      keywords: keywords.split('\n').filter((k: string) => k.trim()),
      priority: parseInt(priority.toString()),
      is_active: isActive,
    })
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <h2>{category ? 'Editar Categoria' : 'Nova Categoria'}</h2>
        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label>Nom *</label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
            />
          </div>
          <div className="form-group">
            <label>Descripció</label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={3}
            />
          </div>
          <div className="form-group">
            <label>Tipus *</label>
            <select
              value={categoryType}
              onChange={(e) => setCategoryType(e.target.value)}
              required
            >
              <option value="sentiment">Sentiment</option>
              <option value="topic">Tema</option>
              <option value="theme">Temàtica</option>
              <option value="industry">Indústria</option>
            </select>
          </div>
          <div className="form-group">
            <label>Paraules Clau (una per línia)</label>
            <textarea
              value={keywords}
              onChange={(e) => setKeywords(e.target.value)}
              rows={5}
              placeholder="Paraula1&#10;Paraula2&#10;Paraula3"
            />
          </div>
          <div className="form-group">
            <label>Prioritat</label>
            <input
              type="number"
              value={priority}
              onChange={(e) => setPriority(parseInt(e.target.value) || 0)}
              min="0"
            />
          </div>
          <div className="form-group">
            <label>
              <input
                type="checkbox"
                checked={isActive}
                onChange={(e) => setIsActive(e.target.checked)}
              />
              Activa
            </label>
          </div>
          <div className="modal-actions">
            <button type="button" onClick={onClose}>Cancel·lar</button>
            <button type="submit">Guardar</button>
          </div>
        </form>
      </div>
    </div>
  )
}

