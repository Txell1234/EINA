import React, { useMemo } from 'react';
import { useMutation, useQuery, useQueryClient } from 'react-query';
import {
  Box,
  Button,
  Card,
  CardContent,
  Typography,
  Grid,
  Alert,
  LinearProgress,
  Chip,
  alpha,
  Divider,
  List,
  ListItem,
  ListItemText,
} from '@mui/material';
import PsychologyIcon from '@mui/icons-material/Psychology';
import TrendingUpIcon from '@mui/icons-material/TrendingUp';
import { analyzeWithAI, getAIStatus } from '../../services/api';

const EIU = {
  black: '#0A0A0A',
  red: '#E3120B',
  redDark: '#B00E08',
  gray: '#4A4A4A',
  border: '#E0E0E0',
  bgCard: 'linear-gradient(135deg, #FFFFFF 0%, #FAFAFA 100%)',
  serif: '"Georgia", "Times New Roman", serif',
  success: '#10b981',
  warning: '#f59e0b',
};

function normalizeConcepts(results) {
  if (!results) return [];
  const raw = results.concepts || results.concept_list || [];
  if (!Array.isArray(raw)) return [];
  return raw.map((c) => ({
    concept: typeof c === 'string' ? c : (c.concept ?? c.name ?? c.text ?? c.label ?? JSON.stringify(c)),
    relevance: typeof c === 'object' && typeof c.relevance === 'number' ? c.relevance : (c.score ?? c.value ?? 0.5),
  })).filter((c) => c.concept);
}

function normalizePredictions(results) {
  if (!results?.predictions) return [];
  const pred = results.predictions;
  if (Array.isArray(pred)) return pred;
  return Object.entries(pred).map(([key, value]) => ({
    key,
    trend: value?.trend ?? value?.direction ?? '—',
    confidence: typeof value?.confidence === 'number' ? value.confidence : 0,
    reasoning: value?.reasoning ?? value?.summary ?? '',
  }));
}

function AIAnalysisTab({ caseId, caseData, setSnackbar }) {
  const queryClient = useQueryClient();
  const { data: aiStatus } = useQuery(['ai-status'], () => getAIStatus().then((r) => r.data), { staleTime: 60000 });

  const analyzeMutation = useMutation(() => analyzeWithAI(caseId), {
    onSuccess: () => { queryClient.invalidateQueries(['case', caseId]); setSnackbar?.({ open: true, message: 'Anàlisi completada', severity: 'success' }); },
    onError: (e) => setSnackbar?.({ open: true, message: e?.message || 'Error anàlisi IA', severity: 'error' }),
  });

  const aiAnalysis = caseData?.ai_analysis || [];
  const latestAnalysis = aiAnalysis.length > 0 ? aiAnalysis[aiAnalysis.length - 1] : null;
  const results = latestAnalysis?.results || {};

  const concepts = useMemo(() => normalizeConcepts(results), [results]);
  const predictions = useMemo(() => normalizePredictions(results), [results]);

  const hasOsint = (caseData?.osint_data?.length || 0) > 0;

  return (
    <Box>
      <Card
        sx={{
          mb: 3,
          background: EIU.bgCard,
          border: `1px solid ${EIU.border}`,
          borderRadius: 2,
          boxShadow: '0px 2px 8px rgba(0,0,0,0.08)',
        }}
      >
        <CardContent>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 2 }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <Typography variant="h6" sx={{ fontWeight: 600, color: EIU.black, fontFamily: EIU.serif }}>
                Anàlisi amb intel·ligència artificial
              </Typography>
              {aiStatus && !aiStatus.openai_configured && <Chip label="Mode demo" size="small" variant="outlined" sx={{ fontSize: '0.7rem' }} />}
            </Box>
            <Button
              variant="contained"
              startIcon={<PsychologyIcon />}
              onClick={() => analyzeMutation.mutate()}
              disabled={analyzeMutation.isLoading || !hasOsint}
              sx={{
                backgroundColor: EIU.red,
                textTransform: 'none',
                fontWeight: 600,
                borderRadius: 1,
                '&:hover': { backgroundColor: EIU.redDark },
              }}
            >
              {analyzeMutation.isLoading ? 'Analitzant…' : 'Analitzar conceptes'}
            </Button>
          </Box>
          {!hasOsint && (
            <Alert severity="warning" sx={{ mt: 2 }}>
              Cal recopilar dades OSINT abans d’executar l’anàlisi de conceptes.
            </Alert>
          )}
        </CardContent>
      </Card>

      {analyzeMutation.isError && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => analyzeMutation.reset()}>
          {analyzeMutation.error?.message || 'Error en l’anàlisi IA'}
        </Alert>
      )}

      {latestAnalysis ? (
        <Grid container spacing={3}>
          {/* Confiança i tipus */}
          <Grid item xs={12}>
            <Card sx={{ background: EIU.bgCard, border: `1px solid ${EIU.border}`, borderRadius: 2 }}>
              <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, flexWrap: 'wrap' }}>
                  <Chip
                    label={`Confiança: ${((latestAnalysis.confidence_score ?? 0) * 100).toFixed(0)}%`}
                    sx={{
                      fontWeight: 600,
                      backgroundColor: alpha(EIU.red, 0.1),
                      color: EIU.red,
                      border: `1px solid ${alpha(EIU.red, 0.3)}`,
                    }}
                  />
                  {latestAnalysis.analysis_type && (
                    <Chip label={latestAnalysis.analysis_type} size="small" variant="outlined" />
                  )}
                </Box>
              </CardContent>
            </Card>
          </Grid>

          {/* Conceptes identificats */}
          {concepts.length > 0 && (
            <Grid item xs={12} md={6}>
              <Card sx={{ background: EIU.bgCard, border: `1px solid ${EIU.border}`, borderRadius: 2, height: '100%' }}>
                <CardContent>
                  <Typography variant="h6" sx={{ fontWeight: 600, color: EIU.black, fontFamily: EIU.serif, mb: 2 }}>
                    Conceptes identificats
                  </Typography>
                  <List dense disablePadding>
                    {concepts.slice(0, 15).map((item, idx) => (
                      <ListItem key={idx} disablePadding sx={{ py: 0.5, flexDirection: 'column', alignItems: 'stretch' }}>
                        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                          <ListItemText
                            primary={item.concept}
                            primaryTypographyProps={{ fontWeight: 500, color: EIU.black }}
                          />
                          <Chip
                            size="small"
                            label={`${((item.relevance ?? 0) * 100).toFixed(0)}%`}
                            sx={{ fontWeight: 600, backgroundColor: alpha(EIU.red, 0.08), color: EIU.red }}
                          />
                        </Box>
                        <LinearProgress
                          variant="determinate"
                          value={Math.min(100, (item.relevance ?? 0) * 100)}
                          sx={{
                            mt: 0.5,
                            height: 6,
                            borderRadius: 1,
                            backgroundColor: alpha(EIU.red, 0.1),
                            '& .MuiLinearProgress-bar': { backgroundColor: EIU.red },
                          }}
                        />
                      </ListItem>
                    ))}
                  </List>
                </CardContent>
              </Card>
            </Grid>
          )}

          {/* Prediccions / tendències */}
          {predictions.length > 0 && (
            <Grid item xs={12} md={6}>
              <Card sx={{ background: EIU.bgCard, border: `1px solid ${EIU.border}`, borderRadius: 2, height: '100%' }}>
                <CardContent>
                  <Typography variant="h6" sx={{ fontWeight: 600, color: EIU.black, fontFamily: EIU.serif, mb: 2 }}>
                    Prediccions i tendències
                  </Typography>
                  <List dense disablePadding>
                    {predictions.map((p, idx) => (
                      <ListItem key={idx} disablePadding sx={{ flexDirection: 'column', alignItems: 'stretch', py: 1 }}>
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 0.5 }}>
                          <TrendingUpIcon sx={{ color: EIU.gray, fontSize: 20 }} />
                          <Typography variant="subtitle2" sx={{ fontWeight: 600, color: EIU.black }}>
                            {p.key}
                          </Typography>
                          <Chip size="small" label={p.trend} variant="outlined" />
                          <Chip size="small" label={`${(p.confidence * 100).toFixed(0)}%`} sx={{ backgroundColor: alpha(EIU.success, 0.1), color: EIU.success }} />
                        </Box>
                        {p.reasoning && (
                          <Typography variant="body2" sx={{ color: EIU.gray, lineHeight: 1.6 }}>
                            {p.reasoning}
                          </Typography>
                        )}
                        <Divider sx={{ mt: 1 }} />
                      </ListItem>
                    ))}
                  </List>
                </CardContent>
              </Card>
            </Grid>
          )}

          {/* JSON brut (col·lapsat) */}
          <Grid item xs={12}>
            <Card sx={{ background: EIU.bgCard, border: `1px solid ${EIU.border}`, borderRadius: 2 }}>
              <CardContent>
                <Typography variant="subtitle2" sx={{ color: EIU.gray, mb: 1 }}>
                  Dades completes de l’anàlisi
                </Typography>
                <Box sx={{ p: 2, bgcolor: 'grey.100', borderRadius: 1, border: `1px solid ${EIU.border}`, maxHeight: 280, overflow: 'auto' }}>
                  <Typography component="pre" variant="caption" sx={{ fontSize: '0.75rem' }}>
                    {JSON.stringify(latestAnalysis.results || {}, null, 2)}
                  </Typography>
                </Box>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      ) : (
        <Alert severity="info" sx={{ borderRadius: 2 }}>
          Encara no hi ha anàlisi de conceptes. Feu clic a «Analitzar conceptes» després d’haver recopilat dades OSINT.
        </Alert>
      )}
    </Box>
  );
}

export default AIAnalysisTab;
