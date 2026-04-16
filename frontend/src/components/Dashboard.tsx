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
  castes: Record<string, number>;
  avg_income_start: number;
  avg_income_end: number;
}

interface PolicyAnalysis {
  domain: string;
  mechanism: string;
  time_effect: string;
  summary: string;
  affected_groups: string[];
  key_attributes: string[];
  potential_winners: string[];
  potential_losers: string[];
  parsed_by: string;
  recommendation?: 'implement' | 'conditional' | 'do_not_implement' | string;
  recommendation_confidence?: number;
  recommendation_reasoning?: string;
  recommendation_key_risks?: string[];
  recommendation_conditions?: string[];
  recommendation_source?: string;
}

interface PipelineTimings {
  parse_policy_ms: number;
  map_attributes_ms: number;
  population_generation_ms: number;
  llm_sampling_ms: number;
  model_training_ms: number;
  simulation_ms: number;
  total_ms: number;
}

interface PipelineInfo {
  run_id?: string;
  llm_mode: 'groq' | 'mock' | string;
  population_size: number;
  sample_size: number;
  steps: number;
  training_epochs: number;
  batch_size: number;
  sample_strategy?: string;
  model_validation?: {
    samples_total: number;
    samples_train: number;
    samples_validation: number;
    train_loss: number;
    train_mae: number;
    validation_loss: number | null;
    validation_mae: number | null;
  };
  timings_ms: PipelineTimings;
}

interface ReactionPreview {
  citizen_id: number;
  occupation: string;
  location: string;
  happiness_change: number;
  support_change: number;
  income_change: number;
  diary_entry: string;
}

interface SimulationResults {
  happiness_trend: number[];
  support_trend: number[];
  income_trend: number[];
  population_stats: PopulationStats;
  policy_analysis: PolicyAnalysis;
  pipeline: PipelineInfo;
  reaction_preview: ReactionPreview[];
}

const buildStepLabels = (seriesLength: number) =>
  Array.from({ length: Math.max(seriesLength, 1) }, (_value, index) => `Step ${index + 1}`);

const toDisplayMs = (ms: number) => (ms >= 1000 ? `${(ms / 1000).toFixed(2)}s` : `${ms.toFixed(0)}ms`);

const Dashboard: React.FC = () => {
  const [policy, setPolicy] = useState('');
  const [loading, setLoading] = useState(false);
  const [uiError, setUiError] = useState<string | null>(null);
  const [results, setResults] = useState<SimulationResults | null>(null);

  const [populationSize, setPopulationSize] = useState(3000);
  const [sampleSize, setSampleSize] = useState(120);
  const [simulationSteps, setSimulationSteps] = useState(12);
  const [trainingEpochs, setTrainingEpochs] = useState(80);

  const apiBaseUrl = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/$/, '');
  const policyCharacterCount = policy.trim().length;

  const policyPresets = [
    'Introduce targeted farming subsidies with digital market access support for rural smallholders.',
    'Expand public healthcare clinics with medicine support in low-income districts and villages.',
    'Launch vocational skilling grants and apprenticeship stipends for youth in semi-urban regions.',
  ];

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
        {
          policy: policy.trim(),
          population_size: populationSize,
          sample_size: sampleSize,
          steps: simulationSteps,
          training_epochs: trainingEpochs,
        },
        { timeout: 120000 }
      );
      setResults(response.data);
    } catch (error) {
      console.error(error);

      if (axios.isAxiosError(error)) {
        if (error.code === 'ECONNABORTED') {
          setUiError('Simulation timed out. Try reducing population/sample size or training epochs.');
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

  const happinessSeries = results?.happiness_trend ?? [];
  const supportSeries = results?.support_trend ?? [];
  const incomeSeries = results?.income_trend ?? [];

  const happinessData = useMemo(
    () => ({
      labels: buildStepLabels(happinessSeries.length),
      datasets: [
        {
          label: 'Average Happiness',
          data: happinessSeries,
          borderColor: '#38bdf8',
          backgroundColor: 'rgba(56, 189, 248, 0.2)',
          pointBackgroundColor: '#38bdf8',
          fill: true,
          tension: 0.35,
        },
      ],
    }),
    [happinessSeries]
  );

  const supportData = useMemo(
    () => ({
      labels: buildStepLabels(supportSeries.length),
      datasets: [
        {
          label: 'Policy Support',
          data: supportSeries,
          borderColor: '#3b82f6',
          backgroundColor: 'rgba(59, 130, 246, 0.18)',
          pointBackgroundColor: '#3b82f6',
          fill: true,
          tension: 0.35,
        },
      ],
    }),
    [supportSeries]
  );

  const incomeData = useMemo(
    () => ({
      labels: buildStepLabels(incomeSeries.length),
      datasets: [
        {
          label: 'Average Income (Rs)',
          data: incomeSeries,
          borderColor: '#0ea5e9',
          backgroundColor: 'rgba(14, 165, 233, 0.2)',
          pointBackgroundColor: '#0ea5e9',
          fill: true,
          tension: 0.3,
        },
      ],
    }),
    [incomeSeries]
  );

  const occupationData = useMemo(
    () => ({
      labels: Object.keys(results?.population_stats.occupations ?? {}),
      datasets: [
        {
          data: Object.values(results?.population_stats.occupations ?? {}),
          backgroundColor: ['#38bdf8', '#3b82f6', '#1d4ed8', '#0ea5e9', '#0284c7', '#0369a1'],
        },
      ],
    }),
    [results?.population_stats.occupations]
  );

  const topCasteStats = useMemo(
    () =>
      Object.entries(results?.population_stats.castes || {})
        .sort((a, b) => b[1] - a[1])
        .slice(0, 4),
    [results?.population_stats.castes]
  );

  const recommendation = (results?.policy_analysis.recommendation || 'conditional').toLowerCase();
  const recommendationLabel =
    recommendation === 'implement'
      ? 'Implement'
      : recommendation === 'do_not_implement'
      ? 'Do Not Implement'
      : 'Conditional';

  const recommendationPalette =
    recommendation === 'implement'
      ? {
          border: 'rgba(34, 197, 94, 0.5)',
          bg: 'rgba(20, 83, 45, 0.28)',
          chipBg: 'rgba(34, 197, 94, 0.2)',
        }
      : recommendation === 'do_not_implement'
      ? {
          border: 'rgba(248, 113, 113, 0.52)',
          bg: 'rgba(127, 29, 29, 0.3)',
          chipBg: 'rgba(248, 113, 113, 0.22)',
        }
      : {
          border: 'rgba(251, 191, 36, 0.52)',
          bg: 'rgba(120, 53, 15, 0.28)',
          chipBg: 'rgba(251, 191, 36, 0.22)',
        };

  const cardSx = {
    background: colors.cardBg,
    backdropFilter: 'blur(14px)',
    borderRadius: 4,
    border: `1px solid ${colors.cardBorder}`,
    overflow: 'hidden',
    minWidth: 0,
    height: '100%',
    boxShadow: '0 20px 40px rgba(2, 8, 23, 0.35)',
    transition: 'transform 0.24s ease, border-color 0.24s ease, box-shadow 0.24s ease',
    '&:hover': {
      borderColor: colors.cardBorderHover,
      boxShadow: '0 24px 48px rgba(14, 165, 233, 0.22)',
    },
  };

  const tuningFieldSx = {
    '& .MuiOutlinedInput-root': {
      backgroundColor: 'rgba(12, 24, 42, 0.68)',
      borderRadius: 2,
      color: colors.text,
      '& fieldset': {
        borderColor: colors.cardBorder,
      },
      '&:hover fieldset': {
        borderColor: colors.accentBlue,
      },
      '&.Mui-focused fieldset': {
        borderColor: colors.accentCyan,
      },
    },
    '& .MuiInputLabel-root': {
      color: colors.textMuted,
    },
  };

  const wrappedTextSx = {
    whiteSpace: 'normal',
    wordBreak: 'break-word',
    overflowWrap: 'anywhere',
  };

  const wrappedChipSx = {
    color: colors.text,
    maxWidth: '100%',
    height: 'auto',
    '& .MuiChip-label': {
      display: 'block',
      whiteSpace: 'normal',
      wordBreak: 'break-word',
      overflowWrap: 'anywhere',
      lineHeight: 1.2,
      py: 0.65,
    },
  };

  return (
    <Box
      sx={{
        minHeight: '100vh',
        overflowX: 'hidden',
        background:
          'radial-gradient(circle at 15% 20%, rgba(56, 189, 248, 0.24) 0%, rgba(7, 11, 18, 0) 35%), radial-gradient(circle at 80% 80%, rgba(59, 130, 246, 0.22) 0%, rgba(7, 11, 18, 0) 42%), linear-gradient(160deg, #05070d 0%, #0a1220 55%, #060a13 100%)',
        py: { xs: 3, sm: 4, md: 5 },
      }}
    >
      <Container maxWidth="lg" sx={{ overflowX: 'hidden', px: { xs: 1.4, sm: 2.3, md: 3 } }}>
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
            <Typography
              variant="h2"
              component="h1"
              gutterBottom
              align="center"
              sx={{
                color: colors.text,
                maxWidth: { xs: '100%', md: 920 },
                mx: 'auto',
                lineHeight: { xs: 1.12, md: 1.16 },
                fontSize: { xs: '1.95rem', sm: '2.4rem', md: '3.1rem' },
                overflowWrap: 'anywhere',
              }}
            >
              CiviSim Dashboard
            </Typography>
            <Typography
              variant="h5"
              align="center"
              sx={{
                color: colors.textMuted,
                mb: 3,
                maxWidth: { xs: '100%', md: 940 },
                mx: 'auto',
                lineHeight: 1.35,
                fontSize: { xs: '1rem', sm: '1.15rem', md: '1.45rem' },
                overflowWrap: 'anywhere',
              }}
            >
              Deep policy simulation with LLM sampling, model training, and timeline dynamics
            </Typography>
            <Box sx={{ display: 'flex', justifyContent: 'center', mb: 3 }}>
              <Avatar
                aria-label="CiviSim icon"
                sx={{
                  width: { xs: 68, sm: 80 },
                  height: { xs: 68, sm: 80 },
                  background: 'linear-gradient(135deg, #3b82f6 0%, #38bdf8 100%)',
                  boxShadow: '0 14px 32px rgba(56, 189, 248, 0.34)',
                }}
              >
                <Box component="svg" viewBox="0 0 24 24" sx={{ width: { xs: 32, sm: 38 }, height: { xs: 32, sm: 38 } }}>
                  <path
                    d="M12 2.4 4.3 6.8v10.4L12 21.6l7.7-4.4V6.8L12 2.4Zm0 2.6 5.3 3-5.3 3-5.3-3 5.3-3Zm-6 5.4 5 2.9v5.6l-5-2.9v-5.6Zm12 0V16l-5 2.9v-5.6l5-2.9Z"
                    fill="#071423"
                  />
                </Box>
              </Avatar>
            </Box>

            <Box sx={{ display: 'flex', flexWrap: 'wrap', justifyContent: 'center', alignItems: 'stretch', gap: 1, mb: 2.5 }}>
              {policyPresets.map((preset) => (
                <Chip
                  key={preset}
                  label={preset}
                  onClick={() => setPolicy(preset)}
                  disabled={loading}
                  sx={{
                    flex: { xs: '1 1 100%', sm: '1 1 320px' },
                    maxWidth: { xs: '100%', sm: 420 },
                    minHeight: 56,
                    height: 'auto',
                    alignItems: 'flex-start',
                    borderRadius: 999,
                    backgroundColor: 'rgba(56, 189, 248, 0.18)',
                    border: '1px solid rgba(56, 189, 248, 0.36)',
                    color: colors.text,
                    '& .MuiChip-label': {
                      display: 'block',
                      whiteSpace: 'normal',
                      wordBreak: 'break-word',
                      overflowWrap: 'anywhere',
                      textAlign: 'left',
                      lineHeight: 1.3,
                      px: 2,
                      py: 1.25,
                    },
                    '&:hover': {
                      backgroundColor: 'rgba(56, 189, 248, 0.28)',
                    },
                  }}
                />
              ))}
            </Box>

            <TextField
              fullWidth
              multiline
              rows={4}
              label="Enter Policy Description"
              value={policy}
              onChange={(event) => setPolicy(event.target.value)}
              disabled={loading}
              variant="outlined"
              sx={{
                mb: 2,
                ...tuningFieldSx,
              }}
            />
            <Typography
              variant="body2"
              sx={{
                mb: 3,
                textAlign: 'right',
                color: policyCharacterCount < 60 ? '#fbbf24' : colors.textMuted,
              }}
            >
              Policy length: {policyCharacterCount} characters (longer policies usually produce better targeted simulation)
            </Typography>

            <Typography variant="h6" sx={{ color: colors.text, mb: 1.5 }}>
              Simulation Tuning
            </Typography>
            <Grid container spacing={{ xs: 1.5, sm: 2 }} sx={{ mb: 3 }}>
              <Grid size={{ xs: 12, sm: 6, md: 3 }}>
                <TextField
                  fullWidth
                  type="number"
                  label="Population"
                  value={populationSize}
                  onChange={(event) => setPopulationSize(Math.max(200, Number(event.target.value) || 3000))}
                  disabled={loading}
                  sx={tuningFieldSx}
                />
              </Grid>
              <Grid size={{ xs: 12, sm: 6, md: 3 }}>
                <TextField
                  fullWidth
                  type="number"
                  label="LLM Sample"
                  value={sampleSize}
                  onChange={(event) => setSampleSize(Math.max(20, Number(event.target.value) || 120))}
                  disabled={loading}
                  sx={tuningFieldSx}
                />
              </Grid>
              <Grid size={{ xs: 12, sm: 6, md: 3 }}>
                <TextField
                  fullWidth
                  type="number"
                  label="Simulation Steps"
                  value={simulationSteps}
                  onChange={(event) => setSimulationSteps(Math.max(3, Number(event.target.value) || 12))}
                  disabled={loading}
                  sx={tuningFieldSx}
                />
              </Grid>
              <Grid size={{ xs: 12, sm: 6, md: 3 }}>
                <TextField
                  fullWidth
                  type="number"
                  label="Training Epochs"
                  value={trainingEpochs}
                  onChange={(event) => setTrainingEpochs(Math.max(20, Number(event.target.value) || 80))}
                  disabled={loading}
                  sx={tuningFieldSx}
                />
              </Grid>
            </Grid>

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
                    minWidth: 240,
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
                  {loading ? 'Running Full Pipeline...' : 'Run Deep Simulation'}
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
            {results.pipeline.llm_mode !== 'groq' && (
              <Alert
                severity="warning"
                sx={{
                  mb: 3,
                  borderRadius: 2.5,
                  border: '1px solid rgba(251, 191, 36, 0.45)',
                  backgroundColor: 'rgba(120, 53, 15, 0.28)',
                  color: colors.text,
                }}
              >
                Running in mock LLM mode. Configure GROQ_API_KEY for real model calls and richer reaction fidelity.
              </Alert>
            )}

            <Grid
              container
              spacing={{ xs: 2, sm: 2.5, md: 3 }}
              sx={{
                '& > .MuiGrid-root': { minWidth: 0 },
                '& > *': { alignSelf: 'stretch' },
              }}
            >
              <Grid size={{ xs: 12 }}>
                <motion.div whileHover={{ scale: 1.005, y: -2 }} transition={{ duration: 0.2 }}>
                  <Card
                    sx={{
                      ...cardSx,
                      borderColor: recommendationPalette.border,
                      background: recommendationPalette.bg,
                    }}
                  >
                    <CardContent>
                      <Box sx={{ display: 'flex', flexWrap: 'wrap', alignItems: { xs: 'flex-start', sm: 'center' }, gap: 1.2, mb: 1 }}>
                        <Typography variant="h5" sx={{ color: colors.text }}>
                          Policy Recommendation
                        </Typography>
                        <Chip
                          label={recommendationLabel}
                          sx={{
                            fontWeight: 700,
                            border: `1px solid ${recommendationPalette.border}`,
                            backgroundColor: recommendationPalette.chipBg,
                            ...wrappedChipSx,
                          }}
                        />
                        <Chip
                          label={`Confidence: ${((results.policy_analysis.recommendation_confidence ?? 0.5) * 100).toFixed(0)}%`}
                          sx={{
                            border: `1px solid ${recommendationPalette.border}`,
                            backgroundColor: recommendationPalette.chipBg,
                            ...wrappedChipSx,
                          }}
                        />
                        {results.policy_analysis.recommendation_source && (
                          <Chip
                            label={`Source: ${results.policy_analysis.recommendation_source}`}
                            sx={{
                              border: `1px solid ${recommendationPalette.border}`,
                              backgroundColor: recommendationPalette.chipBg,
                              ...wrappedChipSx,
                            }}
                          />
                        )}
                      </Box>

                      <Typography sx={{ color: colors.textMuted, mb: 1.2, ...wrappedTextSx }}>
                        {results.policy_analysis.recommendation_reasoning ||
                          'No recommendation narrative was returned for this run.'}
                      </Typography>

                      {(results.policy_analysis.recommendation_key_risks || []).length > 0 && (
                        <Typography variant="body2" sx={{ color: colors.textMuted, mb: 0.8, ...wrappedTextSx }}>
                          Risks: {(results.policy_analysis.recommendation_key_risks || []).join(' | ')}
                        </Typography>
                      )}

                      {(results.policy_analysis.recommendation_conditions || []).length > 0 && (
                        <Typography variant="body2" sx={{ color: colors.textMuted, ...wrappedTextSx }}>
                          Conditions: {(results.policy_analysis.recommendation_conditions || []).join(' | ')}
                        </Typography>
                      )}
                    </CardContent>
                  </Card>
                </motion.div>
              </Grid>

              <Grid size={{ xs: 12, md: 6 }}>
                <motion.div whileHover={{ scale: 1.01, y: -2 }} transition={{ duration: 0.22 }}>
                  <Card sx={cardSx}>
                    <CardContent>
                      <Typography variant="h5" sx={{ color: colors.text, mb: 2 }}>
                        Happiness Trend
                      </Typography>
                      <Box sx={{ height: { xs: 220, sm: 260, md: 300 }, overflow: 'hidden' }}>
                        {happinessSeries.length > 0 ? (
                          <Line data={happinessData} options={lineChartOptions} />
                        ) : (
                          <Typography sx={{ color: colors.textMuted }}>
                            No happiness trend data returned for this run.
                          </Typography>
                        )}
                      </Box>
                    </CardContent>
                  </Card>
                </motion.div>
              </Grid>

              <Grid size={{ xs: 12, md: 6 }}>
                <motion.div whileHover={{ scale: 1.01, y: -2 }} transition={{ duration: 0.22 }}>
                  <Card sx={cardSx}>
                    <CardContent>
                      <Typography variant="h5" sx={{ color: colors.text, mb: 2 }}>
                        Policy Support Trend
                      </Typography>
                      <Box sx={{ height: { xs: 220, sm: 260, md: 300 }, overflow: 'hidden' }}>
                        {supportSeries.length > 0 ? (
                          <Line data={supportData} options={lineChartOptions} />
                        ) : (
                          <Typography sx={{ color: colors.textMuted }}>
                            No support trend data returned for this run.
                          </Typography>
                        )}
                      </Box>
                    </CardContent>
                  </Card>
                </motion.div>
              </Grid>

              <Grid size={{ xs: 12, md: 6 }}>
                <motion.div whileHover={{ scale: 1.01, y: -2 }} transition={{ duration: 0.22 }}>
                  <Card sx={cardSx}>
                    <CardContent>
                      <Typography variant="h5" sx={{ color: colors.text, mb: 2 }}>
                        Average Income Trend
                      </Typography>
                      <Box sx={{ height: { xs: 220, sm: 260, md: 300 }, overflow: 'hidden' }}>
                        {incomeSeries.length > 0 ? (
                          <Line data={incomeData} options={lineChartOptions} />
                        ) : (
                          <Typography sx={{ color: colors.textMuted }}>
                            No income trend data returned for this run.
                          </Typography>
                        )}
                      </Box>
                    </CardContent>
                  </Card>
                </motion.div>
              </Grid>

              <Grid size={{ xs: 12, md: 6 }}>
                <motion.div whileHover={{ scale: 1.01, y: -2 }} transition={{ duration: 0.22 }}>
                  <Card sx={cardSx}>
                    <CardContent>
                      <Typography variant="h5" sx={{ color: colors.text, mb: 2 }}>
                        Occupation Distribution
                      </Typography>
                      <Box sx={{ height: { xs: 220, sm: 260, md: 300 }, overflow: 'hidden' }}>
                        {Object.keys(results.population_stats.occupations || {}).length > 0 ? (
                          <Pie data={occupationData} options={pieChartOptions} />
                        ) : (
                          <Typography sx={{ color: colors.textMuted }}>
                            Occupation distribution is unavailable for this run.
                          </Typography>
                        )}
                      </Box>
                    </CardContent>
                  </Card>
                </motion.div>
              </Grid>

              <Grid size={{ xs: 12, md: 6 }}>
                <motion.div whileHover={{ scale: 1.01, y: -2 }} transition={{ duration: 0.22 }}>
                  <Card sx={cardSx}>
                    <CardContent>
                      <Typography variant="h5" sx={{ color: colors.text, mb: 2 }}>
                        Policy Analysis
                      </Typography>
                      <Typography sx={{ color: colors.textMuted, mb: 1.5, ...wrappedTextSx }}>
                        {results.policy_analysis.summary}
                      </Typography>
                      <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1, mb: 2 }}>
                        <Chip label={`Domain: ${results.policy_analysis.domain}`} sx={wrappedChipSx} />
                        <Chip label={`Mechanism: ${results.policy_analysis.mechanism}`} sx={wrappedChipSx} />
                        <Chip label={`Parser: ${results.policy_analysis.parsed_by}`} sx={wrappedChipSx} />
                        <Chip label={`Time effect: ${results.policy_analysis.time_effect}`} sx={wrappedChipSx} />
                      </Box>

                      <Typography variant="subtitle2" sx={{ color: colors.text, mb: 0.5 }}>
                        Affected Groups
                      </Typography>
                      <Typography variant="body2" sx={{ color: colors.textMuted, mb: 1.5, ...wrappedTextSx }}>
                        {results.policy_analysis.affected_groups.length > 0
                          ? results.policy_analysis.affected_groups.join(', ')
                          : 'No explicit groups extracted in this run.'}
                      </Typography>

                      <Typography variant="subtitle2" sx={{ color: colors.text, mb: 0.5 }}>
                        Key Attributes
                      </Typography>
                      <Typography variant="body2" sx={{ color: colors.textMuted, ...wrappedTextSx }}>
                        {results.policy_analysis.key_attributes.length > 0
                          ? results.policy_analysis.key_attributes.join(', ')
                          : 'No key attributes extracted in this run.'}
                      </Typography>

                      <Typography variant="subtitle2" sx={{ color: colors.text, mt: 1.5, mb: 0.5 }}>
                        Potential Winners
                      </Typography>
                      <Typography variant="body2" sx={{ color: colors.textMuted, ...wrappedTextSx }}>
                        {(results.policy_analysis.potential_winners || []).length > 0
                          ? (results.policy_analysis.potential_winners || []).join(', ')
                          : 'No clear winner groups identified.'}
                      </Typography>

                      <Typography variant="subtitle2" sx={{ color: colors.text, mt: 1.5, mb: 0.5 }}>
                        Potential Losers
                      </Typography>
                      <Typography variant="body2" sx={{ color: colors.textMuted, ...wrappedTextSx }}>
                        {(results.policy_analysis.potential_losers || []).length > 0
                          ? (results.policy_analysis.potential_losers || []).join(', ')
                          : 'No explicit loser groups identified.'}
                      </Typography>
                    </CardContent>
                  </Card>
                </motion.div>
              </Grid>

              <Grid size={{ xs: 12, md: 6 }}>
                <motion.div whileHover={{ scale: 1.01, y: -2 }} transition={{ duration: 0.22 }}>
                  <Card sx={cardSx}>
                    <CardContent>
                      <Typography variant="h5" sx={{ color: colors.text, mb: 2 }}>
                        Pipeline Diagnostics
                      </Typography>
                      <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1, mb: 2 }}>
                        <Chip label={`Mode: ${results.pipeline.llm_mode}`} sx={wrappedChipSx} />
                        {results.pipeline.run_id && <Chip label={`Run: ${results.pipeline.run_id.slice(0, 8)}`} sx={wrappedChipSx} />}
                        <Chip label={`Population: ${results.pipeline.population_size}`} sx={wrappedChipSx} />
                        <Chip label={`Sample: ${results.pipeline.sample_size}`} sx={wrappedChipSx} />
                        <Chip label={`Steps: ${results.pipeline.steps}`} sx={wrappedChipSx} />
                        <Chip label={`Epochs: ${results.pipeline.training_epochs}`} sx={wrappedChipSx} />
                        {results.pipeline.sample_strategy && (
                          <Chip label={`Sampling: ${results.pipeline.sample_strategy}`} sx={wrappedChipSx} />
                        )}
                      </Box>
                      <Typography variant="body2" sx={{ color: colors.textMuted, mb: 0.8, ...wrappedTextSx }}>
                        Total runtime: {toDisplayMs(results.pipeline.timings_ms.total_ms)}
                      </Typography>
                      <Typography variant="body2" sx={{ color: colors.textMuted, ...wrappedTextSx }}>
                        Parse: {toDisplayMs(results.pipeline.timings_ms.parse_policy_ms)} | Mapping: {toDisplayMs(results.pipeline.timings_ms.map_attributes_ms)}
                      </Typography>
                      <Typography variant="body2" sx={{ color: colors.textMuted, ...wrappedTextSx }}>
                        Population: {toDisplayMs(results.pipeline.timings_ms.population_generation_ms)} | LLM sample: {toDisplayMs(results.pipeline.timings_ms.llm_sampling_ms)}
                      </Typography>
                      <Typography variant="body2" sx={{ color: colors.textMuted, ...wrappedTextSx }}>
                        Training: {toDisplayMs(results.pipeline.timings_ms.model_training_ms)} | Simulation: {toDisplayMs(results.pipeline.timings_ms.simulation_ms)}
                      </Typography>

                      {results.pipeline.model_validation && (
                        <>
                          <Typography variant="subtitle2" sx={{ color: colors.text, mt: 1.4, mb: 0.6 }}>
                            Model Validation
                          </Typography>
                          <Typography variant="body2" sx={{ color: colors.textMuted, ...wrappedTextSx }}>
                            Samples: total {results.pipeline.model_validation.samples_total}, train {results.pipeline.model_validation.samples_train}, val {results.pipeline.model_validation.samples_validation}
                          </Typography>
                          <Typography variant="body2" sx={{ color: colors.textMuted, ...wrappedTextSx }}>
                            Train loss: {results.pipeline.model_validation.train_loss.toFixed(4)} | Train MAE: {results.pipeline.model_validation.train_mae.toFixed(4)}
                          </Typography>
                          <Typography variant="body2" sx={{ color: colors.textMuted, ...wrappedTextSx }}>
                            Val loss: {results.pipeline.model_validation.validation_loss != null ? results.pipeline.model_validation.validation_loss.toFixed(4) : 'n/a'} | Val MAE: {results.pipeline.model_validation.validation_mae != null ? results.pipeline.model_validation.validation_mae.toFixed(4) : 'n/a'}
                          </Typography>
                        </>
                      )}
                    </CardContent>
                  </Card>
                </motion.div>
              </Grid>

              <Grid size={{ xs: 12, md: 6 }}>
                <motion.div whileHover={{ scale: 1.01, y: -2 }} transition={{ duration: 0.22 }}>
                  <Card sx={cardSx}>
                    <CardContent>
                      <Typography variant="h5" sx={{ color: colors.text, mb: 2 }}>
                        Population Stats
                      </Typography>
                      <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1, mb: 1 }}>
                        <Chip label={`Total: ${results.population_stats.total}`} sx={wrappedChipSx} />
                        <Chip label={`Income start: Rs ${results.population_stats.avg_income_start.toFixed(0)}`} sx={wrappedChipSx} />
                        <Chip label={`Income end: Rs ${results.population_stats.avg_income_end.toFixed(0)}`} sx={wrappedChipSx} />
                      </Box>
                      <Typography variant="subtitle2" sx={{ color: colors.text, mt: 1.5, mb: 0.8 }}>
                        Top castes in generated population
                      </Typography>
                      <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
                        {topCasteStats.length > 0 ? (
                          topCasteStats.map(([caste, count]) => (
                            <Chip
                              key={caste}
                              label={`${caste.toUpperCase()}: ${count}`}
                              sx={{
                                backgroundColor: 'rgba(59, 130, 246, 0.2)',
                                border: '1px solid rgba(59, 130, 246, 0.35)',
                                ...wrappedChipSx,
                              }}
                            />
                          ))
                        ) : (
                          <Typography variant="body2" sx={{ color: colors.textMuted }}>
                            No caste distribution data available for this run.
                          </Typography>
                        )}
                      </Box>
                    </CardContent>
                  </Card>
                </motion.div>
              </Grid>

              <Grid size={{ xs: 12, md: 6 }}>
                <motion.div whileHover={{ scale: 1.01, y: -2 }} transition={{ duration: 0.22 }}>
                  <Card sx={cardSx}>
                    <CardContent>
                      <Typography variant="h5" sx={{ color: colors.text, mb: 2 }}>
                        Citizen Reaction Preview
                      </Typography>
                      {(results.reaction_preview || []).slice(0, 3).map((reaction) => (
                        <Box
                          key={reaction.citizen_id}
                          sx={{
                            mb: 1.5,
                            p: 1.5,
                            borderRadius: 2,
                            border: '1px solid rgba(56, 189, 248, 0.3)',
                            backgroundColor: 'rgba(12, 24, 42, 0.55)',
                          }}
                        >
                          <Typography variant="subtitle2" sx={{ color: colors.text, mb: 0.5, ...wrappedTextSx }}>
                            Citizen #{reaction.citizen_id} - {reaction.occupation} ({reaction.location})
                          </Typography>
                          <Typography variant="body2" sx={{ color: colors.textMuted, mb: 0.4, ...wrappedTextSx }}>
                            Happiness: {reaction.happiness_change.toFixed(3)} | Support: {reaction.support_change.toFixed(3)} | Income: Rs {reaction.income_change.toFixed(0)}
                          </Typography>
                          <Typography variant="body2" sx={{ color: colors.textMuted, ...wrappedTextSx }}>
                            {reaction.diary_entry}
                          </Typography>
                        </Box>
                      ))}
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
