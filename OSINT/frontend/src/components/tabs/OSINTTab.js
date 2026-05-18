import React, { useState } from 'react';
import { useMutation, useQueryClient, useQuery } from 'react-query';
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
  Chip,
  alpha,
  LinearProgress,
  Collapse,
} from '@mui/material';
import SearchIcon from '@mui/icons-material/Search';
import PublicIcon from '@mui/icons-material/Public';
import ArticleIcon from '@mui/icons-material/Article';
import CodeIcon from '@mui/icons-material/Code';
import DnsIcon from '@mui/icons-material/Dns';
import HistoryIcon from '@mui/icons-material/History';
import PersonIcon from '@mui/icons-material/Person';
import OpenInNewIcon from '@mui/icons-material/OpenInNew';
import { collectOSINT, getOSINTTools } from '../../services/api';
import { format } from 'date-fns';

const EIU = {
  black: '#0A0A0A',
  red: '#E3120B',
  redDark: '#B00E08',
  gray: '#4A4A4A',
  border: '#E0E0E0',
  bgCard: 'linear-gradient(135deg, #FFFFFF 0%, #FAFAFA 100%)',
  serif: '"Georgia", "Times New Roman", serif',
};

const THEMATIC_OPTIONS = [
  { value: '', label: 'Sense temàtica' },
  { value: 'geopolitical', label: 'Geopolítica' },
  { value: 'cyber', label: 'Ciberseguretat' },
  { value: 'brand', label: 'Marca' },
  { value: 'person', label: 'Persona' },
  { value: 'market', label: 'Mercat' },
  { value: 'other', label: 'Altres' },
];

function getOriginalUrl(item) {
  const meta = item?.metadata_info;
  if (meta?.original_url) return meta.original_url;
  const rd = item?.raw_data;
  if (!rd) return null;
  const src = (item?.source || '').toLowerCase();
  if (src.includes('news')) return rd.link ?? rd.articles?.[0]?.link ?? rd.url;
  if (src.includes('reddit')) return rd.data?.url ?? rd.url ?? (rd.data?.permalink ? `https://reddit.com${rd.data.permalink}` : null);
  if (src.includes('sherlock') || src.includes('username')) {
    const res = rd.results ?? rd.accounts ?? {};
    const first = Object.values(res)[0];
    return first?.url ?? first?.link ?? rd.url;
  }
  if (src.includes('github')) return rd.html_url ?? rd.url;
  return rd.url ?? rd.link ?? rd.original_url;
}

const SOURCE_OPTIONS = [
  { value: 'username', label: "Nom d'usuari (Sherlock)", icon: <PersonIcon /> },
  { value: 'sherlock', label: 'Xarxes socials (Sherlock)', icon: <PersonIcon /> },
  { value: 'domain', label: 'Domini (Recon-ng)', icon: <PublicIcon /> },
  { value: 'recon-ng', label: 'Anàlisi domini (Recon-ng)', icon: <PublicIcon /> },
  { value: 'news', label: 'Notícies (Google News)', icon: <ArticleIcon /> },
  { value: 'google_news', label: 'Google News', icon: <ArticleIcon /> },
  { value: 'reddit', label: 'Reddit', icon: <ArticleIcon /> },
  { value: 'github', label: 'GitHub', icon: <CodeIcon /> },
  { value: 'whois', label: 'Whois', icon: <DnsIcon /> },
  { value: 'dns', label: 'DNS', icon: <DnsIcon /> },
  { value: 'wayback', label: 'Wayback Machine', icon: <HistoryIcon /> },
];

function OSINTTab({ caseId, caseData, setSnackbar }) {
  const [query, setQuery] = useState('');
  const [sourceType, setSourceType] = useState('username');
  const [thematic, setThematic] = useState('');
  const [expandedId, setExpandedId] = useState(null);
  const queryClient = useQueryClient();

  const { data: toolsData } = useQuery(['osint-tools'], getOSINTTools, {
    select: (res) => res.data?.tools || [],
    staleTime: 60000,
  });

  const collectMutation = useMutation(collectOSINT, {
    onSuccess: () => {
      queryClient.invalidateQueries(['case', caseId]);
      setQuery('');
      setSnackbar?.({ open: true, message: 'Dades OSINT recopilades', severity: 'success' });
    },
    onError: (err) => {
      setSnackbar?.({ open: true, message: err?.message || 'Error recopilant OSINT', severity: 'error' });
    },
  });

  const handleCollect = () => {
    if (!query.trim()) return;
    collectMutation.mutate({
      case_id: parseInt(caseId, 10),
      query: query.trim(),
      source_type: sourceType,
      thematic: thematic || undefined,
    });
  };

  const osintData = caseData?.osint_data || [];
  const tools = (toolsData?.length ? toolsData : SOURCE_OPTIONS.map((s) => ({ id: s.value, name: s.label, category: 'OSINT' })));

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
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
            <Typography variant="h6" sx={{ fontWeight: 600, color: EIU.black, fontFamily: EIU.serif }}>
              Recopilar dades OSINT
            </Typography>
            <Chip label="Dades de demostració" size="small" variant="outlined" sx={{ fontSize: '0.7rem' }} />
          </Box>
          <Grid container spacing={2} alignItems="center">
            <Grid item xs={12} sm={3}>
              <FormControl fullWidth size="small">
                <InputLabel>Temàtica</InputLabel>
                <Select
                  value={thematic}
                  onChange={(e) => setThematic(e.target.value)}
                  label="Temàtica"
                  sx={{ borderRadius: 1 }}
                >
                  {THEMATIC_OPTIONS.map((opt) => (
                    <MenuItem key={opt.value || 'none'} value={opt.value}>
                      {opt.label}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Grid>
            <Grid item xs={12} sm={3}>
              <FormControl fullWidth size="small">
                <InputLabel>Tipus de font</InputLabel>
                <Select
                  value={sourceType}
                  onChange={(e) => setSourceType(e.target.value)}
                  label="Tipus de font"
                  sx={{ borderRadius: 1 }}
                >
                  {SOURCE_OPTIONS.map((opt) => (
                    <MenuItem key={opt.value} value={opt.value}>
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        {opt.icon}
                        {opt.label}
                      </Box>
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Grid>
            <Grid item xs={12} sm={4}>
              <TextField
                fullWidth
                size="small"
                label="Consulta"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder={
                  sourceType === 'username' || sourceType === 'sherlock'
                    ? "Nom d'usuari a cercar"
                    : sourceType === 'domain' || sourceType === 'recon-ng' || sourceType === 'whois' || sourceType === 'dns'
                    ? 'Domini (ex: example.com)'
                    : 'Paraules clau o consulta'
                }
                onKeyDown={(e) => e.key === 'Enter' && handleCollect()}
                sx={{ '& .MuiOutlinedInput-root': { borderRadius: 1 } }}
              />
            </Grid>
            <Grid item xs={12} sm={2}>
              <Button
                fullWidth
                variant="contained"
                startIcon={<SearchIcon />}
                onClick={handleCollect}
                disabled={!query.trim() || collectMutation.isLoading}
                sx={{
                  backgroundColor: EIU.red,
                  color: '#fff',
                  textTransform: 'none',
                  fontWeight: 600,
                  borderRadius: 1,
                  '&:hover': { backgroundColor: EIU.redDark },
                }}
              >
                {collectMutation.isLoading ? 'Cercant…' : 'Cercar'}
              </Button>
            </Grid>
          </Grid>
          {collectMutation.isLoading && (
            <LinearProgress sx={{ mt: 2, height: 4, borderRadius: 2, backgroundColor: alpha(EIU.red, 0.2), '& .MuiLinearProgress-bar': { backgroundColor: EIU.red } }} />
          )}
        </CardContent>
      </Card>

      {collectMutation.isError && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => collectMutation.reset()}>
          {collectMutation.error?.message || 'Error recopilant dades OSINT'}
        </Alert>
      )}

      <Typography variant="h6" sx={{ fontWeight: 600, color: EIU.black, fontFamily: EIU.serif, mb: 2 }}>
        Dades recopilades ({osintData.length})
      </Typography>

      <Grid container spacing={2}>
        {osintData.map((item) => (
          <Grid item xs={12} key={item.id}>
            <Card
              sx={{
                background: EIU.bgCard,
                border: `1px solid ${EIU.border}`,
                borderRadius: 2,
                overflow: 'hidden',
              }}
              onClick={() => setExpandedId(expandedId === item.id ? null : item.id)}
            >
              <CardContent>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 1 }}>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, flexWrap: 'wrap' }}>
                    <Chip
                      label={item.source}
                      size="small"
                    sx={{
                      fontWeight: 600,
                      backgroundColor: alpha(EIU.red, 0.1),
                      color: EIU.red,
                      border: `1px solid ${alpha(EIU.red, 0.3)}`,
                    }}
                  />
                    {item.thematic && (
                      <Chip label={item.thematic} size="small" variant="outlined" sx={{ fontWeight: 500 }} />
                    )}
                    {(() => {
                      const url = getOriginalUrl(item);
                      return url ? (
                        <Button
                          size="small"
                          startIcon={<OpenInNewIcon />}
                          onClick={(e) => { e.stopPropagation(); window.open(url, '_blank'); }}
                          sx={{ textTransform: 'none', minWidth: 'auto', px: 1 }}
                        >
                          Veure original
                        </Button>
                      ) : null;
                    })()}
                  </Box>
                  <Typography variant="caption" sx={{ color: EIU.gray }}>
                    {item.collected_at && format(new Date(item.collected_at), 'dd/MM/yyyy HH:mm')}
                  </Typography>
                </Box>
                <Typography variant="body2" sx={{ mt: 1, color: EIU.gray }}>
                  Tipus: {item.data_type}
                </Typography>
                <Collapse in={expandedId === item.id}>
                  <Box sx={{ mt: 2, p: 2, bgcolor: 'grey.100', borderRadius: 1, border: `1px solid ${EIU.border}` }}>
                    <Typography variant="body2" component="pre" sx={{ fontSize: '0.8125rem', overflow: 'auto', maxHeight: 320 }}>
                      {JSON.stringify(item.raw_data, null, 2)}
                    </Typography>
                  </Box>
                </Collapse>
                <Typography variant="caption" sx={{ display: 'block', mt: 1, color: EIU.gray }}>
                  {expandedId === item.id ? 'Clica per tancar' : 'Clica per veure JSON'}
                </Typography>
              </CardContent>
            </Card>
          </Grid>
        ))}

        {osintData.length === 0 && (
          <Grid item xs={12}>
            <Alert severity="info" sx={{ borderRadius: 2 }}>
              No hi ha dades OSINT. Triau tipus de font i introduïu una consulta per començar.
            </Alert>
          </Grid>
        )}
      </Grid>
    </Box>
  );
}

export default OSINTTab;
