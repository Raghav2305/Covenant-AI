
import React, { useState, useEffect } from 'react';
import { Box, Typography, Button, Paper } from '@mui/material';
import { DataGrid } from '@mui/x-data-grid';
import type { GridColDef } from '@mui/x-data-grid';
import { Add } from '@mui/icons-material';
import type { Contract } from '../services/contractService';
import { getContracts } from '../services/contractService';
import ContractUploadModal from '../components/ContractUploadModal';

const columns: GridColDef[] = [
  { field: 'title', headerName: 'Title', width: 300 },
  { field: 'party_a', headerName: 'Party A', width: 200 },
  { field: 'party_b', headerName: 'Party B', width: 200 },
  { field: 'contract_type', headerName: 'Type', width: 150 },
  { field: 'processing_status', headerName: 'Status', width: 130 },
  {
    field: 'created_at',
    headerName: 'Upload Date',
    width: 180,
    renderCell: (params) => 
      params.value ? new Date(params.value).toLocaleString() : 'N/A',
  },
];

const ContractsPage: React.FC = () => {
  const [contracts, setContracts] = useState<Contract[]>([]);
  const [loading, setLoading] = useState(true);
  const [isModalOpen, setIsModalOpen] = useState(false);

  const fetchContracts = async () => {
    setLoading(true);
    const data = await getContracts();
    setContracts(data);
    setLoading(false);
  };

  useEffect(() => {
    fetchContracts();
  }, []);

  const handleUploadSuccess = () => {
    fetchContracts(); // Refresh the list after a successful upload
    setIsModalOpen(false);
  };

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h4">Contract Management</Typography>
        <Button variant="contained" startIcon={<Add />} onClick={() => setIsModalOpen(true)}>
          Upload Contract
        </Button>
      </Box>
      <Paper sx={{ height: 600, width: '100%' }}>
        <DataGrid
          rows={contracts}
          columns={columns}
          loading={loading}
          pageSizeOptions={[10, 25, 50]}
          getRowId={(row) => row.id}
        />
      </Paper>
      <ContractUploadModal
        open={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        onUploadSuccess={handleUploadSuccess}
      />
    </Box>
  );
};

export default ContractsPage;
