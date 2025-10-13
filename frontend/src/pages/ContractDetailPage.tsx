import React, { useState, useEffect, useMemo } from 'react';
import { useParams } from 'react-router-dom';
import { Box, Typography, Paper, Grid, CircularProgress, Alert, Chip, Tooltip, Button, Tabs, Tab, Divider, List, ListItem, ListItemText, Drawer, IconButton } from '@mui/material';
import { DataGrid, GridToolbar } from '@mui/x-data-grid';
import type { GridColDef } from '@mui/x-data-grid';
import { styled } from '@mui/material/styles';
import { getContractById } from '../services/contractService';
import { Article, Gavel, Notifications, TextSnippet, Close } from '@mui/icons-material';

// --- Interfaces --- //
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
  condition: string | null;
  trigger_conditions: string | null;
  status: string;
  risk_level: string;
  last_checked: string | null;
  next_check: string | null;
  compliance_status: string;
  compliance_evidence: string | null;
  breach_count: number;
  last_breach_date: string | null;
  created_at: string;
  updated_at: string;
}
interface AlertData { id: string; title: string; message: string; severity: string; created_at: string; }
interface ContractDetails {
  id: string;
  title: string;
  party_a: string;
  party_b: string;
  status: string;
  contract_type: string;
  start_date: string;
  end_date: string;
  extracted_text: string;
  processing_status: string;
}

// --- Styled Components --- //
const StyledDataGrid = styled(DataGrid)(({ theme }) => ({
  border: 0,
  '& .MuiDataGrid-columnHeaders': {
    backgroundColor: theme.palette.grey[100],
    borderBottom: `1px solid ${theme.palette.grey[300]}`, 
  },
  '& .MuiDataGrid-row:nth-of-type(odd)': {
    backgroundColor: theme.palette.action.hover,
  },
  '& .MuiDataGrid-toolbarContainer': {
    padding: theme.spacing(1),
    borderBottom: `1px solid ${theme.palette.grey[300]}`,
  }
}));

const DetailItem = ({ label, value }: { label: string; value: React.ReactNode }) => (
    <ListItem sx={{ py: 1.5, px: 0 }}>
        <ListItemText
            primary={label}
            primaryTypographyProps={{ fontWeight: 'bold', color: 'text.secondary', width: '40%' }}
            secondary={value || 'N/A'}
            secondaryTypographyProps={{ component: 'div', color: 'text.primary', textAlign: 'left' }}
            sx={{ m: 0, display: 'flex', justifyContent: 'flex-start', alignItems: 'center' }}
        />
    </ListItem>
);

// --- Helper Functions --- //
const formatCurrency = (amount: number | null, currency: string | null = 'INR') => {
  if (amount === null || amount === undefined) return 'N/A';
  const effectiveCurrency = currency && currency !== 'null' ? currency : 'INR';
  try {
    return new Intl.NumberFormat('en-IN', { style: 'currency', currency: effectiveCurrency }).format(amount);
  } catch (e) {
    return `${amount} (Invalid Currency)`;
  }
};
const getStatusChipColor = (status: string): 'primary' | 'success' | 'error' | 'warning' | 'default' => {
    if (!status) return 'default';
    switch (status.toLowerCase()) {
        case 'active': return 'primary';
        case 'completed': return 'success';
        case 'breached': return 'error';
        case 'pending': return 'warning';
        case 'compliant': return 'success';
        case 'non_compliant': return 'error';
        default: return 'default';
    }
};
const getRiskChipColor = (riskLevel: string): 'success' | 'warning' | 'error' | 'default' => {
    if (!riskLevel) return 'default';
    switch (riskLevel.toLowerCase()) {
        case 'low': return 'success';
        case 'medium': return 'warning';
        case 'high': return 'error';
        case 'critical': return 'error';
        default: return 'default';
    }
};

// --- Main Component --- //
const ContractDetailPage: React.FC = () => {
  const { contractId } = useParams<{ contractId: string }>();
  const [data, setData] = useState<{ contract: ContractDetails; obligations: Obligation[]; alerts: AlertData[] } | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState('details');
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [selectedObligation, setSelectedObligation] = useState<Obligation | null>(null);

  const handleViewCondition = (obligation: Obligation) => {
    setSelectedObligation(obligation);
    setDrawerOpen(true);
  };

  const handleCloseDrawer = () => {
    setDrawerOpen(false);
  };

  useEffect(() => {
    if (contractId) {
      setLoading(true);
      getContractById(contractId)
        .then(response => {
            setData(response);
        })
        .catch(err => {
          setError('Failed to fetch contract details.');
          console.error(err);
        })
        .finally(() => setLoading(false));
    }
  }, [contractId]);

  const handleTabChange = (event: React.SyntheticEvent, newValue: string) => {
    setActiveTab(newValue);
  };

  const highlightedText = useMemo(() => {
    if (!data?.contract.extracted_text || !data?.obligations) return null;
    let text = data.contract.extracted_text;
    const descriptions = data.obligations.map(o => o.description).filter(Boolean);
    if(descriptions.length === 0) return text;
    const regex = new RegExp(`(${descriptions.map(d => d.replace(/[.*+?^${}()|[\\]/g, '\\$&')).join('|')})`, 'gi');
    return text.replace(regex, '<mark>$1</mark>');
  }, [data]);

  if (loading) return <Box sx={{ display: 'flex', justifyContent: 'center', p: 5 }}><CircularProgress /></Box>;
  if (error) return <Alert severity="error">{error}</Alert>;
  if (!data) return <Alert severity="info">No contract data found.</Alert>;

  const { contract, obligations, alerts } = data;

  const obligationColumns: GridColDef[] = [
    { field: 'obligation_type', headerName: 'Type', width: 150 },
    { field: 'description', headerName: 'Description', flex: 1, minWidth: 250 },
    { field: 'party', headerName: 'Party', width: 150 },
    { field: 'deadline', headerName: 'Next Deadline', width: 150, type: 'date', valueGetter: (value) => value ? new Date(value) : null },
    { field: 'status', headerName: 'Status', width: 120, renderCell: (params) => <Chip label={params.value} color={getStatusChipColor(params.value)} size="small" /> },
    { field: 'risk_level', headerName: 'Risk Level', width: 120, renderCell: (params) => <Chip label={params.value} color={getRiskChipColor(params.value)} size="small" /> },
    { field: 'penalty_amount', headerName: 'Penalty', type: 'number', width: 130, renderCell: (params) => formatCurrency(params.value, params.row.penalty_currency) },
    { field: 'rebate_amount', headerName: 'Rebate', type: 'number', width: 130, renderCell: (params) => formatCurrency(params.value, params.row.rebate_currency) },
    { field: 'compliance_status', headerName: 'Compliance', width: 130, renderCell: (params) => <Chip label={params.value} color={getStatusChipColor(params.value)} size="small" variant="outlined" /> },
    {
        field: 'condition',
        headerName: 'Condition',
        width: 150,
        sortable: false,
        renderCell: (params) => {
            return params.value ? (
                <Button variant="outlined" size="small" onClick={() => handleViewCondition(params.row as Obligation)}>
                    View
                </Button>
            ) : (
                <Typography variant="body2" color="text.secondary">N/A</Typography>
            );
        },
    },
  ];

  const alertColumns: GridColDef[] = [
      { field: 'severity', headerName: 'Severity', width: 120, renderCell: (params) => <Chip label={params.value} color={getRiskChipColor(params.value)} size="small" /> },
      { field: 'title', headerName: 'Title', flex: 1 },
      { field: 'created_at', headerName: 'Date', width: 180, type: 'dateTime', valueGetter: (value) => value && new Date(value) },
  ];

  return (
    <Box>
      <Paper elevation={0} sx={{ p: 3, mb: 3, border: '1px solid #e0e0e0', borderRadius: 2 }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <Box>
            <Typography variant="h4" fontWeight="bold">{contract.title}</Typography>
            <Typography variant="subtitle1" color="text.secondary">Contract ID: {contract.id}</Typography>
          </Box>
          <Chip label={contract.processing_status} color={getStatusChipColor(contract.processing_status)} />
        </Box>
        <Divider sx={{ my: 2 }} />
        <Box sx={{ display: 'flex', justifyContent: 'flex-end', gap: 1 }}>
            <Button variant="outlined">Reprocess</Button>
            <Button variant="outlined" color="error">Delete</Button>
        </Box>
      </Paper>

      <Paper elevation={0} sx={{ border: '1px solid #e0e0e0', borderRadius: 2 }}>
        <Tabs value={activeTab} onChange={handleTabChange} sx={{ borderBottom: 1, borderColor: 'divider' }}>
          <Tab icon={<Article />} iconPosition="start" label="Details" value="details" />
          <Tab icon={<Gavel />} iconPosition="start" label={`Obligations (${obligations.length})`} value="obligations" />
          <Tab icon={<Notifications />} iconPosition="start" label={`Alerts (${alerts.length})`} value="alerts" />
          <Tab icon={<TextSnippet />} iconPosition="start" label="Full Text" value="text" />
        </Tabs>

        <Box sx={{ p: activeTab.startsWith('grid') ? 0 : 3 }}>
            {activeTab === 'details' && (
                <Box>
                    <Typography variant="h6" gutterBottom>Key Information</Typography>
                    <Grid container spacing={2}>
                        <Grid item xs={12} md={6}>
                            <List dense>
                                <DetailItem label="Party A" value={contract.party_a} />
                                <DetailItem label="Contract Type" value={contract.contract_type} />
                                <DetailItem label="Start Date" value={contract.start_date ? new Date(contract.start_date).toLocaleDateString() : 'N/A'} />
                                <DetailItem label="Processing Status" value={<Chip label={contract.processing_status} color={getStatusChipColor(contract.processing_status)} size="small" />} />
                            </List>
                        </Grid>
                        <Grid item xs={12} md={6}>
                            <List dense>
                                <DetailItem label="Party B" value={contract.party_b} />
                                <DetailItem label="Contract Status" value={<Chip label={contract.status} color={getStatusChipColor(contract.status)} size="small" />} />
                                <DetailItem label="End Date" value={contract.end_date ? new Date(contract.end_date).toLocaleDateString() : 'N/A'} />
                            </List>
                        </Grid>
                    </Grid>
                </Box>
            )}

            {activeTab === 'obligations' && (
              <Box sx={{ height: 600, width: '100%' }}>
                <StyledDataGrid 
                    rows={obligations} 
                    columns={obligationColumns} 
                    getRowId={(row) => row.id} 
                    slots={{ toolbar: GridToolbar }}
                    slotProps={{
                        toolbar: {
                          showQuickFilter: true,
                        },
                    }}
                    disableRowSelectionOnClick 
                />
              </Box>
            )}

            {activeTab === 'alerts' && (
                <Box sx={{ height: 500, width: '100%' }}>
                    <StyledDataGrid rows={alerts} columns={alertColumns} getRowId={(row) => row.id} disableRowSelectionOnClick />
                </Box>
            )}
        </Box>
        {activeTab === 'text' && (
            <Box sx={{ p: 3, maxHeight: '600px', overflowY: 'auto', whiteSpace: 'pre-wrap', fontFamily: 'monospace', bgcolor: 'grey.50' }}>
                {highlightedText ? <div dangerouslySetInnerHTML={{ __html: highlightedText }} /> : <Typography>No text extracted.</Typography>}
            </Box>
        )}
      </Paper>

      <Drawer anchor="right" open={drawerOpen} onClose={handleCloseDrawer}>
        <Box sx={{ width: 400, p: 3 }}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center'}}>
                <Typography variant="h6">Obligation Condition</Typography>
                <IconButton onClick={handleCloseDrawer}><Close /></IconButton>
            </Box>
            <Divider sx={{ my: 2 }} />
            {selectedObligation ? (
                <Box>
                    <Typography variant="subtitle1" gutterBottom><strong>Type:</strong> {selectedObligation.obligation_type}</Typography>
                    <Typography variant="body1" sx={{ whiteSpace: 'pre-wrap', bgcolor: 'grey.100', p: 2, borderRadius: 1 }}>
                        {selectedObligation.condition}
                    </Typography>
                </Box>
            ) : (
                <Typography>No obligation selected.</Typography>
            )}
        </Box>
      </Drawer>

    </Box>
  );
};

export default ContractDetailPage;