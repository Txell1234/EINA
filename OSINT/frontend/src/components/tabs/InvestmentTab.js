import React from 'react';
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
  alpha,
} from '@mui/material';
import TrendingUpIcon from '@mui/icons-material/TrendingUp';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Radar,
  LineChart,
  Line,
  Legend,
} from 'recharts';
import { analyzeInvestment } from '../../services/api';

const COLORS = ['#E3120B', '#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6'];

function InvestmentTab({ caseId, caseData }) {
  const queryClient = useQueryClient();

  const analyzeMutation = useMutation(() => analyzeInvestment(caseId), {
    onSuccess: () => {
      queryClient.invalidateQueries(['case', caseId]);
    },
  });

  const recommendations = caseData?.investment_recommendations || [];
  const latestRecommendation = recommendations.length > 0 ? recommendations[recommendations.length - 1] : null;
  const visualizationData = latestRecommendation?.visualization_data || latestRecommendation?.osint_factors?.visualization_data || {};

  const getRecommendationColor = (type) => {
    switch (type) {
      case 'buy':
        return 'success';
      case 'sell':
        return 'error';
      case 'hold':
        return 'warning';
      case 'avoid':
        return 'error';
      default:
        return 'default';
    }
  };

  const getRiskColor = (level) => {
    switch (level) {
      case 'low':
        return 'success';
      case 'medium':
        return 'warning';
      case 'high':
        return 'error';
      default:
        return 'default';
    }
  };

  // Preparar dades per gràfics
  const riskBreakdownData = visualizationData.risk_breakdown
    ? Object.entries(visualizationData.risk_breakdown).map(([key, value]) => ({
        name: key.charAt(0).toUpperCase() + key.slice(1),
        value: value,
      }))
    : [];

  const opportunityBreakdownData = visualizationData.opportunity_breakdown
    ? Object.entries(visualizationData.opportunity_breakdown).map(([key, value]) => ({
        name: key.charAt(0).toUpperCase() + key.slice(1),
        value: value,
      }))
    : [];

  const scoresData = visualizationData.scores
    ? [
        { name: 'Risc', value: visualizationData.scores.risk * 100 },
        { name: 'Oportunitat', value: visualizationData.scores.opportunity * 100 },
      ]
    : [];

  const radarData = latestRecommendation
    ? [
        {
          category: 'Risc Geopolític',
          value: (visualizationData.risk_breakdown?.geopolitical || 0) * 10,
          fullMark: 100,
        },
        {
          category: 'Risc Polític',
          value: (visualizationData.risk_breakdown?.political || 0) * 10,
          fullMark: 100,
        },
        {
          category: 'Oportunitat Creixement',
          value: (visualizationData.opportunity_breakdown?.growth || 0) * 10,
          fullMark: 100,
        },
        {
          category: 'Oportunitat Innovació',
          value: (visualizationData.opportunity_breakdown?.innovation || 0) * 10,
          fullMark: 100,
        },
        {
          category: 'Estabilitat',
          value: (visualizationData.opportunity_breakdown?.stability || 0) * 10,
          fullMark: 100,
        },
      ]
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
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <Typography variant="h6" sx={{ fontWeight: 600, color: '#1a1f3a' }}>
              Recomanacions d'Inversió
            </Typography>
            <Button
              variant="contained"
              startIcon={<TrendingUpIcon />}
              onClick={() => analyzeMutation.mutate()}
              disabled={analyzeMutation.isLoading || !caseData?.osint_data?.length}
              sx={{
                backgroundColor: '#E3120B',
                '&:hover': {
                  backgroundColor: '#cc5529',
                },
                textTransform: 'none',
                fontWeight: 500,
              }}
            >
              {analyzeMutation.isLoading ? 'Analitzant...' : 'Generar Recomanació'}
            </Button>
          </Box>
          {!caseData?.osint_data?.length && (
            <Alert severity="warning" sx={{ mt: 2 }}>
              Necessites recopilar dades OSINT abans de poder generar recomanacions d'inversió.
            </Alert>
          )}
        </CardContent>
      </Card>

      {analyzeMutation.isError && (
        <Alert severity="error" sx={{ mb: 2 }}>
          Error generant recomanació d'inversió
        </Alert>
      )}

      {latestRecommendation ? (
        <>
          {/* Recomanació Principal */}
          <Grid container spacing={3} sx={{ mb: 3 }}>
            <Grid item xs={12}>
              <Card
                sx={{
                  background: 'linear-gradient(135deg, #ffffff 0%, #f9fafb 100%)',
                  border: '1px solid rgba(0, 0, 0, 0.05)',
                }}
              >
                <CardContent>
                  <Box sx={{ display: 'flex', gap: 2, mb: 3, flexWrap: 'wrap' }}>
                    <Chip
                      label={`Recomanació: ${latestRecommendation.recommendation_type.toUpperCase()}`}
                      color={getRecommendationColor(latestRecommendation.recommendation_type)}
                      size="large"
                      sx={{ fontWeight: 600 }}
                    />
                    <Chip
                      label={`Confiança: ${(latestRecommendation.confidence * 100).toFixed(0)}%`}
                      sx={{
                        backgroundColor: alpha('#3b82f6', 0.1),
                        color: '#3b82f6',
                        fontWeight: 600,
                      }}
                      size="large"
                    />
                    <Chip
                      label={`Risc: ${latestRecommendation.risk_level}`}
                      color={getRiskColor(latestRecommendation.risk_level)}
                      size="large"
                      sx={{ fontWeight: 600 }}
                    />
                    <Chip
                      label={`Horitzó: ${latestRecommendation.time_horizon}`}
                      variant="outlined"
                      size="large"
                      sx={{ fontWeight: 500 }}
                    />
                    {latestRecommendation.sector && (
                      <Chip
                        label={`Sector: ${latestRecommendation.sector}`}
                        variant="outlined"
                        size="large"
                        sx={{ fontWeight: 500 }}
                      />
                    )}
                    {latestRecommendation.asset_type && (
                      <Chip
                        label={`Actiu: ${latestRecommendation.asset_type}`}
                        variant="outlined"
                        size="large"
                        sx={{ fontWeight: 500 }}
                      />
                    )}
                  </Box>

                  <Typography variant="h6" gutterBottom sx={{ fontWeight: 600, color: '#1a1f3a' }}>
                    Raonament
                  </Typography>
                  <Typography variant="body1" sx={{ mb: 3, whiteSpace: 'pre-line', color: '#4b5563' }}>
                    {latestRecommendation.reasoning}
                  </Typography>

                  {latestRecommendation.target && (
                    <Box sx={{ mt: 2 }}>
                      <Typography variant="subtitle2" sx={{ color: '#6b7280', mb: 1 }}>
                        Objectiu d'Inversió
                      </Typography>
                      <Typography variant="body1" sx={{ fontWeight: 500, color: '#1a1f3a' }}>
                        {latestRecommendation.target}
                      </Typography>
                    </Box>
                  )}
                </CardContent>
              </Card>
            </Grid>
          </Grid>

          {/* Visualitzacions */}
          {visualizationData && Object.keys(visualizationData).length > 0 && (
            <Grid container spacing={3}>
              {/* Gràfic de Scores */}
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
                      Scores de Risc i Oportunitat
                    </Typography>
                    <ResponsiveContainer width="100%" height={300}>
                      <BarChart data={scoresData}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                        <XAxis dataKey="name" stroke="#6b7280" />
                        <YAxis stroke="#6b7280" domain={[0, 100]} />
                        <Tooltip
                          contentStyle={{
                            backgroundColor: '#ffffff',
                            border: '1px solid #e5e7eb',
                            borderRadius: 8,
                          }}
                          formatter={(value) => `${value.toFixed(1)}%`}
                        />
                        <Bar dataKey="value" fill="#E3120B" radius={[4, 4, 0, 0]} />
                      </BarChart>
                    </ResponsiveContainer>
                  </CardContent>
                </Card>
              </Grid>

              {/* Desglossament de Riscs */}
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
                      Desglossament de Riscs
                    </Typography>
                    <ResponsiveContainer width="100%" height={300}>
                      <BarChart data={riskBreakdownData} layout="vertical">
                        <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                        <XAxis type="number" stroke="#6b7280" />
                        <YAxis dataKey="name" type="category" stroke="#6b7280" width={100} />
                        <Tooltip
                          contentStyle={{
                            backgroundColor: '#ffffff',
                            border: '1px solid #e5e7eb',
                            borderRadius: 8,
                          }}
                        />
                        <Bar dataKey="value" fill="#ef4444" radius={[0, 4, 4, 0]} />
                      </BarChart>
                    </ResponsiveContainer>
                  </CardContent>
                </Card>
              </Grid>

              {/* Desglossament d'Oportunitats */}
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
                      Desglossament d'Oportunitats
                    </Typography>
                    <ResponsiveContainer width="100%" height={300}>
                      <BarChart data={opportunityBreakdownData}>
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
                        <Bar dataKey="value" fill="#10b981" radius={[4, 4, 0, 0]} />
                      </BarChart>
                    </ResponsiveContainer>
                  </CardContent>
                </Card>
              </Grid>

              {/* Radar Chart */}
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
                      Anàlisi Radar
                    </Typography>
                    <ResponsiveContainer width="100%" height={300}>
                      <RadarChart data={radarData}>
                        <PolarGrid stroke="#e5e7eb" />
                        <PolarAngleAxis dataKey="category" stroke="#6b7280" tick={{ fontSize: 12 }} />
                        <PolarRadiusAxis angle={90} domain={[0, 100]} stroke="#6b7280" />
                        <Radar
                          name="Valors"
                          dataKey="value"
                          stroke="#E3120B"
                          fill="#E3120B"
                          fillOpacity={0.6}
                        />
                        <Tooltip
                          contentStyle={{
                            backgroundColor: '#ffffff',
                            border: '1px solid #e5e7eb',
                            borderRadius: 8,
                          }}
                        />
                      </RadarChart>
                    </ResponsiveContainer>
                  </CardContent>
                </Card>
              </Grid>
            </Grid>
          )}

          {/* Factors OSINT */}
          {latestRecommendation.osint_factors && (
            <Card
              sx={{
                mt: 3,
                background: 'linear-gradient(135deg, #ffffff 0%, #f9fafb 100%)',
                border: '1px solid rgba(0, 0, 0, 0.05)',
              }}
            >
              <CardContent>
                <Typography variant="h6" gutterBottom sx={{ fontWeight: 600, color: '#1a1f3a' }}>
                  Factors OSINT Analitzats
                </Typography>
                <Box sx={{ p: 2, bgcolor: '#f9fafb', borderRadius: 2, mt: 2 }}>
                  <Typography variant="body2" component="pre" sx={{ fontSize: '0.875rem', color: '#4b5563' }}>
                    {JSON.stringify(latestRecommendation.osint_factors, null, 2)}
                  </Typography>
                </Box>
              </CardContent>
            </Card>
          )}
        </>
      ) : (
        <Alert severity="info">
          No hi ha recomanacions d'inversió disponibles. Fes clic a "Generar Recomanació" per començar.
        </Alert>
      )}
    </Box>
  );
}

export default InvestmentTab;
