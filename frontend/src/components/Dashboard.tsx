import React, { useMemo, useState } from 'react';
import { motion } from 'framer-motion';
import {
  Alert,
  Avatar,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  Container,
  Grid,
  LinearProgress,
  Paper,
  TextField,
  Typography,
} from '@mui/material';
import { Line, Pie } from 'react-chartjs-2';
import axios from 'axios';
import {
  Chart as ChartJS,
  ArcElement,
  CategoryScale,
  Filler,
  Legend,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
} from 'chart.js';
import type { ChartOptions } from 'chart.js';

ChartJS.register(
  ArcElement,
  CategoryScale,
  Filler,
  Legend,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip
);

interface PopulationStats {
  total: number;
  occupations: Record<string, number>;
}

interface SimulationResults {
  happiness_trend: number[];
  support_trend: number[];
  population_stats: PopulationStats;
}

const Dashboard: React.FC = () => {
  const [policy, setPolicy] = useState('');
  const [loading, setLoading] = useState(false);
  const [uiError, setUiError] = useState<string | null>(null);
  const [results, setResults] = useState<SimulationResults | null>(null);
  const apiBaseUrl = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/$/, '');

  const colors = {
    accentBlue: '#3b82f6',
    accentCyan: '#38bdf8',
    cardBg: 'rgba(14, 26, 46, 0.72)',
    cardBorder: 'rgba(110, 164, 248, 0.26)',
    cardBorderHover: 'rgba(56, 189, 248, 0.6)',
    text: '#eaf1ff',
    textMuted: '#a8bddf',
  };

  const handleSimulate = async () => {
    if (!policy.trim()) {
      setUiError('Please enter a policy description before running the simulation.');
      return;
    }

    setUiError(null);
    setLoading(true);
    try {
      const endpoint = `${apiBaseUrl}/api/simulate`;
      const response = await axios.post<SimulationResults>(
        endpoint,
        { policy },
        { timeout: 25000 }
      );
      setResults(response.data);
    } catch (error) {
      console.error(error);

      if (axios.isAxiosError(error)) {
        if (error.code === 'ECONNABORTED') {
          setUiError('Simulation timed out. Try a shorter policy description or retry.');
        } else {
          const serverDetail =
            typeof error.response?.data?.detail === 'string'
              ? error.response.data.detail
              : null;
          setUiError(serverDetail || 'Simulation failed. Please ensure the backend is running and try again.');
        }
      } else {
        setUiError('Unexpected error while running simulation. Please retry.');
      }
    } finally {
      setLoading(false);
    }
  };

  const lineChartOptions: ChartOptions<'line'> = useMemo(
    () => ({
      maintainAspectRatio: false,
      animation: {
        duration: 650,
      },
      plugins: {
        legend: {
          labels: {
            color: colors.text,
            font: {
              family: 'Manrope',
              weight: 600,
            },
          },
        },
      },
      scales: {
        x: {
          grid: {
            color: 'rgba(168, 189, 223, 0.12)',
          },
          ticks: {
            color: colors.textMuted,
          },
        },
        y: {
          grid: {
            color: 'rgba(168, 189, 223, 0.12)',
          },
          ticks: {
            color: colors.textMuted,
          },
        },
      },
    }),
    [colors.text, colors.textMuted]
  );

  const pieChartOptions: ChartOptions<'pie'> = useMemo(
    () => ({
      maintainAspectRatio: false,
      animation: {
        duration: 650,
      },
      plugins: {
        legend: {
          labels: {
            color: colors.text,
            font: {
              family: 'Manrope',
              weight: 600,
            },
          },
        },
      },
    }),
    [colors.text]
  );

  const stepLabels = ['Step 1', 'Step 2', 'Step 3', 'Step 4', 'Step 5', 'Step 6', 'Step 7', 'Step 8', 'Step 9', 'Step 10'];

  const happinessData = useMemo(
    () => ({
      labels: stepLabels,
      datasets: [
        {
          label: 'Average Happiness',
          data: results?.happiness_trend || [0.5, 0.6, 0.7, 0.8, 0.9, 0.85, 0.9, 0.95, 0.92, 0.88],
          borderColor: '#38bdf8',
          backgroundColor: 'rgba(56, 189, 248, 0.2)',
          pointBackgroundColor: '#38bdf8',
          fill: true,
          tension: 0.35,
        },
      ],
    }),
    [results?.happiness_trend]
  );

  const supportData = useMemo(
    () => ({
      labels: stepLabels,
      datasets: [
        {
          label: 'Policy Support',
          data: results?.support_trend || [0.3, 0.4, 0.5, 0.6, 0.7, 0.75, 0.8, 0.85, 0.82, 0.78],
          borderColor: '#3b82f6',
          backgroundColor: 'rgba(59, 130, 246, 0.18)',
          pointBackgroundColor: '#3b82f6',
          fill: true,
          tension: 0.35,
        },
      ],
    }),
    [results?.support_trend]
  );

  const occupationData = useMemo(
    () => ({
      labels: ['Farmer', 'Merchant', 'Clerk', 'Laborer'],
      datasets: [
        {
          data: [25, 30, 20, 25],
          backgroundColor: ['#38bdf8', '#3b82f6', '#1d4ed8', '#0ea5e9'],
        },
      ],
    }),
    []
  );

  const cardSx = {
    background: colors.cardBg,
    backdropFilter: 'blur(14px)',
    borderRadius: 4,
    border: `1px solid ${colors.cardBorder}`,
    boxShadow: '0 20px 40px rgba(2, 8, 23, 0.35)',
    transition: 'transform 0.24s ease, border-color 0.24s ease, box-shadow 0.24s ease',
    '&:hover': {
      borderColor: colors.cardBorderHover,
      boxShadow: '0 24px 48px rgba(14, 165, 233, 0.22)',
    },
  };

  return (
    <Box
      sx={{
        minHeight: '100vh',
        background:
          'radial-gradient(circle at 15% 20%, rgba(56, 189, 248, 0.24) 0%, rgba(7, 11, 18, 0) 35%), radial-gradient(circle at 80% 80%, rgba(59, 130, 246, 0.22) 0%, rgba(7, 11, 18, 0) 42%), linear-gradient(160deg, #05070d 0%, #0a1220 55%, #060a13 100%)',
        py: { xs: 3, sm: 4, md: 5 },
      }}
    >
      <Container maxWidth="lg">
        <motion.div
          initial={{ opacity: 0, y: 34 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.55, ease: 'easeOut' }}
        >
          <Paper
            elevation={0}
            sx={{
              p: { xs: 2.5, sm: 3, md: 4 },
              mb: 4,
              background: 'linear-gradient(135deg, rgba(18, 32, 56, 0.9) 0%, rgba(10, 18, 34, 0.88) 100%)',
              backdropFilter: 'blur(12px)',
              borderRadius: 4,
              border: `1px solid ${colors.cardBorder}`,
              boxShadow: '0 20px 50px rgba(2, 8, 23, 0.44)',
            }}
          >
            <Typography variant="h2" component="h1" gutterBottom align="center" sx={{ color: colors.text }}>
              CiviSim Dashboard
            </Typography>
            <Typography variant="h5" align="center" sx={{ color: colors.textMuted, mb: 3 }}>
              Simulate Policy Impacts on Society
            </Typography>
            <Box sx={{ display: 'flex', justifyContent: 'center', mb: 3 }}>
              <Avatar
                sx={{
                  width: 80,
                  height: 80,
                  fontSize: '1.8rem',
                  fontWeight: 700,
                  background: 'linear-gradient(135deg, #3b82f6 0%, #38bdf8 100%)',
                  boxShadow: '0 14px 32px rgba(56, 189, 248, 0.34)',
                }}
              >
                C
              </Avatar>
            </Box>
            <TextField
              fullWidth
              multiline
              rows={4}
              label="Enter Policy Description"
              value={policy}
              onChange={(e) => setPolicy(e.target.value)}
              disabled={loading}
              variant="outlined"
              sx={{
                mb: 3,
                '& .MuiOutlinedInput-root': {
                  backgroundColor: 'rgba(12, 24, 42, 0.78)',
                  borderRadius: 2.5,
                  color: colors.text,
                  '& fieldset': {
                    borderColor: colors.cardBorder,
                  },
                  '&:hover fieldset': {
                    borderColor: colors.accentBlue,
                  },
                  '&.Mui-focused fieldset': {
                    borderColor: colors.accentCyan,
                    boxShadow: '0 0 0 4px rgba(56, 189, 248, 0.16)',
                  },
                },
                '& .MuiInputLabel-root': {
                  color: colors.textMuted,
                },
                '& .MuiInputLabel-root.Mui-focused': {
                  color: colors.accentCyan,
                },
              }}
            />
            {uiError && (
              <Alert
                severity="error"
                sx={{
                  mb: 3,
                  borderRadius: 2.5,
                  border: '1px solid rgba(248, 113, 113, 0.4)',
                  backgroundColor: 'rgba(127, 29, 29, 0.35)',
                }}
              >
                {uiError}
              </Alert>
            )}
            <Box sx={{ display: 'flex', justifyContent: 'center' }}>
              <motion.div whileHover={{ scale: 1.03, y: -2 }} whileTap={{ scale: 0.98 }} transition={{ duration: 0.2 }}>
                <Button
                  variant="contained"
                  onClick={handleSimulate}
                  disabled={loading}
                  sx={{
                    px: 4,
                    py: 1.7,
                    minWidth: 210,
                    fontSize: '1.05rem',
                    borderRadius: 999,
                    color: '#f8fcff',
                    background: 'linear-gradient(120deg, #2563eb 0%, #38bdf8 100%)',
                    boxShadow: '0 12px 30px rgba(37, 99, 235, 0.38)',
                    '&:hover': {
                      background: 'linear-gradient(120deg, #1d4ed8 0%, #0ea5e9 100%)',
                      boxShadow: '0 16px 36px rgba(14, 165, 233, 0.44)',
                    },
                    '&.Mui-disabled': {
                      color: 'rgba(234, 241, 255, 0.72)',
                      background: 'rgba(56, 189, 248, 0.3)',
                    },
                  }}
                >
                  {loading ? 'Simulating...' : 'Run Simulation'}
                </Button>
              </motion.div>
            </Box>
            {loading && (
              <LinearProgress
                sx={{
                  mt: 2,
                  height: 10,
                  borderRadius: 999,
                  backgroundColor: 'rgba(56, 189, 248, 0.18)',
                  '& .MuiLinearProgress-bar': {
                    background: 'linear-gradient(90deg, #2563eb 0%, #38bdf8 100%)',
                  },
                }}
              />
            )}
          </Paper>
        </motion.div>

        {results && (
          <motion.div
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.15, duration: 0.55, ease: 'easeOut' }}
          >
            <Grid container spacing={{ xs: 2, sm: 3, md: 4 }}>
              <Grid item xs={12} md={6}>
                <motion.div whileHover={{ scale: 1.01, y: -2 }} transition={{ duration: 0.22 }}>
                  <Card sx={cardSx}>
                    <CardContent>
                      <Typography variant="h5" sx={{ color: colors.text, mb: 2 }}>
                        Happiness Trend
                      </Typography>
                      <Box sx={{ height: 320 }}>
                        <Line data={happinessData} options={lineChartOptions} />
                      </Box>
                    </CardContent>
                  </Card>
                </motion.div>
              </Grid>
              <Grid item xs={12} md={6}>
                <motion.div whileHover={{ scale: 1.01, y: -2 }} transition={{ duration: 0.22 }}>
                  <Card sx={cardSx}>
                    <CardContent>
                      <Typography variant="h5" sx={{ color: colors.text, mb: 2 }}>
                        Policy Support Trend
                      </Typography>
                      <Box sx={{ height: 320 }}>
                        <Line data={supportData} options={lineChartOptions} />
                      </Box>
                    </CardContent>
                  </Card>
                </motion.div>
              </Grid>
              <Grid item xs={12} md={6}>
                <motion.div whileHover={{ scale: 1.01, y: -2 }} transition={{ duration: 0.22 }}>
                  <Card sx={cardSx}>
                    <CardContent>
                      <Typography variant="h5" sx={{ color: colors.text, mb: 2 }}>
                        Occupation Distribution
                      </Typography>
                      <Box sx={{ height: 320 }}>
                        <Pie data={occupationData} options={pieChartOptions} />
                      </Box>
                    </CardContent>
                  </Card>
                </motion.div>
              </Grid>
              <Grid item xs={12} md={6}>
                <motion.div whileHover={{ scale: 1.01, y: -2 }} transition={{ duration: 0.22 }}>
                  <Card sx={cardSx}>
                    <CardContent>
                      <Typography variant="h5" sx={{ color: colors.text, mb: 2 }}>
                        Population Stats
                      </Typography>
                      <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
                        <Chip
                          label={`Total: ${results.population_stats.total}`}
                          sx={{
                            backgroundColor: 'rgba(56, 189, 248, 0.22)',
                            color: colors.text,
                            border: '1px solid rgba(56, 189, 248, 0.35)',
                            fontWeight: 600,
                          }}
                        />
                      </Box>
                    </CardContent>
                  </Card>
                </motion.div>
              </Grid>
            </Grid>
          </motion.div>
        )}
      </Container>
    </Box>
  );
};

export default Dashboard;