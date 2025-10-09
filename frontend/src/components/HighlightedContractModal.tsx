import React from 'react';
import { Dialog, DialogTitle, DialogContent, DialogActions, Button, Typography, Box } from '@mui/material';

interface HighlightedContractModalProps {
  open: boolean;
  onClose: () => void;
  extractedText: string;
  obligations: { description: string }[]; // Simplified for highlighting
}

const HighlightedContractModal: React.FC<HighlightedContractModalProps> = ({ open, onClose, extractedText, obligations }) => {
  const escapeRegExp = (string: string) => {
    return string.replace(/[.*+?^${}()|[\\]\\]/g, '\\$&'); // $& means the whole matched string
  };

  const highlightText = (text: string, obligations: { description: string }[]) => {
    console.log("Full Extracted Text:", text);
    let highlightedContent = text;
    obligations.forEach(obligation => {
      const description = obligation.description;
      console.log("Attempting to highlight description:", description);
      if (description && description.length > 0) {
        // Escape special regex characters in the description
        const escapedDescription = escapeRegExp(description);
        
        // Use a regex to find all occurrences of the description and replace them with highlighted spans
        // The 'gi' flags mean global (all occurrences) and case-insensitive
        const regex = new RegExp(`(${escapedDescription})`, 'gi');
        highlightedContent = highlightedContent.replace(regex, '<span style="background-color: yellow; font-weight: bold;">$1</span>');
      }
    });
    return <div dangerouslySetInnerHTML={{ __html: highlightedContent }} />;
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth="md" fullWidth>
      <DialogTitle>Highlighted Contract Content</DialogTitle>
      <DialogContent dividers>
        <Box sx={{ whiteSpace: 'pre-wrap', fontFamily: 'monospace', fontSize: '0.875rem' }}>
          {highlightText(extractedText, obligations)}
        </Box>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Close</Button>
      </DialogActions>
    </Dialog>
  );
};

export default HighlightedContractModal;