
import React from 'react';
import { Box, Typography, Grid, Paper } from '@mui/material';
import ChatWindow from '../components/copilot/ChatWindow';
import SuggestedQuestions from '../components/copilot/SuggestedQuestions';

const CopilotPage: React.FC = () => {
  // This is a bit of a hack to allow the suggested questions to send a message.
  // A better solution would be to use a state management library like Redux or Zustand.
  const [question, setQuestion] = React.useState('');

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        AI Copilot
      </Typography>
      <Grid container spacing={3}>
        <Grid item xs={12} md={8}>
          <ChatWindow key={question} initialMessage={question} />
          <Box sx={{ mt: 2 }}>
            <SuggestedQuestions onQuestionClick={setQuestion} />
          </Box>
        </Grid>
        <Grid item xs={12} md={4}>
          <Paper sx={{ height: '75vh', p: 2 }}>
            <Typography variant="h6">Context Viewer</Typography>
            {/* Context will be displayed here */}
          </Paper>
        </Grid>
      </Grid>
    </Box>
  );
};

export default CopilotPage;
