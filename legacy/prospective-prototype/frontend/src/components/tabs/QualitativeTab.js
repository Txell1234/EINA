import React, { useState } from 'react';
import { useMutation, useQueryClient } from 'react-query';
import {
  Box,
  Button,
  TextField,
  Card,
  CardContent,
  Typography,
  Grid,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Alert,
  Checkbox,
  FormControlLabel,
  FormGroup,
} from '@mui/material';
import AnalyticsIcon from '@mui/icons-material/Analytics';
import { getKPIs, createKPI, qualitativeAnalyze } from '../../services/api';
import { useQuery } from 'react-query';

function QualitativeTab({ caseId, caseData, setSnackbar }) {
  const [premise, setPremise] = useState('');
  const [reasoningFramework, setReasoningFramework] = useState('deductive');
  const [selectedKPIs, setSelectedKPIs] = useState([]);
  const [newKPI, setNewKPI] = useState({
    name: '',
    description: '',
    variable_type: 'quantitative',
    value: '',
    reasoning: '',
  });

  const queryClient = useQueryClient();

  const { data: kpisData } = useQuery(
    ['kpis', caseId],
    () => getKPIs(caseId),
    {
      select: (response) => response.data,
    }
  );

  const kpis = kpisData || [];

  const createKPIMutation = useMutation(createKPI, {
    onSuccess: () => {
      queryClient.invalidateQueries(['kpis', caseId]);
      setNewKPI({ name: '', description: '', variable_type: 'quantitative', value: '', reasoning: '' });
      setSnackbar?.({ open: true, message: 'KPI creat', severity: 'success' });
    },
    onError: (e) => setSnackbar?.({ open: true, message: e?.message || 'Error', severity: 'error' }),
  });

  const analyzeMutation = useMutation(qualitativeAnalyze, {
    onSuccess: () => {
      queryClient.invalidateQueries(['case', caseId]);
      setSnackbar?.({ open: true, message: 'Anàlisi qualitatiu completat', severity: 'success' });
    },
    onError: (e) => setSnackbar?.({ open: true, message: e?.message || 'Error', severity: 'error' }),
  });

  const handleCreateKPI = () => {
    const kpiData = {
      case_id: parseInt(caseId),
      ...newKPI,
      value: newKPI.variable_type === 'quantitative' ? parseFloat(newKPI.value) : null,
      qualitative_value: newKPI.variable_type === 'qualitative' ? newKPI.value : null,
    };
    createKPIMutation.mutate(kpiData);
  };

  const handleAnalyze = () => {
    if (!premise.trim() || selectedKPIs.length === 0) return;
    analyzeMutation.mutate({
      case_id: parseInt(caseId),
      premise: premise,
      reasoning_framework: reasoningFramework,
      kpi_ids: selectedKPIs,
    });
  };

  const handleKPIChange = (kpiId) => {
    setSelectedKPIs((prev) =>
      prev.includes(kpiId) ? prev.filter((id) => id !== kpiId) : [...prev, kpiId]
    );
  };

  const qualitativeAnalysis = caseData?.qualitative_analysis || [];
  const latestAnalysis = qualitativeAnalysis.length > 0 ? qualitativeAnalysis[qualitativeAnalysis.length - 1] : null;

  return (
    <Box>
      <Grid container spacing={3}>
        <Grid item xs={12} md={6}>
          <Card sx={{ mb: 3 }}>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Crear KPI
              </Typography>
              <TextField
                fullWidth
                label="Nom del KPI"
                value={newKPI.name}
                onChange={(e) => setNewKPI({ ...newKPI, name: e.target.value })}
                sx={{ mb: 2 }}
              />
              <TextField
                fullWidth
                label="Descripció"
                value={newKPI.description}
                onChange={(e) => setNewKPI({ ...newKPI, description: e.target.value })}
                sx={{ mb: 2 }}
              />
              <FormControl fullWidth sx={{ mb: 2 }}>
                <InputLabel>Tipus</InputLabel>
                <Select
                  value={newKPI.variable_type}
                  onChange={(e) => setNewKPI({ ...newKPI, variable_type: e.target.value })}
                  label="Tipus"
                >
                  <MenuItem value="quantitative">Quantitatiu</MenuItem>
                  <MenuItem value="qualitative">Qualitatiu</MenuItem>
                </Select>
              </FormControl>
              <TextField
                fullWidth
                label={newKPI.variable_type === 'quantitative' ? 'Valor' : 'Valor Qualitatiu'}
                value={newKPI.value}
                onChange={(e) => setNewKPI({ ...newKPI, value: e.target.value })}
                sx={{ mb: 2 }}
              />
              <TextField
                fullWidth
                label="Raonament"
                multiline
                rows={3}
                value={newKPI.reasoning}
                onChange={(e) => setNewKPI({ ...newKPI, reasoning: e.target.value })}
                sx={{ mb: 2 }}
              />
              <Button
                variant="contained"
                onClick={handleCreateKPI}
                disabled={!newKPI.name || createKPIMutation.isLoading}
              >
                Crear KPI
              </Button>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={6}>
          <Card sx={{ mb: 3 }}>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Anàlisi Qualitatiu
              </Typography>
              <TextField
                fullWidth
                label="Premissa"
                multiline
                rows={3}
                value={premise}
                onChange={(e) => setPremise(e.target.value)}
                sx={{ mb: 2 }}
              />
              <FormControl fullWidth sx={{ mb: 2 }}>
                <InputLabel>Framework de Raonament</InputLabel>
                <Select
                  value={reasoningFramework}
                  onChange={(e) => setReasoningFramework(e.target.value)}
                  label="Framework de Raonament"
                >
                  <MenuItem value="deductive">Deductiu</MenuItem>
                  <MenuItem value="inductive">Inductiu</MenuItem>
                  <MenuItem value="abductive">Abductiu</MenuItem>
                  <MenuItem value="causal">Causal</MenuItem>
                </Select>
              </FormControl>

              <Typography variant="subtitle2" gutterBottom>
                Seleccionar KPIs ({selectedKPIs.length} seleccionats)
              </Typography>
              <FormGroup>
                {kpis.map((kpi) => (
                  <FormControlLabel
                    key={kpi.id}
                    control={
                      <Checkbox
                        checked={selectedKPIs.includes(kpi.id)}
                        onChange={() => handleKPIChange(kpi.id)}
                      />
                    }
                    label={`${kpi.name} (${kpi.variable_type})`}
                  />
                ))}
              </FormGroup>

              {kpis.length === 0 && (
                <Alert severity="info" sx={{ mt: 2 }}>
                  Crea KPIs abans de realitzar anàlisi qualitatiu.
                </Alert>
              )}

              <Button
                variant="contained"
                startIcon={<AnalyticsIcon />}
                onClick={handleAnalyze}
                disabled={!premise.trim() || selectedKPIs.length === 0 || analyzeMutation.isLoading}
                fullWidth
                sx={{ mt: 2 }}
              >
                Analitzar
              </Button>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {latestAnalysis && (
        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              Última Anàlisi Qualitatiu
            </Typography>
            <Typography variant="body1" sx={{ mb: 2 }}>
              <strong>Premissa:</strong> {latestAnalysis.premise}
            </Typography>
            <Typography variant="body1" sx={{ mb: 2 }}>
              <strong>Framework:</strong> {latestAnalysis.reasoning_framework}
            </Typography>
            {latestAnalysis.analysis_result && (
              <Box sx={{ mt: 2 }}>
                <Typography variant="subtitle1" gutterBottom>
                  Resultats
                </Typography>
                <Box sx={{ p: 2, bgcolor: 'grey.100', borderRadius: 1 }}>
                  <Typography variant="body2" component="pre" sx={{ fontSize: '0.875rem' }}>
                    {JSON.stringify(latestAnalysis.analysis_result, null, 2)}
                  </Typography>
                </Box>
              </Box>
            )}
            {latestAnalysis.conclusion && (
              <Box sx={{ mt: 2 }}>
                <Typography variant="subtitle1" gutterBottom>
                  Conclusió
                </Typography>
                <Typography variant="body2">{latestAnalysis.conclusion}</Typography>
              </Box>
            )}
          </CardContent>
        </Card>
      )}
    </Box>
  );
}

export default QualitativeTab;

