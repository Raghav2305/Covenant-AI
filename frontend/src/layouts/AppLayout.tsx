import React from 'react';
import { Box, CssBaseline, AppBar, Toolbar, Typography, Drawer, List, ListItem, ListItemButton, ListItemIcon, ListItemText } from '@mui/material';
import { Dashboard, Description, Gavel, Chat, Notifications, Assessment } from '@mui/icons-material';
import { Link, Outlet } from 'react-router-dom';

const drawerWidth = 240;

const navItems = [
  { text: 'Dashboard', icon: <Dashboard />, path: '/' },
  { text: 'Contracts', icon: <Description />, path: '/contracts' },
  { text: 'Obligations', icon: <Gavel />, path: '/obligations' },
  { text: 'AI Copilot', icon: <Chat />, path: '/copilot' },
  { text: 'Alerts', icon: <Notifications />, path: '/alerts' },
  { text: 'Reports', icon: <Assessment />, path: '/reports' },
];

const AppLayout: React.FC = () => {
  return (
    <Box sx={{ display: 'flex' }}>
      <CssBaseline />
      <AppBar position="fixed" sx={{ zIndex: (theme) => theme.zIndex.drawer + 1 }}>
        <Toolbar>
          <Typography variant="h6" noWrap component="div">
            Contract AI Copilot
          </Typography>
        </Toolbar>
      </AppBar>
      <Drawer
        variant="permanent"
        sx={{
          width: drawerWidth,
          flexShrink: 0,
          [`& .MuiDrawer-paper`]: { width: drawerWidth, boxSizing: 'border-box' },
        }}
      >
        <Toolbar />
        <Box sx={{ overflow: 'auto' }}>
          <List>
            {navItems.map((item) => (
              <ListItem key={item.text} disablePadding>
                <ListItemButton component={Link} to={item.path}>
                  <ListItemIcon>{item.icon}</ListItemIcon>
                  <ListItemText primary={item.text} />
                </ListItemButton>
              </ListItem>
            ))}
          </List>
        </Box>
      </Drawer>
      <Box component="main" sx={{ flexGrow: 1, p: 3 }}>
        <Toolbar />
        <Outlet />
      </Box>
    </Box>
  );
};

export default AppLayout;