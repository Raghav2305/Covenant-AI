
import React from 'react';
import { Box, Paper, Typography, Chip, Link } from '@mui/material';
import { Link as RouterLink } from 'react-router-dom';

export type Message = {
  id: string;
  text: string;
  sender: 'user' | 'bot';
  metadata?: Record<string, any>;
};

interface MessageListProps {
  messages: Message[];
}

const MessageList: React.FC<MessageListProps> = ({ messages }) => {
  return (
    <Box>
      {messages.map(msg => (
        <Box key={msg.id} sx={{ mb: 2, display: 'flex', flexDirection: 'column', alignItems: msg.sender === 'user' ? 'flex-end' : 'flex-start' }}>
          <Paper sx={{ p: 1.5, maxWidth: '70%', bgcolor: msg.sender === 'user' ? 'primary.main' : 'grey.300', color: msg.sender === 'user' ? 'primary.contrastText' : 'inherit' }}>
            <Typography variant="body1">{msg.text}</Typography>
          </Paper>
          {msg.sender === 'bot' && msg.metadata?.sources && (
            <Box sx={{ mt: 1, display: 'flex', flexWrap: 'wrap', gap: 1 }}>
              <Typography variant="caption" sx={{ mr: 1 }}>Sources:</Typography>
              {msg.metadata.sources.map((source: any, index: number) => (
                <Chip
                  key={index}
                  label={source.metadata.title || `Source ${index + 1}`}
                  component={RouterLink}
                  to={`/contracts/${source.metadata.contract_id}`}
                  clickable
                  size="small"
                />
              ))}
            </Box>
          )}
        </Box>
      ))}
    </Box>
  );
};

export default MessageList;
