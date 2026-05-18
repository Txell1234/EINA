import React from 'react';
import { Box, Paper, Typography } from '@mui/material';

function GeopoliticalMap({ countries = [], height = 400 }) {
  const primary = countries?.[0]?.name;
  return (
    <Paper sx={{ p: 2, minHeight: height || 120, bgcolor: 'grey.50' }}>
      <Typography variant="subtitle2" color="text.secondary" gutterBottom>
        Mapa geopolític
      </Typography>
      <Box sx={{ py: 2, textAlign: 'center' }}>
        <Typography variant="body2" color="text.secondary">
          {primary ? `País: ${primary}` : 'Selecciona un país per visualitzar'}
        </Typography>
      </Box>
    </Paper>
  );
}

export default GeopoliticalMap;
