import React, { useState, useEffect, useMemo } from 'react';
import { Box, Typography, Button, Paper, Chip, TextField, InputAdornment, ToggleButtonGroup, ToggleButton, CircularProgress } from '@mui/material';
import { DataGrid } from '@mui/x-data-grid';
import type { GridColDef } from '@mui/x-data-grid';
import { Add, Search, UploadFile } from '@mui/icons-material';
import { useNavigate } from 'react-router-dom';
import type { Contract } from '../services/contractService';
import { getContracts } from '../services/contractService';
import ContractUploadModal from '../components/ContractUploadModal';
import { styled } from '@mui/material/styles';

const getStatusChipColor = (status: string): 'success' | 'warning' | 'error' | 'default' => {
  switch (status.toLowerCase()) {
    case 'completed':
      return 'success';
    case 'processing':
      return 'warning';
    case 'failed':
      return 'error';
    default:
      return 'default';
  }
};

const StyledDataGrid = styled(DataGrid)(({ theme }) => ({
  border: 0,
  '& .MuiDataGrid-columnHeaders': {
    backgroundColor: theme.palette.grey[100],
    borderBottom: `1px solid ${theme.palette.grey[300]}`,
    fontWeight: 'bold',
  },
  '& .MuiDataGrid-row': {
    cursor: 'pointer',
    '&:nth-of-type(odd)': {
      backgroundColor: theme.palette.action.hover,
    },
    '&:hover': {
      backgroundColor: theme.palette.action.selected,
    }
  },
  '& .MuiDataGrid-cell': {
    borderBottom: `1px solid ${theme.palette.grey[200]}`,
  },
}));

const CustomNoRowsOverlay = () => (
  <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '100%' }}>
    <UploadFile sx={{ fontSize: 60, color: 'grey.400' }} />
    <Typography variant="h6" sx={{ mt: 2 }}>No Contracts Found</Typography>
    <Typography sx={{ color: 'grey.600' }}>Get started by uploading your first contract.</Typography>
  </Box>
);

const ContractsPage: React.FC = () => {
  const [contracts, setContracts] = useState<Contract[]>([]);
  const [loading, setLoading] = useState(true);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [searchText, setSearchText] = useState('');
  const [statusFilter, setStatusFilter] = useState<string | null>('all');
  const navigate = useNavigate();

  const columns: GridColDef[] = [
    { field: 'title', headerName: 'Title', flex: 1, minWidth: 250 },
    { field: 'party_a', headerName: 'Party A', flex: 0.7, minWidth: 180 },
    { field: 'party_b', headerName: 'Party B', flex: 0.7, minWidth: 180 },
    { field: 'contract_type', headerName: 'Type', width: 150 },
    {
      field: 'processing_status',
      headerName: 'Status',
      width: 130,
      renderCell: (params) => (
        <Chip
          label={params.value}
          color={getStatusChipColor(params.value)}
          size="small"
          variant="outlined"
        />
      ),
    },
    {
      field: 'created_at',
      headerName: 'Upload Date',
      width: 180,
      type: 'dateTime',
      valueGetter: (value) => value && new Date(value),
    },
  ];

  const handleRowClick = (params: any) => {
    navigate(`/contracts/${params.id}`);
  };

  const fetchContracts = async () => {
    setLoading(true);
    try {
      const data = await getContracts();
      setContracts(data);
    } catch (error) {
      console.error("Failed to fetch contracts:", error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchContracts();
  }, []);

  const handleUploadSuccess = () => {
    fetchContracts();
    setIsModalOpen(false);
  };

  const handleStatusFilterChange = (event: React.MouseEvent<HTMLElement>, newFilter: string | null) => {
    if (newFilter !== null) {
      setStatusFilter(newFilter);
    }
  };

  const filteredContracts = useMemo(() => {
    return contracts.filter((contract) => {
      const matchesSearch = [contract.title, contract.party_a, contract.party_b]
        .some(field => field.toLowerCase().includes(searchText.toLowerCase()));
      
      const matchesStatus = statusFilter === 'all' || contract.processing_status.toLowerCase() === statusFilter;

      return matchesSearch && matchesStatus;
    });
  }, [contracts, searchText, statusFilter]);

  return (
    <Paper elevation={3} sx={{ p: 3, borderRadius: 2 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2, flexWrap: 'wrap', gap: 2 }}>
        <Typography variant="h4" sx={{ fontWeight: 'bold', color: 'primary.main' }}>
          Contract Management
        </Typography>
        <Button variant="contained" startIcon={<Add />} onClick={() => setIsModalOpen(true)}>
          Upload Contract
        </Button>
      </Box>

      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 2, flexWrap: 'wrap', gap: 2 }}>
        <TextField
          variant="outlined"
          size="small"
          placeholder="Search by title or party..."
          value={searchText}
          onChange={(e) => setSearchText(e.target.value)}
          InputProps={{
            startAdornment: (
              <InputAdornment position="start">
                <Search />
              </InputAdornment>
            ),
          }}
          sx={{ minWidth: '300px' }}
        />
        <ToggleButtonGroup
          value={statusFilter}
          exclusive
          onChange={handleStatusFilterChange}
          aria-label="status filter"
          size="small"
        >
          <ToggleButton value="all" aria-label="all">All</ToggleButton>
          <ToggleButton value="completed" aria-label="completed">Completed</ToggleButton>
          <ToggleButton value="processing" aria-label="processing">Processing</ToggleButton>
          <ToggleButton value="failed" aria-label="failed">Failed</ToggleButton>
        </ToggleButtonGroup>
      </Box>

      <Box sx={{ height: 600, width: '100%' }}>
        <StyledDataGrid
          rows={filteredContracts}
          columns={columns}
          loading={loading}
          pageSizeOptions={[10, 25, 50]}
          getRowId={(row) => row.id}
          onRowClick={handleRowClick}
          slots={{
            noRowsOverlay: CustomNoRowsOverlay,
            loadingOverlay: () => <CircularProgress />,
          }}
          disableRowSelectionOnClick
        />
      </Box>

      <ContractUploadModal
        open={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        onUploadSuccess={handleUploadSuccess}
      />
    </Paper>
  );
};

export default ContractsPage;
