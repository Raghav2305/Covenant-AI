
import React, { useState } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  TextField,
  Box,
  Typography,
  CircularProgress,
  Alert
} from '@mui/material';
import { UploadFile } from '@mui/icons-material';
import { uploadContract } from '../services/contractService';

interface ContractUploadModalProps {
  open: boolean;
  onClose: () => void;
  onUploadSuccess: () => void;
}

const ContractUploadModal: React.FC<ContractUploadModalProps> = ({ open, onClose, onUploadSuccess }) => {
  const [file, setFile] = useState<File | null>(null);
  const [title, setTitle] = useState('');
  const [partyA, setPartyA] = useState('');
  const [partyB, setPartyB] = useState('');
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    if (event.target.files) {
      setFile(event.target.files[0]);
      setError(null);
    }
  };

  const resetForm = () => {
    setFile(null);
    setTitle('');
    setPartyA('');
    setPartyB('');
    setError(null);
    setIsUploading(false);
  };

  const handleClose = () => {
    resetForm();
    onClose();
  };

  const handleUpload = async () => {
    if (!file || !title || !partyA || !partyB) {
      setError('Please fill in all required fields and select a file.');
      return;
    }

    const formData = new FormData();
    formData.append('file', file);
    formData.append('title', title);
    formData.append('party_a', partyA);
    formData.append('party_b', partyB);

    setIsUploading(true);
    setError(null);

    try {
      await uploadContract(formData);
      resetForm();
      onUploadSuccess();
    } catch (err) { 
      setError('Upload failed. Please check the console for details.');
      console.error(err);
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <Dialog open={open} onClose={handleClose} maxWidth="sm" fullWidth>
      <DialogTitle>Upload New Contract</DialogTitle>
      <DialogContent>
        <Box component="form" sx={{ mt: 2, display: 'flex', flexDirection: 'column', gap: 3 }}>
          {error && <Alert severity="error">{error}</Alert>}
          <TextField
            label="Contract Title"
            variant="outlined"
            required
            fullWidth
            value={title}
            onChange={(e) => setTitle(e.target.value)}
          />
          <TextField
            label="Party A"
            variant="outlined"
            required
            fullWidth
            value={partyA}
            onChange={(e) => setPartyA(e.target.value)}
          />
          <TextField
            label="Party B"
            variant="outlined"
            required
            fullWidth
            value={partyB}
            onChange={(e) => setPartyB(e.target.value)}
          />
          <Button
            variant="outlined"
            component="label"
            startIcon={<UploadFile />}
          >
            Select Contract File
            <input type="file" hidden onChange={handleFileChange} />
          </Button>
          {file && <Typography variant="body2">Selected: {file.name}</Typography>}
        </Box>
      </DialogContent>
      <DialogActions sx={{ p: 3 }}>
        <Button onClick={handleClose} disabled={isUploading}>Cancel</Button>
        <Button onClick={handleUpload} variant="contained" disabled={isUploading}>
          {isUploading ? <CircularProgress size={24} /> : 'Upload and Process'}
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default ContractUploadModal;
