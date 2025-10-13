import React, { useState, useEffect, useMemo, useCallback } from 'react';
import { Box, Typography, Paper, Grid, CircularProgress, Alert, TextField, MenuItem, Select, InputLabel, FormControl, Chip, Card, CardContent, Tooltip, Tabs, Tab, List, ListItem, ListItemText, ListSubheader, Divider, Button, Drawer, IconButton } from '@mui/material';
import { TabContext, TabList, TabPanel } from '@mui/lab';
import { Calendar, momentLocalizer, Views } from 'react-big-calendar';
import moment from 'moment';
import 'react-big-calendar/lib/css/react-big-calendar.css';
import { PieChart, Pie, Cell, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip as RechartsTooltip, Legend, ResponsiveContainer } from 'recharts';
import { DataGrid, GridToolbar } from '@mui/x-data-grid';
import type { GridColDef } from '@mui/x-data-grid';
import { styled } from '@mui/material/styles';
import { useNavigate } from 'react-router-dom';
import { Timeline, TimelineItem, TimelineSeparator, TimelineConnector, TimelineContent, TimelineDot, TimelineOppositeContent } from '@mui/lab';

import { getObligations, getObligationsSummary } from '../services/obligationService';
import type { Obligation, ObligationFilters, ObligationSummary } from '../services/obligationService';
import { Gavel, Event, Timeline as TimelineIcon, Dashboard, Close, AssignmentTurnedIn, ErrorOutline, WarningAmber, AccountBalanceWallet, ChevronLeft, ChevronRight } from '@mui/icons-material';

const localizer = momentLocalizer(moment);
const CHART_COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#AF19FF'];

// --- Helper Functions ---
const getStatusChipColor = (status: string): 'primary' | 'success' | 'error' | 'warning' | 'default' => {
    if (!status) return 'default';
    switch (status.toLowerCase()) {
        case 'active': return 'primary';
        case 'completed': return 'success';
        case 'breached': return 'error';
        case 'pending': return 'warning';
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
const formatCurrency = (amount: number | null, currency: string | null = 'INR') => {
    if (amount === null || amount === undefined) return 'N/A';
    const effectiveCurrency = currency && currency !== 'null' ? currency : 'INR';
    try {
        return new Intl.NumberFormat('en-IN', { style: 'currency', currency: effectiveCurrency }).format(amount);
    } catch (e) {
        return `${amount} (Invalid Currency)`;
    }
};

// --- Styled Components ---
const StyledDataGrid = styled(DataGrid)(({ theme }) => ({ 
    border: 0,
    '& .MuiDataGrid-columnHeaders': {
        backgroundColor: theme.palette.grey[100],
        borderBottom: `1px solid ${theme.palette.grey[300]}`,
    },
    '& .MuiDataGrid-row:nth-of-type(odd)': {
        backgroundColor: theme.palette.action.hover,
    },
 }));

const SummaryCard = ({ title, value, icon, color }: { title: string, value: string | number, icon: React.ReactElement, color?: string }) => (
    <Card elevation={2}>
        <CardContent sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <Box>
                <Typography variant="subtitle1" color="text.secondary">{title}</Typography>
                <Typography variant="h4" fontWeight="bold" color={color}>{value}</Typography>
            </Box>
            {React.cloneElement(icon, { sx: { fontSize: 40, color: color || 'text.secondary', opacity: 0.8 } })}
        </CardContent>
    </Card>
);

const CustomCalendarToolbar = (toolbar: any) => {
    const goToBack = () => toolbar.onNavigate('PREV');
    const goToNext = () => toolbar.onNavigate('NEXT');
    const goToCurrent = () => toolbar.onNavigate('TODAY');
  
    return (
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2, p: 1 }}>
        <Box>
            <IconButton onClick={goToBack}><ChevronLeft /></IconButton>
            <Button onClick={goToCurrent}>Today</Button>
            <IconButton onClick={goToNext}><ChevronRight /></IconButton>
        </Box>
        <Typography variant="h6">{toolbar.label}</Typography>
        <Box sx={{width: 150}} />
      </Box>
    );
  };

const ObligationsPage: React.FC = () => {
  const [obligations, setObligations] = useState<Obligation[]>([]);
  const [summary, setSummary] = useState<ObligationSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filters, setFilters] = useState<ObligationFilters>({});
  const [tab, setTab] = useState('dashboard');
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [selectedObligation, setSelectedObligation] = useState<Obligation | null>(null);
  const [calendarDate, setCalendarDate] = useState(new Date());
  const navigate = useNavigate();

  // --- Data Fetching ---
  useEffect(() => {
    const fetchAllData = async () => {
      try {
        setLoading(true);
        const [obligationsData, summaryData] = await Promise.all([
          getObligations(filters),
          getObligationsSummary(),
        ]);
        setObligations(obligationsData);
        setSummary(summaryData);
        setError(null);
      } catch (err) {
        setError('Failed to fetch obligation data.');
        console.error(err);
      } finally {
        setLoading(false);
      }
    };
    fetchAllData();
  }, [filters]);

  // --- Handlers ---
  const handleTabChange = (event: React.SyntheticEvent, newValue: string) => setTab(newValue);
  const handleFilterChange = (event: any) => {
    const { name, value } = event.target;
    setFilters(prev => ({ ...prev, [name as string]: value === '' ? undefined : value }));
  };
  const handleViewCondition = (obligation: Obligation) => {
    setSelectedObligation(obligation);
    setDrawerOpen(true);
  };
  const handleCloseDrawer = () => setDrawerOpen(false);
  const handleCalendarNavigate = useCallback((newDate: Date) => setCalendarDate(newDate), []);

  // --- Memoized Calculations ---
  const financialExposure = useMemo(() => 
    obligations.reduce((acc, obl) => acc + (obl.penalty_amount || 0), 0),
  [obligations]);

  const calendarEvents = useMemo(() =>
    obligations.filter(obl => obl.deadline).map(obl => ({
        id: obl.id,
        title: `${obl.obligation_type} - ${obl.party}`,
        start: moment(obl.deadline).toDate(),
        end: moment(obl.deadline).toDate(),
        allDay: true,
        resource: obl,
    })),
  [obligations]);

  // --- Column Definitions ---
  const obligationColumns: GridColDef[] = [
    { field: 'description', headerName: 'Description', flex: 1, minWidth: 250 },
    { field: 'party', headerName: 'Party', width: 180 },
    { field: 'deadline', headerName: 'Deadline', type: 'date', width: 120, valueGetter: (value) => value ? new Date(value) : null },
    { field: 'status', headerName: 'Status', width: 120, renderCell: (params) => <Chip label={params.value} color={getStatusChipColor(params.value)} size="small" /> },
    { field: 'risk_level', headerName: 'Risk', width: 100, renderCell: (params) => <Chip label={params.value} color={getRiskChipColor(params.value)} size="small" /> },
    { field: 'condition', headerName: 'Condition', width: 120, sortable: false, renderCell: (params) => params.value ? <Button size="small" onClick={() => handleViewCondition(params.row as Obligation)}>View</Button> : 'N/A' },
  ];

  // --- Render Logic ---
  if (loading) return <CircularProgress />;
  if (error) return <Alert severity="error">{error}</Alert>;

  return (
    <Box>
        <Typography variant="h4" fontWeight="bold" gutterBottom>Obligations Command Center</Typography>
        
        {summary && (
            <Grid container spacing={3} sx={{ mb: 3 }}>
                <Grid item xs={12} sm={6} md={3}><SummaryCard title="Total Obligations" value={summary.total_obligations} icon={<Gavel />} /></Grid>
                <Grid item xs={12} sm={6} md={3}><SummaryCard title="Active" value={summary.status_distribution.active || 0} icon={<AssignmentTurnedIn />} color="primary.main" /></Grid>
                <Grid item xs={12} sm={6} md={3}><SummaryCard title="Overdue" value={summary.overdue_obligations} icon={<ErrorOutline />} color="error.main" /></Grid>
                <Grid item xs={12} sm={6} md={3}><SummaryCard title="High/Critical Risk" value={(summary.risk_distribution.high || 0) + (summary.risk_distribution.critical || 0)} icon={<WarningAmber />} color="warning.main" /></Grid>
            </Grid>
        )}

        <Paper elevation={2} sx={{ p: 2, mb: 3 }}>
            {/* Filter controls here */}
        </Paper>

        <Paper elevation={2}>
            <TabContext value={tab}>
                <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
                    <TabList onChange={handleTabChange} centered>
                        <Tab icon={<Dashboard />} iconPosition="start" label="Dashboard" value="dashboard" />
                        <Tab icon={<Event />} iconPosition="start" label="Calendar" value="calendar" />
                        <Tab icon={<Gavel />} iconPosition="start" label="Table" value="table" />
                        <Tab icon={<TimelineIcon />} iconPosition="start" label="Timeline" value="timeline" />
                    </TabList>
                </Box>
                <TabPanel value="dashboard" sx={{ p: 3 }}><DashboardView summary={summary} financialExposure={financialExposure} /></TabPanel>
                <TabPanel value="calendar" sx={{ height: 700, p: 0 }}><CalendarView events={calendarEvents} navigate={navigate} date={calendarDate} onNavigate={handleCalendarNavigate} /></TabPanel>
                <TabPanel value="table">
                    <Box sx={{ height: 600, width: '100%' }}>
                        <StyledDataGrid rows={obligations} columns={obligationColumns} slots={{ toolbar: GridToolbar }} disableRowSelectionOnClick />
                    </Box>
                </TabPanel>
                <TabPanel value="timeline" sx={{bgcolor: 'grey.50'}}><TimelineView obligations={obligations} /></TabPanel>
            </TabContext>
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

// --- Sub-components for each tab ---
const DashboardView = ({ summary, financialExposure }: { summary: ObligationSummary | null, financialExposure: number }) => (
    <Box>
        <Grid container spacing={3}>
            <Grid item xs={12}>
                <Card>
                    <CardContent>
                        <Typography variant="h6">Obligations by Type</Typography>
                        <Box sx={{ height: 300 }}>
                            <ResponsiveContainer width="100%" height="100%">
                                <BarChart data={Object.entries(summary?.type_distribution || {}).map(([name, value]) => ({ name, value }))} margin={{ top: 5, right: 30, left: 20, bottom: 70 }}>
                                    <CartesianGrid strokeDasharray="3 3" />
                                    <XAxis dataKey="name" angle={-45} textAnchor="end" interval={0} height={100} />
                                    <YAxis />
                                    <Tooltip />
                                    <Bar dataKey="value" fill="#82ca9d" />
                                </BarChart>
                            </ResponsiveContainer>
                        </Box>
                    </CardContent>
                </Card>
            </Grid>
            <Grid item xs={12} md={6}>
                <Card>
                    <CardContent>
                        <Typography variant="h6">Obligations by Status</Typography>
                        <Box sx={{ height: 300 }}>
                            <ResponsiveContainer width="100%" height="100%">
                                <PieChart>
                                    <Pie data={Object.entries(summary?.status_distribution || {}).map(([name, value]) => ({ name, value }))} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={100} label>
                                        {Object.entries(summary?.status_distribution || {}).map((_, index) => (
                                            <Cell key={`cell-${index}`} fill={CHART_COLORS[index % CHART_COLORS.length]} />
                                        ))}
                                    </Pie>
                                    <Tooltip />
                                    <Legend />
                                </PieChart>
                            </ResponsiveContainer>
                        </Box>
                    </CardContent>
                </Card>
            </Grid>
            <Grid item xs={12} md={6}>
                <Card>
                    <CardContent>
                        <Typography variant="h6">Obligations by Risk</Typography>
                        <Box sx={{ height: 300 }}>
                            <ResponsiveContainer width="100%" height="100%">
                                <BarChart data={Object.entries(summary?.risk_distribution || {}).map(([name, value]) => ({ name, value }))}>
                                    <CartesianGrid strokeDasharray="3 3" />
                                    <XAxis dataKey="name" />
                                    <YAxis />
                                    <Tooltip />
                                    <Bar dataKey="value">
                                        {Object.entries(summary?.risk_distribution || {}).map(([name]) => (
                                            <Cell key={`cell-${name}`} fill={getRiskChipColor(name)} />
                                        ))}
                                    </Bar>
                                </BarChart>
                            </ResponsiveContainer>
                        </Box>
                    </CardContent>
                </Card>
            </Grid>
             <Grid item xs={12}>
                <SummaryCard title="Total Penalty Exposure" value={formatCurrency(financialExposure)} icon={<AccountBalanceWallet />} color="error.main" />
            </Grid>
        </Grid>
    </Box>
);

const CalendarView = ({ events, navigate, date, onNavigate }: { events: any[], navigate: any, date: Date, onNavigate: (d: Date) => void }) => (
    <Calendar
        localizer={localizer}
        events={events}
        style={{ height: '100%' }}
        onSelectEvent={(event) => navigate(`/contracts/${event.resource.contract_id}`)}
        date={date}
        onNavigate={onNavigate}
        components={{ 
            toolbar: CustomCalendarToolbar,
            event: (props) => <Box sx={{ p: '2px', borderRadius: 1, bgcolor: getRiskChipColor(props.event.resource.risk_level) }}>{props.title}</Box> 
        }}
    />
);

const TableView = ({ obligations, columns, onViewCondition }: { obligations: Obligation[], columns: GridColDef[], onViewCondition: (obl: Obligation) => void }) => (
    <Box sx={{ height: 600, width: '100%' }}>
        <StyledDataGrid rows={obligations} columns={columns} slots={{ toolbar: GridToolbar }} disableRowSelectionOnClick />
    </Box>
);

const TimelineView = ({ obligations }: { obligations: Obligation[] }) => {
    const sorted = obligations.filter(o => o.deadline).sort((a, b) => moment(a.deadline).diff(moment(b.deadline)));
    const overdue = sorted.filter(o => moment(o.deadline).isBefore(moment(), 'day'));
    const upcoming = sorted.filter(o => !moment(o.deadline).isBefore(moment(), 'day'));

    if (sorted.length === 0) {
        return <Alert severity="info">No obligations with deadlines to display on the timeline.</Alert>;
    }

    return (
        <Timeline position="alternate">
            {overdue.length > 0 && overdue.map((obl, index) => (
                <TimelineItem key={obl.id}>
                    <TimelineOppositeContent color="text.secondary">
                        {moment(obl.deadline).format('MMM D, YYYY')}
                        <Typography variant="caption" display="block" color="error">
                            ({moment(obl.deadline).fromNow()})
                        </Typography>
                    </TimelineOppositeContent>
                    <TimelineSeparator>
                        <TimelineDot color={getRiskChipColor(obl.risk_level)} />
                        <TimelineConnector />
                    </TimelineSeparator>
                    <TimelineContent>
                        <Paper elevation={3} sx={{ p: 2 }}>
                            <Typography variant="h6" component="span">{obl.obligation_type}</Typography>
                            <Typography>{obl.description}</Typography>
                        </Paper>
                    </TimelineContent>
                </TimelineItem>
            ))}
            {upcoming.length > 0 && upcoming.map((obl, index) => (
                <TimelineItem key={obl.id}>
                     <TimelineOppositeContent color="text.secondary">
                        {moment(obl.deadline).format('MMM D, YYYY')}
                        <Typography variant="caption" display="block">
                            (in {moment(obl.deadline).diff(moment(), 'days')} days)
                        </Typography>
                    </TimelineOppositeContent>
                    <TimelineSeparator>
                        <TimelineDot color={getRiskChipColor(obl.risk_level)} variant="outlined" />
                        {index < upcoming.length - 1 && <TimelineConnector />}
                    </TimelineSeparator>
                    <TimelineContent>
                        <Paper elevation={3} sx={{ p: 2 }}>
                            <Typography variant="h6" component="span">{obl.obligation_type}</Typography>
                            <Typography>{obl.description}</Typography>
                        </Paper>
                    </TimelineContent>
                </TimelineItem>
            ))}
        </Timeline>
    );
};

export default ObligationsPage;
