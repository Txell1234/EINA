import { createTheme } from '@mui/material/styles';

export default createTheme({
  palette: {
    primary: { main: '#E3120B' },
    secondary: { main: '#4A4A4A' },
    background: { default: '#fafafa', paper: '#ffffff' },
  },
  typography: {
    fontFamily: '"Inter", "Segoe UI", "Roboto", sans-serif',
    h6: { fontWeight: 600 },
  },
});
