import React from 'react';
import { Typography } from '@mui/material';
import ContractsPage from './ContractsPage';
import ContractDetailPage from './ContractDetailPage';

// Define placeholder pages
const DashboardPage: React.FC = () => <Typography variant="h3">Dashboard</Typography>;
const ObligationsPage: React.FC = () => <Typography variant="h3">Obligation Management</Typography>;
const CopilotPage: React.FC = () => <Typography variant="h3">AI Copilot</Typography>;
const AlertsPage: React.FC = () => <Typography variant="h3">Alerts & Notifications</Typography>;
const ReportsPage: React.FC = () => <Typography variant="h3">Reports</Typography>;

// Export all pages from one central place
export {
  DashboardPage,
  ContractsPage,
  ContractDetailPage,
  ObligationsPage,
  CopilotPage,
  AlertsPage,
  ReportsPage,
};