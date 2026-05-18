import React, { useState } from 'react';
import { HashRouter, Routes, Route, Navigate, useParams, useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from 'react-query';
import {
  Box,
  Drawer,
  AppBar,
  Toolbar,
  Typography,
  List,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Button,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Chip,
  IconButton,
  Snackbar,
  Alert,
  Card,
  CardContent,
  Tabs,
  Tab,
  CircularProgress,
} from '@mui/material';
import DashboardIcon from '@mui/icons-material/Dashboard';
import FolderIcon from '@mui/icons-material/Folder';
import AddIcon from '@mui/icons-material/Add';
import PublicIcon from '@mui/icons-material/Public';
import PsychologyIcon from '@mui/icons-material/Psychology';
import AssessmentIcon from '@mui/icons-material/Assessment';
import TrendingUpIcon from '@mui/icons-material/TrendingUp';
import AnalyticsIcon from '@mui/icons-material/Analytics';
import WarningIcon from '@mui/icons-material/Warning';
import EditIcon from '@mui/icons-material/Edit';
import DeleteIcon from '@mui/icons-material/Delete';
import { getCases, getFullCase, createCase, updateCase, deleteCase, getCasesWithFilters } from './services/api';
import OSINTTab from './components/tabs/OSINTTab';
import AIAnalysisTab from './components/tabs/AIAnalysisTab';
import QualitativeTab from './components/tabs/QualitativeTab';
import InvestmentTab from './components/tabs/InvestmentTab';
import UnifiedAnalysisTab from './components/tabs/UnifiedAnalysisTab';
import RiskAnalysisTab from './components/tabs/RiskAnalysisTab';

const DRAWER_WIDTH = 260;
const THEMATIC_OPTIONS = ['geopolitical', 'cyber', 'brand', 'person', 'market', 'other'];

function Layout({ children }) {
  return (
    <Box sx={{ display: 'flex', minHeight: '100vh' }}>
      <AppBar position="fixed" sx={{ zIndex: (t) => t.zIndex.drawer + 1, backgroundColor: '#0A0A0A' }}>
        <Toolbar>
          <Typography variant="h6" sx={{ flexGrow: 1, fontWeight: 600 }}>
            OSINT Platform
          </Typography>
        </Toolbar>
      </AppBar>
      <Drawer
        variant="permanent"
        sx={{
          width: DRAWER_WIDTH,
          flexShrink: 0,
          '& .MuiDrawer-paper': { width: DRAWER_WIDTH, boxSizing: 'border-box', mt: '64px', borderRight: '1px solid #E0E0E0' },
        }}
      >
        {children}
      </Drawer>
    </Box>
  );
}

function Dashboard({ navigate }) {
  const [thematicFilter, setThematicFilter] = useState('');
  const [searchName, setSearchName] = useState('');
  const { data: cases = [] } = useQuery(
    thematicFilter ? ['cases', 'filtered', thematicFilter] : 'cases',
    thematicFilter ? () => getCasesWithFilters({ thematic: thematicFilter }).then((r) => r.data) : getCases,
    { select: (r) => (Array.isArray(r) ? r : r?.data) || [] }
  );
  const filteredCases = searchName.trim()
    ? cases.filter((c) => (c.name || '').toLowerCase().includes(searchName.trim().toLowerCase()))
    : cases;
  const thematicCounts = cases.reduce((acc, c) => {
    (c.thematics || []).forEach((t) => { acc[t] = (acc[t] || 0) + 1; });
    return acc;
  }, {});
  return (
    <Box sx={{ p: 3, ml: `${DRAWER_WIDTH}px`, mt: '64px' }}>
      <Typography variant="h5" sx={{ fontWeight: 600, mb: 3 }}>
        Dashboard
      </Typography>
      <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap', mb: 3 }}>
        <TextField
          size="small"
          placeholder="Cercar per nom..."
          value={searchName}
          onChange={(e) => setSearchName(e.target.value)}
          sx={{ minWidth: 200 }}
        />
        <FormControl size="small" sx={{ minWidth: 180 }}>
          <InputLabel>Temàtica</InputLabel>
          <Select value={thematicFilter} label="Temàtica" onChange={(e) => setThematicFilter(e.target.value)}>
            <MenuItem value="">Totes</MenuItem>
            {THEMATIC_OPTIONS.map((t) => (
              <MenuItem key={t} value={t}>{t}</MenuItem>
            ))}
          </Select>
        </FormControl>
      </Box>
      {Object.keys(thematicCounts).length > 0 && (
        <Box sx={{ mb: 3, display: 'flex', gap: 1, flexWrap: 'wrap' }}>
          <Typography variant="subtitle2" sx={{ mr: 1, alignSelf: 'center' }}>Casos per temàtica:</Typography>
          {Object.entries(thematicCounts).map(([t, n]) => (
            <Chip key={t} label={`${t}: ${n}`} size="small" variant="outlined" />
          ))}
        </Box>
      )}
      <Typography variant="h6" sx={{ fontWeight: 600, mb: 2 }}>
        Casos
      </Typography>
      <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', sm: 'repeat(2, 1fr)', md: 'repeat(3, 1fr)' }, gap: 2 }}>
        {filteredCases.map((c) => (
          <Card
            key={c.id}
            sx={{ cursor: 'pointer', border: '1px solid #E0E0E0', '&:hover': { boxShadow: 2 } }}
            onClick={() => navigate(`/case/${c.id}`)}
          >
            <CardContent>
              <Typography variant="subtitle1" sx={{ fontWeight: 600 }}>{c.name}</Typography>
              {c.description && <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5, overflow: 'hidden', textOverflow: 'ellipsis', display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical' }}>{c.description}</Typography>}
              <Box sx={{ display: 'flex', gap: 0.5, flexWrap: 'wrap', mt: 1 }}>
                {(c.thematics || []).map((t) => (
                  <Chip key={t} label={t} size="small" variant="outlined" />
                ))}
              </Box>
            </CardContent>
          </Card>
        ))}
      </Box>
      {filteredCases.length === 0 && <Typography color="text.secondary">No hi ha casos. Crea un de nou.</Typography>}
    </Box>
  );
}

function CaseView({ caseId, navigate, setSnackbar }) {
  const [tab, setTab] = useState(0);
  const [editOpen, setEditOpen] = useState(false);
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [editForm, setEditForm] = useState({ name: '', description: '', country: '', case_type: '', thematics: [] });
  const queryClient = useQueryClient();
  const { data: caseData, isLoading } = useQuery(
    ['case', caseId],
    () => getFullCase(caseId).then((r) => r.data),
    { enabled: !!caseId }
  );

  const updateMutation = useMutation((data) => updateCase(caseId, data), {
    onSuccess: () => { queryClient.invalidateQueries(['case', caseId]); setEditOpen(false); setSnackbar?.({ open: true, message: 'Cas actualitzat', severity: 'success' }); },
    onError: (e) => setSnackbar?.({ open: true, message: e?.message || 'Error en actualitzar', severity: 'error' }),
  });
  const deleteMutation = useMutation(() => deleteCase(caseId), {
    onSuccess: () => { queryClient.invalidateQueries('cases'); setSnackbar?.({ open: true, message: 'Cas eliminat', severity: 'success' }); navigate('/'); setDeleteOpen(false); },
    onError: (e) => setSnackbar?.({ open: true, message: e?.message || 'Error en eliminar', severity: 'error' }),
  });

  const openEdit = () => {
    setEditForm({
      name: caseData?.name || '',
      description: caseData?.description || '',
      country: caseData?.country || '',
      case_type: caseData?.case_type || '',
      thematics: caseData?.thematics || [],
    });
    setEditOpen(true);
  };
  const toggleEditThematic = (t) => {
    setEditForm((prev) => ({
      ...prev,
      thematics: prev.thematics.includes(t) ? prev.thematics.filter((x) => x !== t) : [...prev.thematics, t],
    }));
  };

  const tabs = [
    { label: 'OSINT', icon: <PublicIcon />, comp: OSINTTab },
    { label: 'Anàlisi IA', icon: <PsychologyIcon />, comp: AIAnalysisTab },
    { label: 'Qualitatiu', icon: <AssessmentIcon />, comp: QualitativeTab },
    { label: 'Inversió', icon: <TrendingUpIcon />, comp: InvestmentTab },
    { label: 'Unificat', icon: <AnalyticsIcon />, comp: UnifiedAnalysisTab },
    { label: 'Risc', icon: <WarningIcon />, comp: RiskAnalysisTab },
  ];
  const TabComp = tabs[tab]?.comp;

  if (isLoading || !caseData) return <Box sx={{ p: 3, ml: DRAWER_WIDTH, mt: 10, display: 'flex', alignItems: 'center', justifyContent: 'center', flexDirection: 'column', gap: 2 }}><CircularProgress /><Typography color="text.secondary">Carregant...</Typography></Box>;

  return (
    <Box sx={{ p: 3, ml: `${DRAWER_WIDTH}px`, mt: '64px' }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: 1, mb: 2 }}>
        <Box>
          <Typography variant="h5" sx={{ fontWeight: 600 }}>
            {caseData.name}
          </Typography>
          {caseData.thematics?.length > 0 && (
        <Box sx={{ display: 'flex', gap: 1, mt: 1 }}>
          {caseData.thematics.map((t) => (
            <Chip key={t} label={t} size="small" variant="outlined" />
          ))}
        </Box>
          )}
        </Box>
        <Box sx={{ display: 'flex', gap: 1 }}>
          <IconButton size="small" onClick={openEdit} title="Editar cas">
            <EditIcon />
          </IconButton>
          <IconButton size="small" onClick={() => setDeleteOpen(true)} color="error" title="Eliminar cas">
            <DeleteIcon />
          </IconButton>
        </Box>
      </Box>
      <Tabs value={tab} onChange={(_, v) => setTab(v)} sx={{ borderBottom: 1, borderColor: 'divider', mb: 2 }}>
        {tabs.map((t, i) => (
          <Tab key={i} icon={t.icon} iconPosition="start" label={t.label} sx={{ textTransform: 'none' }} />
        ))}
      </Tabs>
      {TabComp && <TabComp caseId={caseId} caseData={caseData} setSnackbar={setSnackbar} />}

      <Dialog open={editOpen} onClose={() => setEditOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Editar cas</DialogTitle>
        <DialogContent>
          <TextField fullWidth label="Nom" value={editForm.name} onChange={(e) => setEditForm({ ...editForm, name: e.target.value })} sx={{ mt: 1, mb: 2 }} />
          <TextField fullWidth label="Descripció" multiline value={editForm.description} onChange={(e) => setEditForm({ ...editForm, description: e.target.value })} sx={{ mb: 2 }} />
          <TextField fullWidth label="País" value={editForm.country} onChange={(e) => setEditForm({ ...editForm, country: e.target.value })} sx={{ mb: 2 }} />
          <FormControl fullWidth sx={{ mb: 2 }}>
            <InputLabel>Tipus de cas</InputLabel>
            <Select value={editForm.case_type} label="Tipus de cas" onChange={(e) => setEditForm({ ...editForm, case_type: e.target.value })}>
              <MenuItem value="">—</MenuItem>
              <MenuItem value="geopolitical">Geopolític</MenuItem>
              <MenuItem value="investment">Inversió</MenuItem>
              <MenuItem value="brand">Marca</MenuItem>
              <MenuItem value="other">Altres</MenuItem>
            </Select>
          </FormControl>
          <Typography variant="subtitle2" sx={{ mb: 1 }}>Temàtiques</Typography>
          <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1, mb: 2 }}>
            {THEMATIC_OPTIONS.map((t) => (
              <Chip key={t} label={t} size="small" onClick={() => toggleEditThematic(t)} color={editForm.thematics.includes(t) ? 'primary' : 'default'} variant={editForm.thematics.includes(t) ? 'filled' : 'outlined'} />
            ))}
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setEditOpen(false)}>Cancel·lar</Button>
          <Button variant="contained" onClick={() => updateMutation.mutate({ name: editForm.name, description: editForm.description || null, country: editForm.country || null, case_type: editForm.case_type || null, thematics: editForm.thematics.length ? editForm.thematics : null })} disabled={!editForm.name.trim() || updateMutation.isLoading}>
            Desar
          </Button>
        </DialogActions>
      </Dialog>

      <Dialog open={deleteOpen} onClose={() => setDeleteOpen(false)}>
        <DialogTitle>Eliminar cas</DialogTitle>
        <DialogContent>
          <Typography>Segur que vols eliminar el cas &quot;{caseData?.name}&quot;? Aquesta acció no es pot desfer.</Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDeleteOpen(false)}>Cancel·lar</Button>
          <Button variant="contained" color="error" onClick={() => deleteMutation.mutate()} disabled={deleteMutation.isLoading}>
            Eliminar
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}

function App() {
  return (
    <HashRouter>
      <AppContent />
    </HashRouter>
  );
}

function AppContent() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [createOpen, setCreateOpen] = useState(false);
  const [newCase, setNewCase] = useState({ name: '', description: '', country: '', case_type: '', thematics: [] });
  const [snackbar, setSnackbar] = useState({ open: false, message: '', severity: 'success' });

  const createMutation = useMutation(createCase, {
    onSuccess: (r) => {
      queryClient.invalidateQueries('cases');
      setCreateOpen(false);
      setNewCase({ name: '', description: '', country: '', case_type: '', thematics: [] });
      setSnackbar({ open: true, message: 'Cas creat correctament', severity: 'success' });
      navigate(`/case/${r.data.id}`);
    },
    onError: (e) => setSnackbar({ open: true, message: e?.message || 'Error en crear el cas', severity: 'error' }),
  });

  const handleCreate = () => {
    createMutation.mutate({
      name: newCase.name,
      description: newCase.description || null,
      country: newCase.country || null,
      case_type: newCase.case_type || null,
      thematics: newCase.thematics.length ? newCase.thematics : null,
    });
  };

  const toggleThematic = (t) => {
    setNewCase((prev) => ({
      ...prev,
      thematics: prev.thematics.includes(t) ? prev.thematics.filter((x) => x !== t) : [...prev.thematics, t],
    }));
  };

  return (
    <>
      <Layout>
        <Box sx={{ overflow: 'auto', py: 2 }}>
          <List>
            <ListItemButton onClick={() => navigate('/')}>
              <ListItemIcon><DashboardIcon /></ListItemIcon>
              <ListItemText primary="Dashboard" />
            </ListItemButton>
            <ListItemButton onClick={() => setCreateOpen(true)}>
              <ListItemIcon><AddIcon /></ListItemIcon>
              <ListItemText primary="Nou cas" />
            </ListItemButton>
          </List>
        </Box>
      </Layout>
      <Box component="main" sx={{ flexGrow: 1 }}>
        <Routes>
          <Route path="/" element={<Dashboard navigate={navigate} />} />
          <Route path="/case/:id" element={<CaseViewWrapper setSnackbar={setSnackbar} />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </Box>

      <Dialog open={createOpen} onClose={() => setCreateOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Nou cas</DialogTitle>
        <DialogContent>
          <TextField fullWidth label="Nom" value={newCase.name} onChange={(e) => setNewCase({ ...newCase, name: e.target.value })} sx={{ mt: 1, mb: 2 }} />
          <TextField fullWidth label="Descripció" multiline value={newCase.description} onChange={(e) => setNewCase({ ...newCase, description: e.target.value })} sx={{ mb: 2 }} />
          <TextField fullWidth label="País" value={newCase.country} onChange={(e) => setNewCase({ ...newCase, country: e.target.value })} sx={{ mb: 2 }} />
          <FormControl fullWidth sx={{ mb: 2 }}>
            <InputLabel>Tipus de cas</InputLabel>
            <Select value={newCase.case_type} label="Tipus de cas" onChange={(e) => setNewCase({ ...newCase, case_type: e.target.value })}>
              <MenuItem value="">—</MenuItem>
              <MenuItem value="geopolitical">Geopolític</MenuItem>
              <MenuItem value="investment">Inversió</MenuItem>
              <MenuItem value="brand">Marca</MenuItem>
              <MenuItem value="other">Altres</MenuItem>
            </Select>
          </FormControl>
          <Typography variant="subtitle2" sx={{ mb: 1 }}>Temàtiques</Typography>
          <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1, mb: 2 }}>
            {THEMATIC_OPTIONS.map((t) => (
              <Chip
                key={t}
                label={t}
                onClick={() => toggleThematic(t)}
                color={newCase.thematics.includes(t) ? 'primary' : 'default'}
                variant={newCase.thematics.includes(t) ? 'filled' : 'outlined'}
                size="small"
              />
            ))}
          </Box>
          <Button variant="contained" onClick={handleCreate} disabled={!newCase.name.trim() || newCase.name.trim().length < 2 || createMutation.isLoading} fullWidth>
            Crear cas
          </Button>
          {newCase.name.trim().length > 0 && newCase.name.trim().length < 2 && <Typography variant="caption" color="error" sx={{ mt: 0.5 }}>El nom ha de tenir almenys 2 caràcters</Typography>}
        </DialogContent>
      </Dialog>

      <Snackbar open={snackbar.open} autoHideDuration={4000} onClose={() => setSnackbar((s) => ({ ...s, open: false }))} anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}>
        <Alert severity={snackbar.severity} onClose={() => setSnackbar((s) => ({ ...s, open: false }))}>
          {snackbar.message}
        </Alert>
      </Snackbar>
    </>
  );
}

function CaseViewWrapper({ setSnackbar }) {
  const { id } = useParams();
  const navigate = useNavigate();
  return <CaseView caseId={id} navigate={navigate} setSnackbar={setSnackbar} />;
}

export default App;
