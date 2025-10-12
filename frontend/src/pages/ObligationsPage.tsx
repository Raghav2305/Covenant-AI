import React, { useState, useEffect, useMemo } from 'react';
import { Box, Typography, Paper, Grid, CircularProgress, Alert, TextField, MenuItem, Select, InputLabel, FormControl, Chip, Card, CardContent, Tooltip, Tabs, Tab, Table, TableBody, TableCell, TableContainer, TableHead, TableRow, TableSortLabel } from '@mui/material';
import { TabContext, TabList, TabPanel } from '@mui/lab';
import { Calendar, momentLocalizer } from 'react-big-calendar';
import moment from 'moment';
import 'react-big-calendar/lib/css/react-big-calendar.css';
import { PieChart, Pie, Cell, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip as RechartsTooltip, Legend, ResponsiveContainer } from 'recharts';

import { getObligations, getObligationsSummary } from '../services/obligationService';
import type { Obligation, ObligationFilters, ObligationSummary } from '../services/obligationService';
import { useNavigate } from 'react-router-dom';

const localizer = momentLocalizer(moment);

const CHART_COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#AF19FF'];

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
  const [tab, setTab] = useState('1');
  const [orderBy, setOrderBy] = useState<keyof Obligation>('deadline');
  const [order, setOrder] = useState<'asc' | 'desc'>('asc');
  const navigate = useNavigate();

  const handleTabChange = (event: React.SyntheticEvent, newValue: string) => {
    setTab(newValue);
  };

  const handleRequestSort = (property: keyof Obligation) => {
    const isAsc = orderBy === property && order === 'asc';
    setOrder(isAsc ? 'desc' : 'asc');
    setOrderBy(property);
  };

  const sortedObligations = useMemo(() => {
    return [...obligations].sort((a, b) => {
      const isAsc = order === 'asc';
      if (a[orderBy] < b[orderBy]) {
        return isAsc ? -1 : 1;
      }
      if (a[orderBy] > b[orderBy]) {
        return isAsc ? 1 : -1;
      }
      return 0;
    });
  }, [obligations, order, orderBy]);

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

  const events = useMemo(() =>
    obligations
      .filter(obl => obl.deadline) // Filter out obligations without a deadline
      .map(obl => ({
        id: obl.id,
        title: `${obl.obligation_type} - ${obl.party}`,
        start: moment(obl.deadline).toDate(),
        end: moment(obl.deadline).toDate(),
        allDay: true,
        resource: obl,
      })),
    [obligations]
  );

  const EventComponent = ({ event }: any) => (
    <Tooltip title={event.resource.description}>
      <Box sx={{ backgroundColor: getRiskChipColor(event.resource.risk_level), color: 'white', padding: '2px 5px', borderRadius: '3px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
        {event.title}
      </Box>
    </Tooltip>
  );

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
        <Paper sx={{ p: 2, mt: 3 }}>
          <TabContext value={tab}>
            <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
              <TabList onChange={handleTabChange} aria-label="obligation views">
                <Tab label="Calendar View" value="1" />
                <Tab label="Table View" value="2" />
                <Tab label="Timeline View" value="3" />
                <Tab label="Dashboard" value="4" />
              </TabList>
            </Box>
            <TabPanel value="1">
              <Box sx={{ height: 600 }}>
                <Calendar
                  localizer={localizer}
                  events={events}
                  startAccessor="start"
                  endAccessor="end"
                  style={{ height: '100%' }}
                  components={{
                    event: EventComponent,
                  }}
                  onSelectEvent={(event) => navigate(`/contracts/${event.resource.contract_id}`)}
                />
              </Box>
            </TabPanel>
            <TabPanel value="2">
              <TableContainer>
                <Table stickyHeader>
                  <TableHead>
                    <TableRow>
                      <TableCell sortDirection={orderBy === 'deadline' ? order : false}>
                        <TableSortLabel
                          active={orderBy === 'deadline'}
                          direction={orderBy === 'deadline' ? order : 'asc'}
                          onClick={() => handleRequestSort('deadline')}
                        >
                          Deadline
                        </TableSortLabel>
                      </TableCell>
                      <TableCell>Description</TableCell>
                      <TableCell>Party</TableCell>
                      <TableCell>Type</TableCell>
                      <TableCell>Risk Level</TableCell>
                      <TableCell>Status</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {sortedObligations.map((obl) => (
                      <TableRow
                        key={obl.id}
                        hover
                        onClick={() => navigate(`/contracts/${obl.contract_id}`)}
                        sx={{ cursor: 'pointer' }}
                      >
                        <TableCell>{obl.deadline ? moment(obl.deadline).format('YYYY-MM-DD') : 'N/A'}</TableCell>
                        <TableCell>{obl.description}</TableCell>
                        <TableCell>{obl.party}</TableCell>
                        <TableCell>{obl.obligation_type}</TableCell>
                        <TableCell>
                          <Chip label={obl.risk_level} color={getRiskChipColor(obl.risk_level)} size="small" />
                        </TableCell>
                        <TableCell>
                          <Chip label={obl.status} color={getStatusChipColor(obl.status)} size="small" />
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
            </TabPanel>
            <TabPanel value="3">
              <Box sx={{ my: 2 }}>
                <Alert severity="info">
                  The timeline view is a planned feature. It will provide an interactive, chronological visualization of all contract obligations and key milestones.
                </Alert>
              </Box>
            </TabPanel>
            <TabPanel value="4">
              {summary ? (
                <Box>
                  <Card sx={{ mb: 3 }}>
                    <CardContent>
                      <Typography variant="h6" gutterBottom align="center">Status Distribution</Typography>
                      <ResponsiveContainer width="100%" height={300}>
                        <PieChart>
                          <Pie
                            data={Object.entries(summary.status_distribution).map(([name, value]) => ({ name, value }))}
                            cx="50%"
                            cy="50%"
                            labelLine={false}
                            outerRadius={120}
                            fill="#8884d8"
                            dataKey="value"
                          >
                            {Object.entries(summary.status_distribution).map(([name, value], index) => (
                              <Cell key={`cell-${index}`} fill={CHART_COLORS[index % CHART_COLORS.length]} />
                            ))}
                          </Pie>
                          <RechartsTooltip />
                          <Legend />
                        </PieChart>
                      </ResponsiveContainer>
                    </CardContent>
                  </Card>
                  <Card>
                    <CardContent>
                      <Typography variant="h6" gutterBottom align="center">Risk Distribution</Typography>
                      <ResponsiveContainer width="100%" height={300}>
                        <BarChart data={Object.entries(summary.risk_distribution).map(([name, value]) => ({ name, value }))}>
                          <CartesianGrid strokeDasharray="3 3" />
                          <XAxis dataKey="name" />
                          <YAxis />
                          <RechartsTooltip />
                          <Bar dataKey="value">
                            {Object.entries(summary.risk_distribution).map(([name, value], index) => (
                              <Cell key={`cell-${index}`} fill={getRiskChipColor(name)} />
                            ))}
                          </Bar>
                        </BarChart>
                      </ResponsiveContainer>
                    </CardContent>
                  </Card>
                </Box>
              ) : (
                <Typography>Summary data not available for charts.</Typography>
              )}
            </TabPanel>
          </TabContext>
        </Paper>
      )}
    </Box>
  );
};

export default ObligationsPage;