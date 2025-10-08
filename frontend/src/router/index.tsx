
import React from 'react';
import { createBrowserRouter } from 'react-router-dom';
import AppLayout from '../layouts/AppLayout';
import { DashboardPage, ContractsPage, ObligationsPage, CopilotPage, AlertsPage, ReportsPage } from '../pages';

const router = createBrowserRouter([
  {
    path: '/',
    element: <AppLayout />,
    children: [
      { index: true, element: <DashboardPage /> },
      { path: 'contracts', element: <ContractsPage /> },
      { path: 'obligations', element: <ObligationsPage /> },
      { path: 'copilot', element: <CopilotPage /> },
      { path: 'alerts', element: <AlertsPage /> },
      { path: 'reports', element: <ReportsPage /> },
    ],
  },
]);

export default router;
