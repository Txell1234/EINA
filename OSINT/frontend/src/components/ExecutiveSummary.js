import React from 'react';
import { Box, Typography } from '@mui/material';

function ExecutiveSummary({ analysis, caseData }) {
  const summary = analysis?.global_decision?.reasoning;
  const decision = analysis?.global_decision?.recommendation;
  return (
    <Box sx={{ mb: 2 }}>
      {summary && <Typography variant="body2" sx={{ mb: 1 }}>{summary}</Typography>}
      {decision && <Typography variant="subtitle2" color="primary">{decision}</Typography>}
    </Box>
  );
}

export default ExecutiveSummary;
