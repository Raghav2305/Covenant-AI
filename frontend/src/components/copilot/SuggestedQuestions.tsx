
import React from 'react';
import { Box, Typography, Chip } from '@mui/material';

const questions = [
  'Which contracts expire in the next 90 days?',
  'Show me all high-risk obligations.',
  'Summarize the key terms of the Acme Corp Service Agreement.',
  'Are there any overdue obligations?',
];

interface SuggestedQuestionsProps {
  onQuestionClick: (question: string) => void;
}

const SuggestedQuestions: React.FC<SuggestedQuestionsProps> = ({ onQuestionClick }) => {
  return (
    <Box>
      <Typography variant="subtitle1" gutterBottom>Suggested Questions</Typography>
      <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
        {questions.map(q => (
          <Chip key={q} label={q} onClick={() => onQuestionClick(q)} />
        ))}
      </Box>
    </Box>
  );
};

export default SuggestedQuestions;
