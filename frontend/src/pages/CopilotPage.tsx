import React, { useState, useEffect, useRef } from 'react';
import { Box, Typography, Grid, Paper, TextField, IconButton, CircularProgress, Alert, Chip, Avatar, Divider } from '@mui/material';
import { styled, keyframes } from '@mui/system';
import { Send, SmartToy, AccountCircle, Close } from '@mui/icons-material';
import { Link as RouterLink } from 'react-router-dom';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { askCopilot } from '../services/copilotService';

// --- Animation ---
const fadeIn = keyframes`
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
`;

// --- Styled Components ---
const GlassmorphicPaper = styled(Paper)(({ theme }) => ({
    height: 'calc(80vh)',
    display: 'flex',
    flexDirection: 'column',
    background: 'rgba(255, 255, 255, 0.6)',
    backdropFilter: 'blur(10px)',
    border: '1px solid rgba(255, 255, 255, 0.2)',
    borderRadius: theme.shape.borderRadius * 2,
}));

const GradientAvatar = styled(Avatar)(({ theme, ownerState }) => ({
    background: ownerState.sender === 'user' 
        ? `linear-gradient(45deg, ${theme.palette.primary.main}, ${theme.palette.primary.light})` 
        : `linear-gradient(45deg, ${theme.palette.secondary.main}, ${theme.palette.secondary.light})`,
}));

const MessageBubble = styled(Paper)(({ theme, ownerState }) => ({
    padding: theme.spacing(1.5, 2),
    borderRadius: ownerState.sender === 'user' ? '20px 20px 5px 20px' : '20px 20px 20px 5px',
    maxWidth: '100%',
    boxShadow: '0 4px 12px rgba(0,0,0,0.1)',
    background: ownerState.sender === 'user' ? theme.palette.primary.main : '#fff',
    color: ownerState.sender === 'user' ? '#fff' : '#000',
}));

const Timestamp = styled(Typography)(({ theme }) => ({
    fontSize: '0.7rem',
    color: theme.palette.text.disabled,
    opacity: 0,
    transition: 'opacity 0.3s',
    textAlign: 'center',
    marginTop: theme.spacing(0.5),
}));

const MessageContainer = styled(Box)({
    animation: `${fadeIn} 0.5s ease-in-out`,
    '&:hover .timestamp': {
        opacity: 1,
    },
});

// --- Helper Types & Components ---
type Message = {
    id: string;
    text: string;
    sender: 'user' | 'bot';
    metadata?: { sources?: any[] };
};

type Source = {
    doc_id: string;
    content: string;
    metadata: {
        type: string;
        title?: string;
        contract_id?: string;
        obligation_id?: string;
    };
};

const SuggestedQuestions = ({ onQuestionClick }: { onQuestionClick: (q: string) => void }) => {
    const questions = [
        'Which contracts expire in the next 90 days?',
        'Show me all high-risk obligations.',
        'Are there any overdue obligations?',
    ];
    return (
        <Box sx={{ p: 2, display: 'flex', flexWrap: 'wrap', gap: 1, justifyContent: 'center' }}>
            {questions.map(q => (
                <Chip key={q} label={q} onClick={() => onQuestionClick(q)} variant="outlined" sx={{ backdropFilter: 'blur(5px)' }} />
            ))}
        </Box>
    );
};

// --- Main Copilot Page Component ---
const CopilotPage: React.FC = () => {
    const [messages, setMessages] = useState<Message[]>([
        {
            id: '1',
            text: 'Hello! I am the Contract AI Copilot. How can I help you today?',
            sender: 'bot',
        },
    ]);
    const [input, setInput] = useState('');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [selectedSource, setSelectedSource] = useState<Source | null>(null);
    const messageEndRef = useRef<HTMLDivElement | null>(null);

    useEffect(() => {
        messageEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages]);

    const handleSendMessage = async (text: string) => {
        if (!text.trim()) return;

        const newMessage: Message = {
            id: Date.now().toString(),
            text,
            sender: 'user',
        };
        setMessages(prev => [...prev, newMessage]);
        setInput('');
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
            setMessages(prev => [...prev, botMessage]);
        } catch (err) {
            setError('Failed to get a response from the copilot. Please try again.');
        } finally {
            setLoading(false);
        }
    };

    return (
        <Box sx={{ 
            background: 'linear-gradient(120deg, #fdfbfb 0%, #ebedee 100%)',
            p: 3, 
            borderRadius: 2 
        }}>
            <Typography variant="h4" fontWeight="bold" gutterBottom sx={{ color: 'text.primary' }}>AI Copilot</Typography>
            <Grid container spacing={3}>
                <Grid item xs={12} md={selectedSource ? 7 : 12}>
                    <GlassmorphicPaper elevation={6}>
                        <Box sx={{ flexGrow: 1, overflowY: 'auto', p: 3 }}>
                            {messages.map(msg => (
                                <MessageContainer key={msg.id}>
                                    <Box sx={{ mb: 2, display: 'flex', gap: 2, flexDirection: msg.sender === 'user' ? 'row-reverse' : 'row' }}>
                                        <GradientAvatar ownerState={{ sender: msg.sender }}>
                                            {msg.sender === 'user' ? <AccountCircle /> : <SmartToy />}
                                        </GradientAvatar>
                                        <Box sx={{ maxWidth: '80%' }}>
                                            <MessageBubble ownerState={{ sender: msg.sender }}>
                                                <ReactMarkdown remarkPlugins={[remarkGfm]}>{msg.text}</ReactMarkdown>
                                            </MessageBubble>
                                            {msg.sender === 'bot' && msg.metadata?.sources && (
                                                <Box sx={{ mt: 1, display: 'flex', flexWrap: 'wrap', gap: 1, justifyContent: 'flex-start' }}>
                                                    {msg.metadata.sources.map((source: Source, index: number) => (
                                                        <Chip
                                                            key={index}
                                                            label={source.metadata.title || `Source ${index + 1}`}
                                                            onClick={() => setSelectedSource(source)}
                                                            clickable size="small" variant="outlined"
                                                        />
                                                    ))}
                                                </Box>
                                            )}
                                        </Box>
                                    </Box>
                                    <Timestamp className="timestamp">{new Date(parseInt(msg.id)).toLocaleTimeString()}</Timestamp>
                                </MessageContainer>
                            ))}
                            {loading && <CircularProgress sx={{ mt: 1, mx: 'auto', display: 'block' }} />}
                            {error && <Alert severity="error" sx={{ mt: 1 }}>{error}</Alert>}
                            <div ref={messageEndRef} />
                        </Box>

                        <Divider />

                        {messages.length <= 1 && <SuggestedQuestions onQuestionClick={handleSendMessage} />}

                        <Box component="form" onSubmit={(e) => { e.preventDefault(); handleSendMessage(input); }} sx={{ p: 2, display: 'flex', alignItems: 'center', gap: 1 }}>
                            <TextField
                                fullWidth
                                variant="outlined"
                                placeholder="Ask the AI Copilot..."
                                value={input}
                                onChange={(e) => setInput(e.target.value)}
                                sx={{ 
                                    '& .MuiOutlinedInput-root': {
                                        borderRadius: '20px',
                                        background: 'rgba(255,255,255,0.7)',
                                    }
                                }}
                            />
                            <IconButton type="submit" color="primary" disabled={loading} sx={{ background: 'rgba(255,255,255,0.7)' }}>
                                <Send />
                            </IconButton>
                        </Box>
                    </GlassmorphicPaper>
                </Grid>

                {selectedSource && (
                    <Grid item xs={12} md={5}>
                        <GlassmorphicPaper elevation={6} sx={{ p: 2, overflowY: 'auto' }}>
                            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                <Typography variant="h6">Context Viewer</Typography>
                                <IconButton onClick={() => setSelectedSource(null)}><Close /></IconButton>
                            </Box>
                            <Divider sx={{ my: 1 }} />
                            <Typography variant="subtitle1" gutterBottom>{selectedSource.metadata.title}</Typography>
                            <Chip
                                label={selectedSource.metadata.type === 'contract' ? 'Contract' : 'Obligation'}
                                component={RouterLink}
                                to={`/contracts/${selectedSource.metadata.contract_id}`}
                                clickable
                                size="small"
                                sx={{ mb: 2 }}
                            />
                            <Typography sx={{ whiteSpace: 'pre-wrap', fontFamily: 'monospace', fontSize: '0.8rem', bgcolor: 'rgba(255,255,255,0.5)', p: 2, borderRadius: 1 }}>
                                {selectedSource.content}
                            </Typography>
                        </GlassmorphicPaper>
                    </Grid>
                )}
            </Grid>
        </Box>
    );
};

export default CopilotPage;
