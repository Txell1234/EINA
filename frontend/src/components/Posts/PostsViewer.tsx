import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { postsService, adminService } from '../../services/api'
import './PostsViewer.css'

interface PostsViewerProps {
  caseId: number
  initialFilters?: {
    sentiment?: string
    category?: string
    concept?: string
  }
  onPostClick?: (post: any) => void
}

export default function PostsViewer({ caseId, initialFilters, onPostClick }: PostsViewerProps) {
  const [filters, setFilters] = useState({
    sentiment: initialFilters?.sentiment || '',
    category: initialFilters?.category || '',
    concept: initialFilters?.concept || '',
    content_type: '',
    search_text: '',
  })
  const [selectedPost, setSelectedPost] = useState<any>(null)
  const [feedbackPost, setFeedbackPost] = useState<any>(null)
  const queryClient = useQueryClient()

  // Feedback mutation
  const feedbackMutation = useMutation({
    mutationFn: (feedbackData: any) => adminService.addFeedback(feedbackData),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['case-posts', caseId] })
      queryClient.invalidateQueries({ queryKey: ['posts-stats', caseId] })
      queryClient.invalidateQueries({ queryKey: ['admin-stats'] })
      setFeedbackPost(null)
      alert('Feedback guardat! La IA aprendrà d\'aquesta correcció.')
    },
    onError: (error: any) => {
      alert('Error al guardar el feedback: ' + (error.message || 'Error desconegut'))
    }
  })

  // Get posts stats
  const { data: stats } = useQuery({
    queryKey: ['posts-stats', caseId],
    queryFn: () => postsService.getPostsStats(caseId),
  })

  // Get posts with filters
  const { data: posts, isLoading } = useQuery({
    queryKey: ['case-posts', caseId, filters],
    queryFn: () => postsService.getCasePosts(caseId, filters),
  })

  const handleFilterChange = (key: string, value: string) => {
    setFilters(prev => ({ ...prev, [key]: value }))
  }

  const clearFilters = () => {
    setFilters({
      sentiment: '',
      category: '',
      concept: '',
      content_type: '',
      search_text: '',
    })
  }

  const handlePostClick = (post: any) => {
    setSelectedPost(post)
    if (onPostClick) {
      onPostClick(post)
    }
  }

  const activeFiltersCount = Object.values(filters).filter(v => v).length

  return (
    <div className="posts-viewer">
      <div className="posts-header">
        <h2>📱 Posts de Xarxes Socials</h2>
        {stats && (
          <div className="posts-stats">
            <span className="stat-item">
              <strong>{stats.total_posts || 0}</strong> posts totals
            </span>
            <span className="stat-item">
              <span className="sentiment-badge sentiment-positive">{stats.sentiment_distribution?.positive || 0}</span>
              <span className="sentiment-badge sentiment-negative">{stats.sentiment_distribution?.negative || 0}</span>
              <span className="sentiment-badge sentiment-neutral">{stats.sentiment_distribution?.neutral || 0}</span>
            </span>
          </div>
        )}
      </div>

      {/* Filters */}
      <div className="posts-filters">
        <div className="filter-group">
          <label>Sentiment:</label>
          <select
            value={filters.sentiment}
            onChange={(e) => handleFilterChange('sentiment', e.target.value)}
          >
            <option value="">Tots</option>
            <option value="positive">Positiu</option>
            <option value="negative">Negatiu</option>
            <option value="neutral">Neutral</option>
          </select>
        </div>

        <div className="filter-group">
          <label>Categoria:</label>
          <select
            value={filters.category}
            onChange={(e) => handleFilterChange('category', e.target.value)}
          >
            <option value="">Totes</option>
            {stats?.available_categories?.map((cat: string) => (
              <option key={cat} value={cat}>{cat}</option>
            ))}
          </select>
        </div>

        <div className="filter-group">
          <label>Concepte:</label>
          <select
            value={filters.concept}
            onChange={(e) => handleFilterChange('concept', e.target.value)}
          >
            <option value="">Tots</option>
            {stats?.available_concepts?.map((concept: string) => (
              <option key={concept} value={concept}>{concept}</option>
            ))}
          </select>
        </div>

        <div className="filter-group">
          <label>Tipus:</label>
          <select
            value={filters.content_type}
            onChange={(e) => handleFilterChange('content_type', e.target.value)}
          >
            <option value="">Tots</option>
            {stats?.content_type_distribution && Object.keys(stats.content_type_distribution).map((type: string) => (
              <option key={type} value={type}>{type}</option>
            ))}
          </select>
        </div>

        <div className="filter-group">
          <label>Cercar:</label>
          <input
            type="text"
            value={filters.search_text}
            onChange={(e) => handleFilterChange('search_text', e.target.value)}
            placeholder="Cercar en el text..."
          />
        </div>

        {activeFiltersCount > 0 && (
          <button className="btn-clear-filters" onClick={clearFilters}>
            ✕ Netejar filtres ({activeFiltersCount})
          </button>
        )}
      </div>

      {/* Posts List */}
      {isLoading ? (
        <div className="loading">Carregant posts...</div>
      ) : (
        <div className="posts-list">
          {posts && posts.length > 0 ? (
            posts.map((post: any) => (
              <div
                key={post.id}
                className={`post-card sentiment-${post.sentiment}`}
                onClick={() => handlePostClick(post)}
              >
                <div className="post-header">
                  <div className="post-meta">
                    <span className={`sentiment-badge sentiment-${post.sentiment}`}>
                      {post.sentiment}
                    </span>
                    <span className="content-type-badge">{post.content_type}</span>
                    {post.source_platform && (
                      <span className="platform-badge">{post.source_platform}</span>
                    )}
                    {post.author && (
                      <span className="author-badge">@{post.author}</span>
                    )}
                  </div>
                  <div className="post-confidence">
                    Confiança: {Math.round(post.confidence_score * 100)}%
                  </div>
                </div>

                <div className="post-content">
                  <p>{post.content_text}</p>
                </div>

                {post.categories && post.categories.length > 0 && (
                  <div className="post-categories">
                    {post.categories.map((cat: string, idx: number) => (
                      <span key={idx} className="category-tag">{cat}</span>
                    ))}
                  </div>
                )}

                {post.concepts && post.concepts.length > 0 && (
                  <div className="post-concepts">
                    <strong>Conceptes:</strong> {post.concepts.join(', ')}
                  </div>
                )}

                {post.engagement && (
                  <div className="post-engagement">
                    <span>👍 {post.engagement.likes || 0}</span>
                    <span>💬 {post.engagement.comments || 0}</span>
                    <span>🔄 {post.engagement.shares || 0}</span>
                    <span>👁️ {post.engagement.views || 0}</span>
                  </div>
                )}

                {post.source_url && (
                  <div className="post-link">
                    <a href={post.source_url} target="_blank" rel="noopener noreferrer" onClick={(e) => e.stopPropagation()}>
                      Veure post original →
                    </a>
                  </div>
                )}

                <div className="post-date">
                  {new Date(post.created_at).toLocaleString('ca-ES')}
                </div>
              </div>
            ))
          ) : (
            <div className="no-posts">
              <p>No s'han trobat posts amb aquests filtres.</p>
              {activeFiltersCount > 0 && (
                <button onClick={clearFilters}>Netejar filtres</button>
              )}
            </div>
          )}
        </div>
      )}

      {/* Post Detail Modal */}
      {selectedPost && (
        <PostDetailModal
          post={selectedPost}
          onClose={() => setSelectedPost(null)}
          onFeedback={(post) => {
            setSelectedPost(null)
            setFeedbackPost(post)
          }}
        />
      )}

      {/* Feedback Modal */}
      {feedbackPost && (
        <FeedbackModal
          post={feedbackPost}
          onClose={() => setFeedbackPost(null)}
          onSave={(feedbackData) => {
            feedbackMutation.mutate({
              classification_id: feedbackPost.id,
              feedback_type: 'incorrect',
              ...feedbackData,
            })
          }}
        />
      )}
    </div>
  )
}

function PostDetailModal({ post, onClose, onFeedback }: { post: any; onClose: () => void; onFeedback?: (post: any) => void }) {
  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content post-detail-modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>Detall del Post</h2>
          <button className="btn-close" onClick={onClose}>✕</button>
        </div>

        <div className="post-detail-content">
          <div className="detail-section">
            <h3>Classificació d'IA</h3>
            <div className="detail-grid">
              <div>
                <strong>Sentiment:</strong>
                <span className={`sentiment-badge sentiment-${post.sentiment}`}>
                  {post.sentiment} ({post.sentiment_score > 0 ? '+' : ''}{post.sentiment_score.toFixed(2)})
                </span>
              </div>
              <div>
                <strong>Confiança:</strong> {Math.round(post.confidence_score * 100)}%
              </div>
              <div>
                <strong>Tipus de contingut:</strong> {post.content_type}
              </div>
            </div>
          </div>

          <div className="detail-section">
            <h3>Contingut</h3>
            <div className="post-text-full">
              {post.content_text}
            </div>
          </div>

          {post.categories && post.categories.length > 0 && (
            <div className="detail-section">
              <h3>Categories</h3>
              <div className="categories-list">
                {post.categories.map((cat: string, idx: number) => (
                  <span key={idx} className="category-tag">{cat}</span>
                ))}
              </div>
            </div>
          )}

          {post.concepts && post.concepts.length > 0 && (
            <div className="detail-section">
              <h3>Conceptes</h3>
              <div className="concepts-list">
                {post.concepts.map((concept: string, idx: number) => (
                  <span key={idx} className="concept-tag">{concept}</span>
                ))}
              </div>
            </div>
          )}

          {post.engagement && (
            <div className="detail-section">
              <h3>Engagement</h3>
              <div className="engagement-stats">
                <div className="engagement-item">
                  <span className="engagement-icon">👍</span>
                  <span className="engagement-label">Likes:</span>
                  <span className="engagement-value">{post.engagement.likes || 0}</span>
                </div>
                <div className="engagement-item">
                  <span className="engagement-icon">💬</span>
                  <span className="engagement-label">Comentaris:</span>
                  <span className="engagement-value">{post.engagement.comments || 0}</span>
                </div>
                <div className="engagement-item">
                  <span className="engagement-icon">🔄</span>
                  <span className="engagement-label">Compartits:</span>
                  <span className="engagement-value">{post.engagement.shares || 0}</span>
                </div>
                <div className="engagement-item">
                  <span className="engagement-icon">👁️</span>
                  <span className="engagement-label">Visualitzacions:</span>
                  <span className="engagement-value">{post.engagement.views || 0}</span>
                </div>
              </div>
            </div>
          )}

          {post.source_url && (
            <div className="detail-section">
              <h3>Enllaç Original</h3>
              <a href={post.source_url} target="_blank" rel="noopener noreferrer" className="source-link">
                {post.source_url}
              </a>
            </div>
          )}

          {post.raw_data && (
            <div className="detail-section">
              <h3>Dades Raw (JSON)</h3>
              <pre className="raw-data">
                {JSON.stringify(post.raw_data, null, 2)}
              </pre>
            </div>
          )}

          {/* Feedback section in detail modal */}
          <div className="detail-section">
            <h3>Feedback per a la IA</h3>
            <p style={{ fontSize: '0.875rem', color: '#666', marginBottom: '1rem' }}>
              Ajuda la IA a aprendre indicant si la classificació és correcta o com s'hauria d'haver classificat.
            </p>
            <div className="feedback-actions">
              <button
                className="btn-feedback-correct"
                onClick={() => {
                  // This would need to be passed through props or use a mutation hook
                  if (onFeedback) {
                    // For now, just close and open feedback modal
                    onClose()
                    onFeedback(post)
                  }
                }}
              >
                ✅ Classificació Correcta
              </button>
              <button
                className="btn-feedback-incorrect"
                onClick={() => {
                  onClose()
                  if (onFeedback) {
                    onFeedback(post)
                  }
                }}
              >
                ❌ Corregir Classificació
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

function FeedbackModal({ post, onClose, onSave }: { post: any; onClose: () => void; onSave: (data: any) => void }) {
  const [correctSentiment, setCorrectSentiment] = useState(post.sentiment || '')
  const [correctCategories, setCorrectCategories] = useState<string[]>(post.categories || [])
  const [newCategory, setNewCategory] = useState('')
  const [correctConcepts, setCorrectConcepts] = useState<string[]>(post.concepts || [])
  const [newConcept, setNewConcept] = useState('')
  const [feedbackNotes, setFeedbackNotes] = useState('')

  // Get available categories from stats
  const { data: stats } = useQuery({
    queryKey: ['posts-stats', post.case_id],
    queryFn: () => postsService.getPostsStats(post.case_id),
  })

  const handleAddCategory = () => {
    if (newCategory.trim() && !correctCategories.includes(newCategory.trim())) {
      setCorrectCategories([...correctCategories, newCategory.trim()])
      setNewCategory('')
    }
  }

  const handleRemoveCategory = (category: string) => {
    setCorrectCategories(correctCategories.filter(c => c !== category))
  }

  const handleAddConcept = () => {
    if (newConcept.trim() && !correctConcepts.includes(newConcept.trim())) {
      setCorrectConcepts([...correctConcepts, newConcept.trim()])
      setNewConcept('')
    }
  }

  const handleRemoveConcept = (concept: string) => {
    setCorrectConcepts(correctConcepts.filter(c => c !== concept))
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    onSave({
      correct_sentiment: correctSentiment || undefined,
      correct_categories: correctCategories.length > 0 ? correctCategories : undefined,
      correct_concepts: correctConcepts.length > 0 ? correctConcepts : undefined,
      feedback_notes: feedbackNotes || undefined,
    })
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content feedback-modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>📝 Corregir Classificació d'IA</h2>
          <button className="btn-close" onClick={onClose}>✕</button>
        </div>

        <div className="feedback-content">
          <div className="current-classification">
            <h3>Classificació Actual (IA)</h3>
            <div className="classification-preview">
              <div className="preview-item">
                <strong>Sentiment:</strong>
                <span className={`sentiment-badge sentiment-${post.sentiment}`}>
                  {post.sentiment} ({post.sentiment_score > 0 ? '+' : ''}{post.sentiment_score.toFixed(2)})
                </span>
              </div>
              <div className="preview-item">
                <strong>Categories:</strong>
                {post.categories && post.categories.length > 0 ? (
                  post.categories.map((cat: string, idx: number) => (
                    <span key={idx} className="category-tag">{cat}</span>
                  ))
                ) : (
                  <span className="no-data">Cap categoria</span>
                )}
              </div>
              <div className="preview-item">
                <strong>Conceptes:</strong>
                {post.concepts && post.concepts.length > 0 ? (
                  post.concepts.join(', ')
                ) : (
                  <span className="no-data">Cap concepte</span>
                )}
              </div>
            </div>
          </div>

          <div className="post-text-preview">
            <h4>Text del Post:</h4>
            <p className="post-text">{post.content_text}</p>
          </div>

          <form onSubmit={handleSubmit} className="feedback-form">
            <div className="form-section">
              <h3>Classificació Correcta</h3>
              
              <div className="form-group">
                <label>Sentiment Correcte *</label>
                <select
                  value={correctSentiment}
                  onChange={(e) => setCorrectSentiment(e.target.value)}
                  required
                >
                  <option value="">-- Selecciona --</option>
                  <option value="positive">Positiu</option>
                  <option value="negative">Negatiu</option>
                  <option value="neutral">Neutral</option>
                </select>
              </div>

              <div className="form-group">
                <label>Categories Correctes</label>
                <div className="categories-input">
                  <div className="selected-categories">
                    {correctCategories.map((cat, idx) => (
                      <span key={idx} className="category-tag">
                        {cat}
                        <button
                          type="button"
                          onClick={() => handleRemoveCategory(cat)}
                          className="remove-tag"
                        >
                          ✕
                        </button>
                      </span>
                    ))}
                  </div>
                  <div className="add-category">
                    <input
                      type="text"
                      value={newCategory}
                      onChange={(e) => setNewCategory(e.target.value)}
                      onKeyPress={(e) => {
                        if (e.key === 'Enter') {
                          e.preventDefault()
                          handleAddCategory()
                        }
                      }}
                      placeholder="Afegir categoria..."
                    />
                    <button type="button" onClick={handleAddCategory}>+</button>
                  </div>
                  {stats?.available_categories && stats.available_categories.length > 0 && (
                    <div className="suggested-categories">
                      <small>Categories disponibles:</small>
                      <div className="category-suggestions">
                        {stats.available_categories
                          .filter((cat: string) => !correctCategories.includes(cat))
                          .slice(0, 10)
                          .map((cat: string) => (
                            <button
                              key={cat}
                              type="button"
                              className="suggestion-tag"
                              onClick={() => {
                                if (!correctCategories.includes(cat)) {
                                  setCorrectCategories([...correctCategories, cat])
                                }
                              }}
                            >
                              + {cat}
                            </button>
                          ))}
                      </div>
                    </div>
                  )}
                </div>
              </div>

              <div className="form-group">
                <label>Conceptes Correctes</label>
                <div className="concepts-input">
                  <div className="selected-concepts">
                    {correctConcepts.map((concept, idx) => (
                      <span key={idx} className="concept-tag">
                        {concept}
                        <button
                          type="button"
                          onClick={() => handleRemoveConcept(concept)}
                          className="remove-tag"
                        >
                          ✕
                        </button>
                      </span>
                    ))}
                  </div>
                  <div className="add-concept">
                    <input
                      type="text"
                      value={newConcept}
                      onChange={(e) => setNewConcept(e.target.value)}
                      onKeyPress={(e) => {
                        if (e.key === 'Enter') {
                          e.preventDefault()
                          handleAddConcept()
                        }
                      }}
                      placeholder="Afegir concepte..."
                    />
                    <button type="button" onClick={handleAddConcept}>+</button>
                  </div>
                  {stats?.available_concepts && stats.available_concepts.length > 0 && (
                    <div className="suggested-concepts">
                      <small>Conceptes disponibles:</small>
                      <div className="concept-suggestions">
                        {stats.available_concepts
                          .filter((concept: string) => !correctConcepts.includes(concept))
                          .slice(0, 10)
                          .map((concept: string) => (
                            <button
                              key={concept}
                              type="button"
                              className="suggestion-tag"
                              onClick={() => {
                                if (!correctConcepts.includes(concept)) {
                                  setCorrectConcepts([...correctConcepts, concept])
                                }
                              }}
                            >
                              + {concept}
                            </button>
                          ))}
                      </div>
                    </div>
                  )}
                </div>
              </div>

              <div className="form-group">
                <label>Notes (Opcional)</label>
                <textarea
                  value={feedbackNotes}
                  onChange={(e) => setFeedbackNotes(e.target.value)}
                  rows={4}
                  placeholder="Explica què està malament i per què la classificació correcta és diferent..."
                />
              </div>
            </div>

            <div className="modal-actions">
              <button type="button" onClick={onClose}>Cancel·lar</button>
              <button type="submit" className="btn-submit-feedback">
                💾 Guardar Feedback i Entrenar IA
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  )
}

