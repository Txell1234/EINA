import React, { useState } from 'react';
import { useMutation, useQueryClient } from 'react-query';
import {
  Box,
  Button,
  Card,
  CardContent,
  Typography,
  Alert,
  Chip,
  Grid,
  TextField,
  alpha,
  Paper,
  Divider,
} from '@mui/material';
import {
  Public as PublicIcon,
  People as PeopleIcon,
  TrendingUp as TrendingUpIcon,
  Psychology as PsychologyIcon,
  Assessment as AssessmentIcon,
  Analytics as AnalyticsIcon,
} from '@mui/icons-material';
import {
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Radar,
  ResponsiveContainer,
  Tooltip,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
} from 'recharts';
import { analyzeUnified } from '../../services/api';
import GeopoliticalMap from '../GeopoliticalMap';
import ExecutiveSummary from '../ExecutiveSummary';

function UnifiedAnalysisTab({ caseId, caseData }) {
  const [country, setCountry] = useState('');
  const [actor, setActor] = useState('');
  const queryClient = useQueryClient();

  const analyzeMutation = useMutation(
    () => analyzeUnified(caseId, country || null, actor || null),
    {
      onSuccess: () => {
        queryClient.invalidateQueries(['case', caseId]);
      },
    }
  );

  const unifiedAnalysis = caseData?.unified_analysis;
  const globalDecision = unifiedAnalysis?.global_decision || {};
  const visualization = unifiedAnalysis?.unified_visualization || {};

  const getDecisionColor = (recommendation) => {
    switch (recommendation) {
      case 'PROCEED':
        return 'success';
      case 'PROCEED_WITH_CAUTION':
        return 'warning';
      case 'HOLD':
        return 'info';
      case 'MONITOR':
        return 'default';
      case 'AVOID':
        return 'error';
      default:
        return 'default';
    }
  };

  const getPriorityColor = (priority) => {
    switch (priority) {
      case 'HIGH':
        return 'error';
      case 'MEDIUM':
        return 'warning';
      case 'LOW':
        return 'success';
      default:
        return 'default';
    }
  };

  // Preparar dades per radar chart
  const riskRadarData = visualization.risk_radar
    ? Object.entries(visualization.risk_radar).map(([key, value]) => ({
        category: key.charAt(0).toUpperCase() + key.slice(1),
        value: value,
        fullMark: 100,
      }))
    : [];

  const sourcesData = unifiedAnalysis?.sources_analyzed
    ? Object.entries(unifiedAnalysis.sources_analyzed).map(([key, value]) => ({
        name: key.charAt(0).toUpperCase() + key.slice(1),
        value: value,
      }))
    : [];

  return (
    <Box>
      <Card
        sx={{
          mb: 3,
          background: 'linear-gradient(135deg, #ffffff 0%, #f9fafb 100%)',
          border: '1px solid rgba(0, 0, 0, 0.05)',
        }}
      >
        <CardContent>
          <Typography variant="h6" sx={{ fontWeight: 600, mb: 3, color: '#1a1f3a' }}>
            Anàlisi Unificada Global
          </Typography>

          <Grid container spacing={2} sx={{ mb: 3 }}>
            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                label="País (opcional)"
                value={country}
                onChange={(e) => setCountry(e.target.value)}
                placeholder="Ex: Espanya, USA, China..."
                variant="outlined"
                size="small"
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                label="Actor (opcional)"
                value={actor}
                onChange={(e) => setActor(e.target.value)}
                placeholder="Ex: Govern, ONU, Empresa..."
                variant="outlined"
                size="small"
              />
            </Grid>
          </Grid>

          <Button
            variant="contained"
            startIcon={<AnalyticsIcon />}
            onClick={() => analyzeMutation.mutate()}
            disabled={analyzeMutation.isLoading || !caseData?.osint_data?.length}
            fullWidth
            sx={{
              backgroundColor: '#E3120B', // Vermell EIU
              '&:hover': {
                backgroundColor: '#B00E08',
              },
              textTransform: 'none',
              fontWeight: 500,
              py: 1.5,
            }}
          >
            {analyzeMutation.isLoading ? 'Analitzant...' : 'Generar Anàlisi Unificada'}
          </Button>

          {!caseData?.osint_data?.length && (
            <Alert severity="warning" sx={{ mt: 2 }}>
              Necessites recopilar dades OSINT abans de poder generar anàlisi unificada.
            </Alert>
          )}
        </CardContent>
      </Card>

      {analyzeMutation.isError && (
        <Alert severity="error" sx={{ mb: 2 }}>
          Error generant anàlisi unificada
        </Alert>
      )}

      {unifiedAnalysis ? (
        <>
          {/* Resum Executiu - Estil EIU */}
          <ExecutiveSummary analysis={unifiedAnalysis} caseData={caseData} />

          {/* Decisió Global */}
          <Card
            sx={{
              mb: 3,
              background: 'linear-gradient(135deg, #ffffff 0%, #f9fafb 100%)',
              border: '1px solid rgba(0, 0, 0, 0.05)',
            }}
          >
            <CardContent>
              <Typography variant="h5" sx={{ fontWeight: 700, mb: 3, color: '#1a1f3a' }}>
                Decisió Global Unificada
              </Typography>

              <Box sx={{ display: 'flex', gap: 2, mb: 3, flexWrap: 'wrap' }}>
                <Chip
                  label={`DECISIÓ: ${globalDecision.recommendation || 'N/A'}`}
                  color={getDecisionColor(globalDecision.recommendation)}
                  size="large"
                  sx={{ fontWeight: 700, fontSize: '1rem', px: 2, py: 3 }}
                />
                <Chip
                  label={`Confiança: ${((globalDecision.confidence || 0) * 100).toFixed(0)}%`}
                  sx={{
                    backgroundColor: alpha('#3b82f6', 0.1),
                    color: '#3b82f6',
                    fontWeight: 600,
                    px: 2,
                    py: 3,
                  }}
                  size="large"
                />
                <Chip
                  label={`Prioritat: ${globalDecision.priority || 'N/A'}`}
                  color={getPriorityColor(globalDecision.priority)}
                  size="large"
                  sx={{ fontWeight: 600, px: 2, py: 3 }}
                />
              </Box>

              <Paper
                sx={{
                  p: 3,
                  backgroundColor: alpha('#E3120B', 0.05),
                  borderRadius: 2,
                  border: `2px solid ${alpha('#E3120B', 0.2)}`,
                }}
              >
                <Typography variant="h6" gutterBottom sx={{ fontWeight: 600, color: '#1a1f3a' }}>
                  Raonament
                </Typography>
                <Typography variant="body1" sx={{ color: '#4b5563', whiteSpace: 'pre-line' }}>
                  {globalDecision.reasoning || 'No disponible'}
                </Typography>
              </Paper>

              {/* Scores Globals */}
              <Grid container spacing={2} sx={{ mt: 3 }}>
                <Grid item xs={6} md={3}>
                  <Paper sx={{ p: 2, textAlign: 'center', backgroundColor: alpha('#ef4444', 0.1) }}>
                    <Typography variant="caption" sx={{ color: '#6b7280' }}>
                      Risc Global
                    </Typography>
                    <Typography variant="h4" sx={{ fontWeight: 700, color: '#ef4444' }}>
                      {((globalDecision.global_risk_score || 0) * 100).toFixed(0)}%
                    </Typography>
                  </Paper>
                </Grid>
                <Grid item xs={6} md={3}>
                  <Paper sx={{ p: 2, textAlign: 'center', backgroundColor: alpha('#10b981', 0.1) }}>
                    <Typography variant="caption" sx={{ color: '#6b7280' }}>
                      Oportunitat Global
                    </Typography>
                    <Typography variant="h4" sx={{ fontWeight: 700, color: '#10b981' }}>
                      {((globalDecision.global_opportunity_score || 0) * 100).toFixed(0)}%
                    </Typography>
                  </Paper>
                </Grid>
                <Grid item xs={6} md={3}>
                  <Paper sx={{ p: 2, textAlign: 'center', backgroundColor: alpha('#f59e0b', 0.1) }}>
                    <Typography variant="caption" sx={{ color: '#6b7280' }}>
                      Índex Geopolític
                    </Typography>
                    <Typography variant="h4" sx={{ fontWeight: 700, color: '#f59e0b' }}>
                      {((globalDecision.geopolitical_index || 0) * 100).toFixed(0)}%
                    </Typography>
                  </Paper>
                </Grid>
                <Grid item xs={6} md={3}>
                  <Paper sx={{ p: 2, textAlign: 'center', backgroundColor: alpha('#3b82f6', 0.1) }}>
                    <Typography variant="caption" sx={{ color: '#6b7280' }}>
                      Índex Social
                    </Typography>
                    <Typography variant="h4" sx={{ fontWeight: 700, color: '#3b82f6' }}>
                      {((globalDecision.social_index || 0) * 100).toFixed(0)}%
                    </Typography>
                  </Paper>
                </Grid>
              </Grid>
            </CardContent>
          </Card>

          {/* Anàlisi Detallada */}
          <Card
            sx={{
              mb: 3,
              background: 'linear-gradient(135deg, #FFFFFF 0%, #FAFAFA 100%)',
              border: '1px solid #E0E0E0',
              borderRadius: 2,
            }}
          >
            <CardContent>
              <Typography 
                variant="h6" 
                sx={{ 
                  fontWeight: 600, 
                  mb: 2, 
                  color: '#0A0A0A',
                  fontFamily: '"Georgia", "Times New Roman", serif',
                }}
              >
                Anàlisi Detallada
              </Typography>
              <Paper
                sx={{
                  p: 3,
                  backgroundColor: '#FAFAFA',
                  borderRadius: 2,
                  maxHeight: 400,
                  overflow: 'auto',
                }}
              >
                <Typography
                  variant="body2"
                  component="pre"
                  sx={{
                    fontFamily: 'monospace',
                    fontSize: '0.875rem',
                    color: '#4b5563',
                    whiteSpace: 'pre-wrap',
                  }}
                >
                  {unifiedAnalysis.executive_summary || 'No disponible'}
                </Typography>
              </Paper>
            </CardContent>
          </Card>

          {/* Visualitzacions */}
          {visualization && Object.keys(visualization).length > 0 && (
            <Grid container spacing={3}>
              {/* Radar Chart de Riscs */}
              <Grid item xs={12} md={6}>
                <Card
                  sx={{
                    background: 'linear-gradient(135deg, #ffffff 0%, #f9fafb 100%)',
                    border: '1px solid rgba(0, 0, 0, 0.05)',
                    height: '100%',
                  }}
                >
                  <CardContent>
                    <Typography variant="h6" sx={{ fontWeight: 600, mb: 3, color: '#1a1f3a' }}>
                      Anàlisi de Riscs (Radar)
                    </Typography>
                    <ResponsiveContainer width="100%" height={300}>
                      <RadarChart data={riskRadarData}>
                        <PolarGrid stroke="#e5e7eb" />
                        <PolarAngleAxis dataKey="category" stroke="#6b7280" tick={{ fontSize: 12 }} />
                        <PolarRadiusAxis angle={90} domain={[0, 100]} stroke="#6b7280" />
                        <Radar
                          name="Risc"
                          dataKey="value"
                          stroke="#ef4444"
                          fill="#ef4444"
                          fillOpacity={0.6}
                        />
                        <Tooltip
                          contentStyle={{
                            backgroundColor: '#ffffff',
                            border: '1px solid #e5e7eb',
                            borderRadius: 8,
                          }}
                          formatter={(value) => `${value.toFixed(1)}%`}
                        />
                      </RadarChart>
                    </ResponsiveContainer>
                  </CardContent>
                </Card>
              </Grid>

              {/* Fonts Analitzades */}
              <Grid item xs={12} md={6}>
                <Card
                  sx={{
                    background: 'linear-gradient(135deg, #ffffff 0%, #f9fafb 100%)',
                    border: '1px solid rgba(0, 0, 0, 0.05)',
                    height: '100%',
                  }}
                >
                  <CardContent>
                    <Typography variant="h6" sx={{ fontWeight: 600, mb: 3, color: '#1a1f3a' }}>
                      Fonts Analitzades
                    </Typography>
                    <ResponsiveContainer width="100%" height={300}>
                      <BarChart data={sourcesData}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                        <XAxis dataKey="name" stroke="#6b7280" />
                        <YAxis stroke="#6b7280" />
                        <Tooltip
                          contentStyle={{
                            backgroundColor: '#ffffff',
                            border: '1px solid #e5e7eb',
                            borderRadius: 8,
                          }}
                        />
                        <Bar dataKey="value" fill="#ff6b35" radius={[4, 4, 0, 0]} />
                      </BarChart>
                    </ResponsiveContainer>
                  </CardContent>
                </Card>
              </Grid>
            </Grid>
          )}

          {/* Mapa Geogràfic Geopolític */}
          {unifiedAnalysis.geopolitical_analysis?.location?.primary_country && (
            <Grid container spacing={3} sx={{ mt: 2 }}>
              <Grid item xs={12}>
                <Card
                  sx={{
                    background: 'linear-gradient(135deg, #ffffff 0%, #f9fafb 100%)',
                    border: '1px solid rgba(0, 0, 0, 0.05)',
                  }}
                >
                  <CardContent>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 3 }}>
                      <PublicIcon sx={{ color: '#ff6b35' }} />
                      <Typography variant="h6" sx={{ fontWeight: 600, color: '#1a1f3a' }}>
                        Visualització Geogràfica Geopolítica
                      </Typography>
                    </Box>
                    <GeopoliticalMap
                      countries={[
                        {
                          name: unifiedAnalysis.geopolitical_analysis.location.primary_country,
                          value: 1,
                        },
                      ]}
                      height={400}
                    />
                  </CardContent>
                </Card>
              </Grid>
            </Grid>
          )}

          {/* Anàlisis Individuals */}
          <Grid container spacing={3} sx={{ mt: 2 }}>
            <Grid item xs={12} md={6}>
              <Card
                sx={{
                  background: 'linear-gradient(135deg, #ffffff 0%, #f9fafb 100%)',
                  border: '1px solid rgba(0, 0, 0, 0.05)',
                }}
              >
                <CardContent>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
                    <PublicIcon sx={{ color: '#f59e0b' }} />
                    <Typography variant="h6" sx={{ fontWeight: 600, color: '#1a1f3a' }}>
                      Anàlisi Geopolítica
                    </Typography>
                  </Box>
                  {unifiedAnalysis.geopolitical_analysis && (
                    <Box>
                      <Typography variant="body2" sx={{ color: '#6b7280', mb: 1 }}>
                        País: {unifiedAnalysis.geopolitical_analysis.location?.primary_country || 'N/A'}
                      </Typography>
                      <Typography variant="body2" sx={{ color: '#6b7280', mb: 1 }}>
                        Índex: {((unifiedAnalysis.geopolitical_analysis.geopolitical_index || 0) * 100).toFixed(0)}%
                      </Typography>
                      <Typography variant="body2" sx={{ color: '#6b7280' }}>
                        Tensió: {unifiedAnalysis.geopolitical_analysis.tension_analysis?.tension_level || 'N/A'}
                      </Typography>
                    </Box>
                  )}
                </CardContent>
              </Card>
            </Grid>

            <Grid item xs={12} md={6}>
              <Card
                sx={{
                  background: 'linear-gradient(135deg, #ffffff 0%, #f9fafb 100%)',
                  border: '1px solid rgba(0, 0, 0, 0.05)',
                }}
              >
                <CardContent>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
                    <PeopleIcon sx={{ color: '#3b82f6' }} />
                    <Typography variant="h6" sx={{ fontWeight: 600, color: '#1a1f3a' }}>
                      Anàlisi Social
                    </Typography>
                  </Box>
                  {unifiedAnalysis.social_analysis && (
                    <Box>
                      <Typography variant="body2" sx={{ color: '#6b7280', mb: 1 }}>
                        Sentiment: {unifiedAnalysis.social_analysis.social_sentiment?.overall_sentiment || 'N/A'}
                      </Typography>
                      <Typography variant="body2" sx={{ color: '#6b7280', mb: 1 }}>
                        Índex: {((unifiedAnalysis.social_analysis.social_index || 0) * 100).toFixed(0)}%
                      </Typography>
                      <Typography variant="body2" sx={{ color: '#6b7280' }}>
                        Moviments: {unifiedAnalysis.social_analysis.social_movements?.total_movements || 0}
                      </Typography>
                    </Box>
                  )}
                </CardContent>
              </Card>
            </Grid>
          </Grid>
        </>
      ) : (
        <Alert severity="info">
          No hi ha anàlisi unificada disponible. Fes clic a "Generar Anàlisi Unificada" per començar.
        </Alert>
      )}
    </Box>
  );
}

export default UnifiedAnalysisTab;

