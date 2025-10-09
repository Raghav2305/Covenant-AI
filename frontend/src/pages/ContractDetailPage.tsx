import React, { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { Box, Typography, Paper, Grid, CircularProgress, Alert, Card, CardContent, Chip, Tooltip, Button } from '@mui/material';
import { DataGrid } from '@mui/x-data-grid';
import type { GridColDef } from '@mui/x-data-grid';
import { getContractById } from '../services/contractService';
import HighlightedContractModal from '../components/HighlightedContractModal'; // Import the new modal

// Expanded interface to include ALL fields from the backend Obligation model
interface Obligation {
  id: string;
  contract_id: string;
  obligation_id: string;
  party: string;
  obligation_type: string;
  description: string;
  deadline: string | null;
  frequency: string | null;
  penalty_amount: number | null;
  rebate_amount: number | null;
  penalty_currency: string | null;
  rebate_currency: string | null;
  condition: string | null; // Assuming JSON as text
  trigger_conditions: string | null; // Assuming JSON as text
  status: string;
  risk_level: string;
  last_checked: string | null;
  next_check: string | null;
  compliance_status: string;
  compliance_evidence: string | null; // Assuming JSON as text
  breach_count: number;
  last_breach_date: string | null;
  created_at: string;
  updated_at: string;
}

interface ContractDetails {
  id: string;
  title: string;
  party_a: string;
  party_b: string;
  status: string;
  contract_type: string;
  start_date: string;
  end_date: string;
  extracted_text: string; // Added extracted_text
}

// Function to format currency
const formatCurrency = (amount: number | null, currency: string = 'INR') => {
  if (amount === null || amount === undefined) return 'N/A';
  return new Intl.NumberFormat('en-IN', { style: 'currency', currency }).format(amount);
};

const getStatusChipColor = (status: string) => {
  switch (status.toLowerCase()) {
    case 'active': return 'primary';
    case 'completed': return 'success';
    case 'breached': return 'error';
    case 'pending': return 'warning';
    default: return 'default';
  }
};

const getRiskChipColor = (riskLevel: string) => {
  switch (riskLevel.toLowerCase()) {
    case 'low': return 'success';
    case 'medium': return 'warning';
    case 'high': return 'error';
    case 'critical': return 'error';
    default: return 'default';
  }
};

const obligationColumns: GridColDef[] = [
  { field: 'obligation_type', headerName: 'Type', width: 150 },
  { field: 'description', headerName: 'Description', flex: 1, minWidth: 200 },
  { 
    field: 'penalty_amount',
    headerName: 'Penalty',
    type: 'number',
    width: 130,
    renderCell: (params) => formatCurrency(params.value, params.row.penalty_currency || undefined)
  },
  { 
    field: 'rebate_amount',
    headerName: 'Rebate',
    type: 'number',
    width: 130,
    renderCell: (params) => formatCurrency(params.value, params.row.rebate_currency || undefined)
  },
  { 
    field: 'deadline',
    headerName: 'Next Deadline',
    width: 150,
    renderCell: (params) => params.value ? new Date(params.value).toLocaleDateString() : 'N/A'
  },
  { 
    field: 'frequency',
    headerName: 'Frequency',
    width: 120,
    renderCell: (params) => params.value || 'One-time'
  },
  { 
    field: 'status',
    headerName: 'Status',
    width: 120,
    renderCell: (params) => (
      <Chip label={params.value} color={getStatusChipColor(params.value)} size="small" />
    ),
  },
  { 
    field: 'risk_level',
    headerName: 'Risk Level',
    width: 120,
    renderCell: (params) => (
      <Chip label={params.value} color={getRiskChipColor(params.value)} size="small" />
    ),
  },
  { 
    field: 'condition',
    headerName: 'Condition',
    flex: 1,
    minWidth: 250,
    renderCell: (params) => (
      <Tooltip title={params.value || 'N/A'}>
        <Typography variant="body2" noWrap>{params.value || 'N/A'}</Typography>
      </Tooltip>
    ),
  },
];

const ContractDetailPage: React.FC = () => {
  const { contractId } = useParams<{ contractId: string }>();
  const [contract, setContract] = useState<ContractDetails | null>(null);
  const [obligations, setObligations] = useState<Obligation[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false); // State for the new modal

  useEffect(() => {
    if (contractId) {
      const fetchContractDetails = async () => {
        try {
          setLoading(true);
          const data = await getContractById(contractId);
          setContract(data.contract);
          setObligations(data.obligations);
          console.log("Fetched contract object:", data.contract); // Log the fetched contract
          setError(null);
        } catch (err) {
          setError('Failed to fetch contract details.');
          console.error(err);
        } finally {
          setLoading(false);
        }
      };
      fetchContractDetails();
    }
  }, [contractId]);

  if (loading) {
    return <CircularProgress />;
  }

  if (error) {
    return <Alert severity="error">{error}</Alert>;
  }

  if (!contract) {
    return <Alert severity="info">No contract data found.</Alert>;
  }

  console.log("ContractDetailPage is rendering.");

  return (
    <Box>
      <Typography variant="h4" gutterBottom>{contract.title}</Typography>
      
      <Grid container spacing={3} sx={{ mb: 3 }}>
        <Grid item xs={12} md={6}><Card><CardContent><Typography variant="subtitle2">Party A</Typography><Typography>{contract.party_a}</Typography></CardContent></Card></Grid>
        <Grid item xs={12} md={6}><Card><CardContent><Typography variant="subtitle2">Party B</Typography><Typography>{contract.party_b}</Typography></CardContent></Card></Grid>
        <Grid item xs={6} sm={3}><Card><CardContent><Typography variant="subtitle2">Status</Typography><Chip label={contract.status} color="primary" /></CardContent></Card></Grid>
        <Grid item xs={6} sm={3}><Card><CardContent><Typography variant="subtitle2">Type</Typography><Typography>{contract.contract_type || 'N/A'}</Typography></CardContent></Card></Grid>
        <Grid item xs={6} sm={3}><Card><CardContent><Typography variant="subtitle2">Start Date</Typography><Typography>{contract.start_date ? new Date(contract.start_date).toLocaleDateString() : 'N/A'}</Typography></CardContent></Card></Grid>
        <Grid item xs={6} sm={3}><Card><CardContent><Typography variant="subtitle2">End Date</Typography><Typography>{contract.end_date ? new Date(contract.end_date).toLocaleDateString() : 'N/A'}</Typography></CardContent></Card></Grid>
        <Grid item xs={12}>
          <Button variant="contained" onClick={() => setIsModalOpen(true)}>
            View Highlighted Contract Text
          </Button>
        </Grid>
      </Grid>

      <Typography variant="h5" gutterBottom sx={{ mt: 4 }}>Extracted Obligations</Typography>
      <Paper sx={{ height: 500, width: '100%' }}>
        <DataGrid
          rows={obligations}
          columns={obligationColumns}
          getRowId={(row) => row.id}
          pageSizeOptions={[5, 10, 20]}
          density="comfortable"
          sx={{
            '& .MuiDataGrid-columnHeaders': {
              backgroundColor: '#f5f5f5',
              fontWeight: 'bold',
            },
            '& .MuiDataGrid-row:nth-of-type(odd)': {
              backgroundColor: '#f9f9f9',
            },
          }}
        />
      </Paper>
      {contract.extracted_text && (
        console.log("Rendering modal. isModalOpen:", isModalOpen, "extracted_text length:", contract.extracted_text.length),
        <HighlightedContractModal
          open={isModalOpen}
          onClose={() => setIsModalOpen(false)}
          extractedText={contract.extracted_text}
          obligations={obligations}
        />
      )}
    </Box>
  );
};

export default ContractDetailPage;