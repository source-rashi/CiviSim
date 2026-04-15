import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { Container, Typography, TextField, Button, Box, Grid, Card, CardContent, LinearProgress, Paper, Avatar, Chip } from '@mui/material';
import { Line, Bar, Pie } from 'react-chartjs-2';
import axios from 'axios';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Title,
  Tooltip,
  Legend,
  ArcElement,
} from 'chart.js';

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Title,
  Tooltip,
  Legend,
  ArcElement
);

const Dashboard: React.FC = () => {
  const [policy, setPolicy] = useState('');
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState<any>(null);

  const handleSimulate = async () => {
    setLoading(true);
    try {
      const response = await axios.post('/api/simulate', { policy });
      setResults(response.data);
    } catch (error) {
      console.error(error);
    }
    setLoading(false);
  };

  const happinessData = {
    labels: ['Step 1', 'Step 2', 'Step 3', 'Step 4', 'Step 5', 'Step 6', 'Step 7', 'Step 8', 'Step 9', 'Step 10'],
    datasets: [
      {
        label: 'Average Happiness',
        data: results?.happiness_trend || [0.5, 0.6, 0.7, 0.8, 0.9, 0.85, 0.9, 0.95, 0.92, 0.88],
        borderColor: 'rgb(75, 192, 192)',
        backgroundColor: 'rgba(75, 192, 192, 0.2)',
        tension: 0.4,
      },
    ],
  };

  const supportData = {
    labels: ['Step 1', 'Step 2', 'Step 3', 'Step 4', 'Step 5', 'Step 6', 'Step 7', 'Step 8', 'Step 9', 'Step 10'],
    datasets: [
      {
        label: 'Policy Support',
        data: results?.support_trend || [0.3, 0.4, 0.5, 0.6, 0.7, 0.75, 0.8, 0.85, 0.82, 0.78],
        borderColor: 'rgb(255, 99, 132)',
        backgroundColor: 'rgba(255, 99, 132, 0.2)',
        tension: 0.4,
      },
    ],
  };

  const occupationData = {
    labels: ['Farmer', 'Merchant', 'Clerk', 'Laborer'],
    datasets: [
      {
        data: [25, 30, 20, 25],
        backgroundColor: ['#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0'],
      },
    ],
  };

  return (
    <Box sx={{ minHeight: '100vh', background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)', py: 4 }}>
      <Container maxWidth="lg">
        <motion.div
          initial={{ opacity: 0, y: 50 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8 }}
        >
          <Paper elevation={10} sx={{ p: 4, mb: 4, background: 'rgba(255,255,255,0.1)', backdropFilter: 'blur(10px)', borderRadius: 3 }}>
            <Typography variant="h2" component="h1" gutterBottom align="center" sx={{ color: 'white', fontWeight: 'bold' }}>
              CiviSim Dashboard
            </Typography>
            <Typography variant="h5" align="center" sx={{ color: 'white', mb: 3 }}>
              Simulate Policy Impacts on Society
            </Typography>
            <Box sx={{ display: 'flex', justifyContent: 'center', mb: 3 }}>
              <Avatar sx={{ width: 80, height: 80, bgcolor: 'primary.main' }}>C</Avatar>
            </Box>
            <TextField
              fullWidth
              multiline
              rows={4}
              label="Enter Policy Description"
              value={policy}
              onChange={(e) => setPolicy(e.target.value)}
              variant="outlined"
              sx={{ mb: 3, '& .MuiOutlinedInput-root': { backgroundColor: 'rgba(255,255,255,0.1)' } }}
              InputLabelProps={{ style: { color: 'white' } }}
              inputProps={{ style: { color: 'white' } }}
            />
            <Box sx={{ display: 'flex', justifyContent: 'center' }}>
              <motion.div whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }}>
                <Button
                  variant="contained"
                  color="secondary"
                  onClick={handleSimulate}
                  disabled={loading}
                  sx={{ px: 4, py: 2, fontSize: '1.2rem' }}
                >
                  {loading ? 'Simulating...' : 'Run Simulation'}
                </Button>
              </motion.div>
            </Box>
            {loading && <LinearProgress sx={{ mt: 2, height: 10, borderRadius: 5 }} />}
          </Paper>
        </motion.div>

        {results && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.5, duration: 0.8 }}
          >
            <Grid container spacing={4}>
              <Grid item xs={12} md={6}>
                <motion.div whileHover={{ scale: 1.02 }}>
                  <Card sx={{ background: 'rgba(255,255,255,0.1)', backdropFilter: 'blur(10px)', borderRadius: 3 }}>
                    <CardContent>
                      <Typography variant="h5" sx={{ color: 'white', mb: 2 }}>Happiness Trend</Typography>
                      <Line data={happinessData} />
                    </CardContent>
                  </Card>
                </motion.div>
              </Grid>
              <Grid item xs={12} md={6}>
                <motion.div whileHover={{ scale: 1.02 }}>
                  <Card sx={{ background: 'rgba(255,255,255,0.1)', backdropFilter: 'blur(10px)', borderRadius: 3 }}>
                    <CardContent>
                      <Typography variant="h5" sx={{ color: 'white', mb: 2 }}>Policy Support Trend</Typography>
                      <Line data={supportData} />
                    </CardContent>
                  </Card>
                </motion.div>
              </Grid>
              <Grid item xs={12} md={6}>
                <motion.div whileHover={{ scale: 1.02 }}>
                  <Card sx={{ background: 'rgba(255,255,255,0.1)', backdropFilter: 'blur(10px)', borderRadius: 3 }}>
                    <CardContent>
                      <Typography variant="h5" sx={{ color: 'white', mb: 2 }}>Occupation Distribution</Typography>
                      <Pie data={occupationData} />
                    </CardContent>
                  </Card>
                </motion.div>
              </Grid>
              <Grid item xs={12} md={6}>
                <motion.div whileHover={{ scale: 1.02 }}>
                  <Card sx={{ background: 'rgba(255,255,255,0.1)', backdropFilter: 'blur(10px)', borderRadius: 3 }}>
                    <CardContent>
                      <Typography variant="h5" sx={{ color: 'white', mb: 2 }}>Population Stats</Typography>
                      <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
                        <Chip label={`Total: ${results.population_stats.total}`} sx={{ backgroundColor: 'rgba(255,255,255,0.2)', color: 'white' }} />
                        {/* Add more chips */}
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