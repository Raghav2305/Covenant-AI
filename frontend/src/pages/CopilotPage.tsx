import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Box, Typography, Grid, Paper, TextField, IconButton, CircularProgress, Alert, Chip, Avatar, Divider, FormControl, InputLabel, Select, MenuItem, List, ListItemButton, ListItemText, Button } from '@mui/material';
import { styled, keyframes } from '@mui/system';
import { Send, SmartToy, AccountCircle, Close, Add, Delete } from '@mui/icons-material';
import { Link as RouterLink } from 'react-router-dom';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { askCopilot } from '../services/copilotService';
import { getContracts } from '../services/contractService';
import type { Contract } from '../services/contractService';
import { v4 as uuidv4 } from 'uuid';

// --- Types ---
type Message = { id: string; text: string; sender: 'user' | 'bot'; metadata?: { sources?: any[] }; };
type Source = { doc_id: string; content: string; metadata: { type: string; title?: string; contract_id?: string; }; };
type ChatSession = { id: string; title: string; messages: Message[]; createdAt: string; };

// --- Styled Components ---
const fadeIn = keyframes`from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); }`;

const GradientAvatar = styled(Avatar)(({ theme, ownerState }) => ({
    background: ownerState.sender === 'user' 
        ? `linear-gradient(45deg, ${theme.palette.primary.main}, ${theme.palette.primary.light})` 
        : `linear-gradient(45deg, ${theme.palette.secondary.main}, ${theme.palette.secondary.light})`,
}));

const MessageBubble = styled(Paper)(({ theme, ownerState }) => ({
    padding: theme.spacing(1.5, 2),
    borderRadius: ownerState.sender === 'user' ? '20px 20px 5px 20px' : '20px 20px 20px 5px',
    maxWidth: '100%',
    boxShadow: '0 4px 12px rgba(0,0,0,0.05)',
    background: ownerState.sender === 'user' ? theme.palette.primary.main : '#fff',
    color: ownerState.sender === 'user' ? '#fff' : theme.palette.text.primary,
    '& a': {
        color: ownerState.sender === 'user' ? '#fff' : theme.palette.primary.main,
        textDecoration: 'underline',
    }
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

const HISTORY_DRAWER_WIDTH = 280;

// --- Main Component ---
const CopilotPage: React.FC = () => {
    const [sessions, setSessions] = useState<ChatSession[]>([]);
    const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
    const [input, setInput] = useState('');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [selectedSource, setSelectedSource] = useState<Source | null>(null);
    const [contracts, setContracts] = useState<Contract[]>([]);
    const [selectedContract, setSelectedContract] = useState<string>('all');
    const messageEndRef = useRef<HTMLDivElement | null>(null);

    const handleNewChat = useCallback(() => {
        const newSession: ChatSession = {
            id: uuidv4(),
            title: 'New Chat',
            createdAt: new Date().toISOString(),
            messages: [{ id: '1', text: 'Hello! How can I help you today?', sender: 'bot' }],
        };
        setSessions(prev => [newSession, ...prev]);
        setActiveSessionId(newSession.id);
    }, []);

    useEffect(() => {
        try {
            const savedSessions = localStorage.getItem('chatSessions');
            const parsedSessions: ChatSession[] = savedSessions ? JSON.parse(savedSessions) : [];
            if (parsedSessions.length > 0) {
                setSessions(parsedSessions);
                setActiveSessionId(parsedSessions[0]?.id || null);
            } else {
                handleNewChat();
            }
        } catch (e) {
            console.error("Failed to load chat sessions", e);
            handleNewChat();
        }
    }, [handleNewChat]);

    useEffect(() => {
        if (sessions.length > 0) {
            localStorage.setItem('chatSessions', JSON.stringify(sessions));
        }
    }, [sessions]);

    useEffect(() => {
        messageEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [sessions, activeSessionId]);
    
    useEffect(() => {
        getContracts().then(setContracts);
    }, []);

    const handleDeleteSession = (sessionId: string) => {
        const newSessions = sessions.filter(s => s.id !== sessionId);
        setSessions(newSessions);
        if (activeSessionId === sessionId) {
            if (newSessions.length > 0) {
                setActiveSessionId(newSessions[0].id);
            } else {
                handleNewChat();
            }
        }
    };

    const handleSendMessage = async (text: string) => {
        if (!text.trim() || !activeSessionId) return;

        const userMessage: Message = { id: uuidv4(), text, sender: 'user' };
        
        const activeSession = sessions.find(s => s.id === activeSessionId);
        const isFirstUserMessage = activeSession?.messages.filter(m => m.sender === 'user').length === 0;

        setSessions(prev => prev.map(s => 
            s.id === activeSessionId 
            ? { ...s, title: isFirstUserMessage && text.length > 1 ? text.substring(0, 40) : s.title, messages: [...s.messages, userMessage] } 
            : s
        ));
        
        setInput('');
        setLoading(true);
        setError(null);

        try {
            const contractId = selectedContract === 'all' ? undefined : selectedContract;
            const response = await askCopilot(text, contractId);
            const botMessage: Message = {
                id: uuidv4(),
                text: response.answer,
                sender: 'bot',
                metadata: { sources: response.sources },
            };
            setSessions(prev => prev.map(s => 
                s.id === activeSessionId 
                ? { ...s, messages: [...s.messages, botMessage] } 
                : s
            ));
        } catch (err) {
            setError('Failed to get a response from the copilot. Please try again.');
        } finally {
            setLoading(false);
        }
    };

    const activeSession = sessions.find(s => s.id === activeSessionId);

    return (
        <Box sx={{ display: 'flex', height: 'calc(100vh - 64px - 48px)', gap: 2 }}>
            {/* History Sidebar */}
            <Paper elevation={3} sx={{ width: HISTORY_DRAWER_WIDTH, flexShrink: 0, display: 'flex', flexDirection: 'column' }}>
                <Box sx={{ p: 1, borderBottom: '1px solid rgba(0, 0, 0, 0.12)' }}>
                    <Button variant="outlined" startIcon={<Add />} fullWidth onClick={handleNewChat}>New Chat</Button>
                </Box>
                <List sx={{ overflowY: 'auto', flexGrow: 1 }}>
                    {sessions.map(session => (
                        <ListItemButton key={session.id} selected={session.id === activeSessionId} onClick={() => setActiveSessionId(session.id)}>
                            <ListItemText primary={session.title} primaryTypographyProps={{ noWrap: true, fontSize: '0.9rem' }} secondary={new Date(session.createdAt).toLocaleDateString()} />
                            <IconButton size="small" onClick={(e) => { e.stopPropagation(); handleDeleteSession(session.id); }}><Delete fontSize="inherit" /></IconButton>
                        </ListItemButton>
                    ))}
                </List>
            </Paper>

            {/* Main Content Area */}
            <Box component="main" sx={{ flexGrow: 1, display: 'flex', flexDirection: 'column', minWidth: 0 }}>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2, flexShrink: 0 }}>
                    <Typography variant="h4" fontWeight="bold">AI Copilot</Typography>
                    <FormControl sx={{ minWidth: 250 }} size="small">
                        <InputLabel>Contract Context</InputLabel>
                        <Select value={selectedContract} label="Contract Context" onChange={(e) => setSelectedContract(e.target.value)}>
                            <MenuItem value="all">All Contracts</MenuItem>
                            {contracts.map(contract => (
                                <MenuItem key={contract.id} value={contract.id}>{contract.title}</MenuItem>
                            ))}
                        </Select>
                    </FormControl>
                </Box>

                <Grid container spacing={2} sx={{ flexGrow: 1, minHeight: 0 }}>
                    <Grid item xs={12} md={selectedSource ? 7 : 12} sx={{ height: '100%'}}>
                        <Paper elevation={3} sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
                            <Box sx={{ flexGrow: 1, overflowY: 'auto', p: 3 }}>
                                {activeSession && activeSession.messages.length > 0 ? (
                                    activeSession.messages.map(msg => (
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
                                                        <Box sx={{ mt: 1, display: 'flex', flexWrap: 'wrap', gap: 1, justifyContent: msg.sender === 'user' ? 'flex-end' : 'flex-start' }}>
                                                            {msg.metadata.sources.map((source: Source, index: number) => (
                                                                <Chip key={index} label={source.metadata.title || `Source ${index + 1}`} onClick={() => setSelectedSource(source)} clickable size="small" variant="outlined" />
                                                            ))}
                                                        </Box>
                                                    )}
                                                </Box>
                                            </Box>
                                            <Timestamp className="timestamp">{new Date(parseInt(msg.id)).toLocaleTimeString()}</Timestamp>
                                        </MessageContainer>
                                    ))
                                ) : (
                                    <Typography sx={{textAlign: 'center', color: 'text.secondary', mt: 4}}>Select a chat or start a new one.</Typography>
                                )}
                                {loading && <CircularProgress sx={{ mt: 2, mx: 'auto', display: 'block' }} />}
                                <div ref={messageEndRef} />
                            </Box>
                            <Divider />
                            <Box component="form" onSubmit={(e) => { e.preventDefault(); handleSendMessage(input); }} sx={{ p: 2, display: 'flex', alignItems: 'center', gap: 1 }}>
                                <TextField fullWidth variant="outlined" placeholder="Ask the AI Copilot..." value={input} onChange={(e) => setInput(e.target.value)} />
                                <IconButton type="submit" color="primary" disabled={loading}><Send /></IconButton>
                            </Box>
                        </Paper>
                    </Grid>
                    {selectedSource && (
                        <Grid item xs={12} md={5} sx={{ height: '100%' }}>
                            <Paper elevation={3} sx={{ height: '100%', p: 2, overflowY: 'auto' }}>
                                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                    <Typography variant="h6">Context Viewer</Typography>
                                    <IconButton onClick={() => setSelectedSource(null)}><Close /></IconButton>
                                </Box>
                                <Divider sx={{ my: 1 }} />
                                <Typography variant="subtitle1" gutterBottom>{selectedSource.metadata.title}</Typography>
                                <Chip label={selectedSource.metadata.type === 'contract' ? 'Contract' : 'Obligation'} component={RouterLink} to={`/contracts/${selectedSource.metadata.contract_id}`} clickable size="small" sx={{ mb: 2 }}/>
                                <Typography sx={{ whiteSpace: 'pre-wrap', fontFamily: 'monospace', fontSize: '0.8rem', bgcolor: 'grey.50', p: 2, borderRadius: 1 }}>
                                    {selectedSource.content}
                                </Typography>
                            </Paper>
                        </Grid>
                    )}
                </Grid>
            </Box>
        </Box>
    );
};

export default CopilotPage;
