
import React, { useState, useEffect } from 'react';
import { Box, Paper, CircularProgress, Alert } from '@mui/material';
import MessageList from './MessageList';
import MessageInput from './MessageInput';
import { askCopilot } from '../../services/copilotService';

export type Message = {
  id: string;
  text: string;
  sender: 'user' | 'bot';
  metadata?: Record<string, any>;
};

interface ChatWindowProps {
  initialMessage?: string;
}

const ChatWindow: React.FC<ChatWindowProps> = ({ initialMessage }) => {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: '1',
      text: 'Hello! I am the Contract AI Copilot. How can I help you today?',
      sender: 'bot',
    },
  ]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (initialMessage) {
      handleSendMessage(initialMessage);
    }
  }, [initialMessage]);

  const handleSendMessage = async (text: string) => {
    const newMessage: Message = {
      id: Date.now().toString(),
      text,
      sender: 'user',
    };
    setMessages(prevMessages => [...prevMessages, newMessage]);
    setLoading(true);
    setError(null);

    try {
      const response = await askCopilot(text);
      const botMessage: Message = {
        id: (Date.now() + 1).toString(),
        text: response.answer,
        sender: 'bot',
        metadata: { sources: response.sources },
      };
      setMessages(prevMessages => [...prevMessages, botMessage]);
    } catch (err) {
      setError('Failed to get a response from the copilot.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Paper sx={{ height: '75vh', display: 'flex', flexDirection: 'column' }}>
      <Box sx={{ flexGrow: 1, p: 2, overflowY: 'auto' }}>
        <MessageList messages={messages} />
        {loading && <CircularProgress sx={{ mt: 1 }} />}
        {error && <Alert severity="error" sx={{ mt: 1 }}>{error}</Alert>}
      </Box>
      <Box sx={{ p: 2, borderTop: '1px solid #ddd' }}>
        <MessageInput onSendMessage={handleSendMessage} />
      </Box>
    </Paper>
  );
};

export default ChatWindow;
