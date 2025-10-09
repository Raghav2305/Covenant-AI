
import React, { useState, useEffect } from 'react';
import { Box, Typography, Paper, Grid, CircularProgress, Alert, TextField, MenuItem, Select, InputLabel, FormControl, Chip, Tooltip, Card, CardContent } from '@mui/material';
import { DataGrid } from '@mui/x-data-grid';
import type { GridColDef } from '@mui/x-data-grid';
import { getObligations, getObligationsSummary } from '../services/obligationService';
import type { Obligation, ObligationFilters, ObligationSummary } from '../services/obligationService';
import { useNavigate } from 'react-router-dom';

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

const ObligationsPage: React.FC = () => {
  const [obligations, setObligations] = useState<Obligation[]>([]);
  const [summary, setSummary] = useState<ObligationSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [summaryLoading, setSummaryLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filters, setFilters] = useState<ObligationFilters>({});
  const navigate = useNavigate();

  const obligationColumns: GridColDef[] = [
    { field: 'obligation_id', headerName: 'Obligation ID', width: 150 },
    { field: 'party', headerName: 'Party', width: 150 },
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
    { 
      field: 'contract_id',
      headerName: 'Contract ID',
      width: 150,
      renderCell: (params) => (
        <Typography 
          variant="body2" 
          color="primary" 
          sx={{ cursor: 'pointer' }} 
          onClick={(event) => {
            event.stopPropagation(); // Prevent row click from firing
            navigate(`/contracts/${params.value}`);
          }}
        >
          {params.value}
        </Typography>
      ),
    },
  ];

  useEffect(() => {
    const fetchObligationsData = async () => {
      try {
        setLoading(true);
        const data = await getObligations(filters);
        setObligations(data);
        setError(null);
      } catch (err) {
        setError('Failed to fetch obligations.');
        console.error(err);
      } finally {
        setLoading(false);
      }
    };
    fetchObligationsData();
  }, [filters]); // Refetch when filters change

  useEffect(() => {
    const fetchSummaryData = async () => {
      try {
        setSummaryLoading(true);
        const data = await getObligationsSummary();
        setSummary(data);
      } catch (err) {
        console.error("Failed to fetch obligation summary:", err);
      } finally {
        setSummaryLoading(false);
      }
    };
    fetchSummaryData();
  }, []);

  const handleFilterChange = (event: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | { name?: string; value: unknown }>) => {
    const { name, value } = event.target;
    setFilters(prevFilters => ({
      ...prevFilters,
      [name as string]: value === '' ? undefined : value,
    }));
  };

  const getChipColorForSummary = (count: number, threshold: number, type: 'positive' | 'negative') => {
    if (type === 'negative') {
      return count > threshold ? 'error' : 'success';
    } else {
      return count > threshold ? 'success' : 'warning';
    }
  };

  return (
    <Box>
      <Typography variant="h4" gutterBottom>Obligation Management</Typography>
      
      {summaryLoading ? (
        <CircularProgress />
      ) : summary ? (
        <Grid container spacing={2} sx={{ mb: 3 }}>
          <Grid item xs={12} sm={6} md={3}>
            <Card>
              <CardContent>
                <Typography variant="subtitle2" color="textSecondary">Total Obligations</Typography>
                <Typography variant="h5">{summary.total_obligations}</Typography>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={12} sm={6} md={3}>
            <Card>
              <CardContent>
                <Typography variant="subtitle2" color="textSecondary">Active Obligations</Typography>
                <Typography variant="h5">{summary.status_distribution.active || 0}</Typography>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={12} sm={6} md={3}>
            <Card>
              <CardContent>
                <Typography variant="subtitle2" color="textSecondary">Overdue Obligations</Typography>
                <Typography variant="h5" color={getChipColorForSummary(summary.overdue_obligations, 0, 'negative')}>{summary.overdue_obligations}</Typography>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={12} sm={6} md={3}>
            <Card>
              <CardContent>
                <Typography variant="subtitle2" color="textSecondary">High Risk</Typography>
                <Typography variant="h5" color={getChipColorForSummary((summary.risk_distribution.high || 0) + (summary.risk_distribution.critical || 0), 0, 'negative')}>
                  {(summary.risk_distribution.high || 0) + (summary.risk_distribution.critical || 0)}
                </Typography>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      ) : (
        <Alert severity="warning" sx={{ mb: 3 }}>Could not load summary data.</Alert>
      )}

      <Paper sx={{ p: 2, mb: 3 }}>
        <Typography variant="h6" gutterBottom>Filters</Typography>
        <Grid container spacing={2}>
          <Grid item xs={12} sm={6} md={3}>
            <TextField
              label="Party"
              name="party"
              fullWidth
              value={filters.party || ''}
              onChange={handleFilterChange}
            />
          </Grid>
          <Grid item xs={12} sm={6} md={3}>
            <FormControl fullWidth>
              <InputLabel>Status</InputLabel>
              <Select
                label="Status"
                name="status"
                value={filters.status || ''}
                onChange={handleFilterChange}
              >
                <MenuItem value="">All</MenuItem>
                <MenuItem value="active">Active</MenuItem>
                <MenuItem value="completed">Completed</MenuItem>
                <MenuItem value="breached">Breached</MenuItem>
                <MenuItem value="pending">Pending</MenuItem>
              </Select>
            </FormControl>
          </Grid>
          <Grid item xs={12} sm={6} md={3}>
            <FormControl fullWidth>
              <InputLabel>Risk Level</InputLabel>
              <Select
                label="Risk Level"
                name="risk_level"
                value={filters.risk_level || ''}
                onChange={handleFilterChange}
              >
                <MenuItem value="">All</MenuItem>
                <MenuItem value="low">Low</MenuItem>
                <MenuItem value="medium">Medium</MenuItem>
                <MenuItem value="high">High</MenuItem>
                <MenuItem value="critical">Critical</MenuItem>
              </Select>
            </FormControl>
          </Grid>
          <Grid item xs={12} sm={6} md={3}>
            <FormControl fullWidth>
              <InputLabel>Obligation Type</InputLabel>
              <Select
                label="Obligation Type"
                name="obligation_type"
                value={filters.obligation_type || ''}
                onChange={handleFilterChange}
              >
                <MenuItem value="">All</MenuItem>
                <MenuItem value="Report Submission">Report Submission</MenuItem>
                <MenuItem value="Payment">Payment</MenuItem>
                <MenuItem value="SLA">SLA</MenuItem>
                {/* Add more types as needed */}
              </Select>
            </FormControl>
          </Grid>
        </Grid>
      </Paper>

      {loading && <CircularProgress />}
      {error && <Alert severity="error">{error}</Alert>}

      {!loading && !error && (
        <Paper sx={{ height: 600, width: '100%' }}>
          <DataGrid
            rows={obligations}
            columns={obligationColumns}
            getRowId={(row) => row.id}
            pageSizeOptions={[10, 25, 50]}
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
      )}
    </Box>
  );
};

export default ObligationsPage;
