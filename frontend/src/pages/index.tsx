
import React from 'react';
import { Typography } from '@mui/material';
import ContractsPage from './ContractsPage';
import ContractDetailPage from './ContractDetailPage';
import ObligationsPage from './ObligationsPage'; // Import the new ObligationsPage

// Define placeholder pages
const DashboardPage: React.FC = () => <Typography variant="h3">Dashboard</Typography>;
const CopilotPage: React.FC = () => <Typography variant="h3">AI Copilot</Typography>;
const AlertsPage: React.FC = () => <Typography variant="h3">Alerts & Notifications</Typography>;
const ReportsPage: React.FC = () => <Typography variant="h3">Reports</Typography>;

// Export all pages from one central place
export {
  DashboardPage,
  ContractsPage,
  ContractDetailPage,
  ObligationsPage, // Export the new ObligationsPage
  CopilotPage,
  AlertsPage,
  ReportsPage,
};
