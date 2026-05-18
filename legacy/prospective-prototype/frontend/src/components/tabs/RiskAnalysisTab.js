import React, { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from 'react-query';
import {
  Box,
  Button,
  TextField,
  Card,
  CardContent,
  Typography,
  Grid,
  Alert,
  Chip,
  alpha,
  LinearProgress,
  IconButton,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
} from '@mui/material';
import AddIcon from '@mui/icons-material/Add';
import DeleteIcon from '@mui/icons-material/Delete';
import PsychologyIcon from '@mui/icons-material/Psychology';
import RuleIcon from '@mui/icons-material/Rule';
import {
  getRiskConcepts,
  createRiskConcept,
  deleteRiskConcept,
  analyzeRisk,
  analyzeRiskAI,
} from '../../services/api';

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

function getScoreColor(score) {
  if (score >= 0.7) return EIU.red;
  if (score >= 0.4) return EIU.warning;
  return EIU.success;
}

function RiskAnalysisTab({ caseId, caseData, setSnackbar }) {
  const [newConcept, setNewConcept] = useState({ name: '', weight: 1, dimension: '' });
  const queryClient = useQueryClient();

  const { data: conceptsData } = useQuery(
    ['risk-concepts', caseId],
    () => getRiskConcepts(caseId),
    { select: (r) => r.data, enabled: !!caseId }
  );
  const concepts = conceptsData || [];

  const createMutation = useMutation(
    () => createRiskConcept(caseId, { name: newConcept.name, weight: newConcept.weight, dimension: newConcept.dimension || null }),
    { onSuccess: () => { queryClient.invalidateQueries(['risk-concepts', caseId]); setNewConcept({ name: '', weight: 1, dimension: '' }); setSnackbar?.({ open: true, message: 'Concepte afegit', severity: 'success' }); } }
  );
  const deleteMutation = useMutation(
    (conceptId) => deleteRiskConcept(caseId, conceptId),
    { onSuccess: () => queryClient.invalidateQueries(['risk-concepts', caseId]) }
  );
  const analyzeMutation = useMutation(() => analyzeRisk(caseId), {
    onSuccess: () => { queryClient.invalidateQueries(['case', caseId]); setSnackbar?.({ open: true, message: 'Anàlisi de risc completada', severity: 'success' }); },
    onError: (e) => setSnackbar?.({ open: true, message: e?.message || 'Error', severity: 'error' }),
  });
  const analyzeAIMutation = useMutation(() => analyzeRiskAI(caseId), {
    onSuccess: () => { queryClient.invalidateQueries(['case', caseId]); setSnackbar?.({ open: true, message: 'Anàlisi de risc amb IA completada', severity: 'success' }); },
    onError: (e) => setSnackbar?.({ open: true, message: e?.message || 'Error', severity: 'error' }),
  });

  const riskAnalyses = caseData?.risk_analyses || [];
  const latest = riskAnalyses.length > 0 ? riskAnalyses[riskAnalyses.length - 1] : null;
  const results = latest?.results || {};
  const resultConcepts = results.concepts || [];

  const hasOsint = (caseData?.osint_data?.length || 0) > 0;

  return (
    <Box>
      <Card sx={{ mb: 3, background: EIU.bgCard, border: `1px solid ${EIU.border}`, borderRadius: 2 }}>
        <CardContent>
          <Typography variant="h6" sx={{ fontWeight: 600, color: EIU.black, fontFamily: EIU.serif, mb: 2 }}>
            Configuració de conceptes de risc
          </Typography>
          <Grid container spacing={2} alignItems="center" sx={{ mb: 2 }}>
            <Grid item xs={12} sm={4}>
              <TextField
                fullWidth
                size="small"
                label="Concepte"
                value={newConcept.name}
                onChange={(e) => setNewConcept({ ...newConcept, name: e.target.value })}
                placeholder="Ex: sancions, conflicte"
              />
            </Grid>
            <Grid item xs={12} sm={2}>
              <TextField
                fullWidth
                size="small"
                type="number"
                label="Pes"
                value={newConcept.weight}
                onChange={(e) => setNewConcept({ ...newConcept, weight: parseFloat(e.target.value) || 1 })}
                inputProps={{ min: 0, max: 1, step: 0.1 }}
              />
            </Grid>
            <Grid item xs={12} sm={2}>
              <TextField
                fullWidth
                size="small"
                label="Dimensió"
                value={newConcept.dimension}
                onChange={(e) => setNewConcept({ ...newConcept, dimension: e.target.value })}
                placeholder="Ex: geopolitic"
              />
            </Grid>
            <Grid item xs={12} sm={2}>
              <Button
                variant="outlined"
                startIcon={<AddIcon />}
                onClick={() => createMutation.mutate()}
                disabled={!newConcept.name.trim() || createMutation.isLoading}
              >
                Afegir
              </Button>
            </Grid>
          </Grid>
          {concepts.length > 0 && (
            <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
              {concepts.map((c) => (
                <Chip
                  key={c.id}
                  label={`${c.name} (${c.weight})`}
                  onDelete={() => deleteMutation.mutate(c.id)}
                  size="small"
                  sx={{ mb: 1 }}
                />
              ))}
            </Box>
          )}
        </CardContent>
      </Card>

      <Card sx={{ mb: 3, background: EIU.bgCard, border: `1px solid ${EIU.border}`, borderRadius: 2 }}>
        <CardContent>
          <Typography variant="h6" sx={{ fontWeight: 600, color: EIU.black, fontFamily: EIU.serif, mb: 2 }}>
            Anàlisi de risc
          </Typography>
          {!hasOsint && (
            <Alert severity="warning" sx={{ mb: 2 }}>Cal recopilar dades OSINT abans d’analitzar el risc.</Alert>
          )}
          <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap' }}>
            <Button
              variant="contained"
              startIcon={<RuleIcon />}
              onClick={() => analyzeMutation.mutate()}
              disabled={!hasOsint || analyzeMutation.isLoading}
              sx={{ backgroundColor: EIU.red, '&:hover': { backgroundColor: EIU.redDark }, textTransform: 'none' }}
            >
              {analyzeMutation.isLoading ? 'Analitzant…' : 'Analitzar sense IA'}
            </Button>
            <Button
              variant="contained"
              startIcon={<PsychologyIcon />}
              onClick={() => analyzeAIMutation.mutate()}
              disabled={!hasOsint || analyzeAIMutation.isLoading}
              sx={{ backgroundColor: EIU.gray, '&:hover': { backgroundColor: EIU.black }, textTransform: 'none' }}
            >
              {analyzeAIMutation.isLoading ? 'Analitzant…' : 'Analitzar amb IA'}
            </Button>
          </Box>
          {(analyzeMutation.isLoading || analyzeAIMutation.isLoading) && (
            <LinearProgress sx={{ mt: 2, height: 4, borderRadius: 2 }} />
          )}
        </CardContent>
      </Card>

      {resultConcepts.length > 0 && (
        <Card sx={{ background: EIU.bgCard, border: `1px solid ${EIU.border}`, borderRadius: 2 }}>
          <CardContent>
            <Typography variant="h6" sx={{ fontWeight: 600, color: EIU.black, fontFamily: EIU.serif, mb: 2 }}>
              Resultats ({latest?.mode === 'ai' ? 'amb IA' : 'sense IA'})
            </Typography>
            <Box sx={{ mb: 2 }}>
              <Chip label={`Score global: ${((results.overall_score ?? 0) * 100).toFixed(0)}%`} sx={{ fontWeight: 600, backgroundColor: alpha(EIU.red, 0.1), color: EIU.red }} />
            </Box>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell><strong>Concepte</strong></TableCell>
                  <TableCell><strong>Score</strong></TableCell>
                  <TableCell><strong>Evidències</strong></TableCell>
                  <TableCell><strong>Dimensió</strong></TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {resultConcepts.map((r, i) => (
                  <TableRow key={i}>
                    <TableCell>{r.concept}</TableCell>
                    <TableCell>
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        <LinearProgress
                          variant="determinate"
                          value={Math.min(100, (r.score ?? 0) * 100)}
                          sx={{ width: 80, height: 8, borderRadius: 1, backgroundColor: alpha(EIU.red, 0.1), '& .MuiLinearProgress-bar': { backgroundColor: getScoreColor(r.score ?? 0) } }}
                        />
                        <Typography variant="body2" sx={{ color: getScoreColor(r.score ?? 0), fontWeight: 600 }}>{((r.score ?? 0) * 100).toFixed(0)}%</Typography>
                      </Box>
                    </TableCell>
                    <TableCell>{r.evidence_count ?? 0}</TableCell>
                    <TableCell>{r.dimension ?? '—'}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}

      {resultConcepts.length === 0 && latest && (
        <Alert severity="info">No s’han trobat conceptes amb evidències. Afegiu conceptes de risc i torneu a analitzar.</Alert>
      )}
    </Box>
  );
}

export default RiskAnalysisTab;
