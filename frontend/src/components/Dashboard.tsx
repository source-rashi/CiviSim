import React, { useEffect, useMemo, useState } from 'react';
import { motion } from 'framer-motion';
import {
  Alert,
  Avatar,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  Collapse,
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

interface RecommendationSummary {
  status: 'good_to_go' | 'needs_changes' | 'not_recommended' | string;
  badge: string;
  headline: string;
  plain_summary: string;
  confidence: number;
  key_impact: string;
  key_risk: string;
  reasons: string[];
  next_actions: string[];
  source?: string;
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
  requested_population_size?: number;
  sample_size: number;
  requested_sample_size?: number;
  sample_size_capped?: boolean;
  steps: number;
  training_epochs: number;
  requested_training_epochs?: number;
  batch_size: number;
  requested_batch_size?: number;
  random_seed?: number;
  sample_strategy?: string;
  sampling_diagnostics?: {
    requested_sample_size: number;
    effective_sample_size: number;
    sample_size_capped: boolean;
    effective_batch_size: number;
    consistency_mae: number | null;
    consistency_sample_size: number;
  };
  model_validation?: {
    samples_total: number;
    samples_train: number;
    samples_validation: number;
    train_loss: number;
    train_mae: number;
    validation_loss: number | null;
    validation_mae: number | null;
    epochs_requested?: number;
    epochs_completed?: number;
    early_stopped?: boolean;
    best_epoch?: number;
    best_validation_loss?: number | null;
    effective_batch_size?: number;
    random_seed?: number | null;
    train_validation_mae_gap?: number | null;
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

interface GovernanceIssue {
  code: string;
  stage: string;
  severity: string;
  message: string;
}

interface AnomalyFlag {
  code: string;
  stage: string;
  severity: string;
  message: string;
  value?: number | null;
  threshold?: number | null;
}

interface AuditTrailEvent {
  timestamp: string;
  stage: string;
  status: string;
  severity: string;
  message: string;
  duration_ms?: number | null;
}

interface MetaAgentSummary {
  run_id: string;
  status: string;
  event_count: number;
  governance_issues: GovernanceIssue[];
  anomaly_flags: AnomalyFlag[];
  audit_trail_preview: AuditTrailEvent[];
}

interface SimulationResults {
  happiness_trend: number[];
  support_trend: number[];
  income_trend: number[];
  population_stats: PopulationStats;
  policy_analysis: PolicyAnalysis;
  recommendation_summary?: RecommendationSummary;
  pipeline: PipelineInfo;
  reaction_preview: ReactionPreview[];
  meta_agent?: MetaAgentSummary;
}

interface RecentRun {
  run_id: string;
  created_at: string;
  policy_text: string;
  domain: string;
  mechanism: string;
  final_happiness: number;
  final_support: number;
  avg_income_end: number;
  recommendation: string;
  population_size: number;
  sample_size: number;
  steps: number;
}

const buildStepLabels = (seriesLength: number) =>
  Array.from({ length: Math.max(seriesLength, 1) }, (_value, index) => `Step ${index + 1}`);

const toDisplayMs = (ms: number) => (ms >= 1000 ? `${(ms / 1000).toFixed(2)}s` : `${ms.toFixed(0)}ms`);
const toDisplayPercent = (value: number) => `${(Math.max(0, Math.min(1, value)) * 100).toFixed(0)}%`;
const formatLabel = (value: string) =>
  value
    .replace(/_/g, ' ')
    .trim()
    .replace(/\b\w/g, (match) => match.toUpperCase());

const formatSeverityLabel = (severity: string) => {
  if (severity === 'critical') {
    return 'High';
  }
  if (severity === 'warning') {
    return 'Medium';
  }
  return 'Info';
};

const tuningLimits = {
  populationSize: { min: 200, max: 20000, defaultValue: 1000 },
  sampleSize: { min: 10, max: 500, defaultValue: 50 },
  simulationSteps: { min: 1, max: 80, defaultValue: 5 },
  trainingEpochs: { min: 20, max: 500, defaultValue: 40 },
};

type TuningErrors = {
  populationSize?: string;
  sampleSize?: string;
  simulationSteps?: string;
  trainingEpochs?: string;
};

const Dashboard: React.FC = () => {
  const [policy, setPolicy] = useState('');
  const [loading, setLoading] = useState(false);
  const [uiError, setUiError] = useState<string | null>(null);
  const [results, setResults] = useState<SimulationResults | null>(null);
  const [tuningErrors, setTuningErrors] = useState<TuningErrors>({});
  const [showAdvancedDetails, setShowAdvancedDetails] = useState(false);
  const [recentRuns, setRecentRuns] = useState<RecentRun[]>([]);

  const [populationSize, setPopulationSize] = useState(1000);
  const [sampleSize, setSampleSize] = useState(50);
  const [simulationSteps, setSimulationSteps] = useState(5);
  const [trainingEpochs, setTrainingEpochs] = useState(40);

  const apiBaseUrl = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/$/, '');
  const policyCharacterCount = policy.trim().length;

  const fetchRecentRuns = async () => {
    try {
      const response = await axios.get(`${apiBaseUrl}/api/runs?limit=10`);
      setRecentRuns(response.data.runs || []);
    } catch (error) {
      console.error('Failed to fetch recent runs:', error);
    }
  };

  const handleLoadRun = async (runId: string) => {
    setUiError(null);
    setLoading(true);
    try {
      const response = await axios.get(`${apiBaseUrl}/api/runs/${runId}`);
      setResults(response.data);
      if (response.data.policy_text) {
        setPolicy(response.data.policy_text);
      }
      window.scrollTo({ top: 0, behavior: 'smooth' });
    } catch (error) {
      console.error(error);
      setUiError('Failed to load the previous simulation run.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchRecentRuns();
  }, []);

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

  const validateRange = (value: number, min: number, max: number, label: string) => {
    if (!Number.isFinite(value)) {
      return `${label} must be a valid number.`;
    }
    if (value < min || value > max) {
      return `${label} must be between ${min} and ${max}.`;
    }
    return undefined;
  };

  const validateTuningInputs = (): boolean => {
    const nextErrors: TuningErrors = {
      populationSize: validateRange(
        populationSize,
        tuningLimits.populationSize.min,
        tuningLimits.populationSize.max,
        'Population'
      ),
      sampleSize: validateRange(sampleSize, tuningLimits.sampleSize.min, tuningLimits.sampleSize.max, 'LLM Sample'),
      simulationSteps: validateRange(
        simulationSteps,
        tuningLimits.simulationSteps.min,
        tuningLimits.simulationSteps.max,
        'Simulation Steps'
      ),
      trainingEpochs: validateRange(
        trainingEpochs,
        tuningLimits.trainingEpochs.min,
        tuningLimits.trainingEpochs.max,
        'Training Epochs'
      ),
    };

    if (!nextErrors.sampleSize && sampleSize > populationSize) {
      nextErrors.sampleSize = 'LLM Sample cannot be greater than Population.';
    }

    setTuningErrors(nextErrors);
    return Object.values(nextErrors).every((value) => !value);
  };

  const handleSimulate = async () => {
    if (!policy.trim()) {
      setUiError('Please enter a policy description before running the simulation.');
      return;
    }

    if (!validateTuningInputs()) {
      setUiError('Please fix the simulation tuning fields before running.');
      return;
    }

    setUiError(null);
    setShowAdvancedDetails(false);
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
        { timeout: 180000 }
      );
      setResults(response.data);
    } catch (error) {
      console.error(error);

      if (axios.isAxiosError(error)) {
        if (error.code === 'ECONNABORTED') {
          setUiError('Simulation exceeded the 3 minute timeout. Try lowering population size, sample size, steps, or epochs.');
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
      fetchRecentRuns();
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

  const metaAgentSummary = results?.meta_agent;
  const governanceIssues = metaAgentSummary?.governance_issues ?? [];
  const anomalyFlags = metaAgentSummary?.anomaly_flags ?? [];
  const auditTrailPreview = metaAgentSummary?.audit_trail_preview ?? [];

  const severityStyles = (severity: string) => {
    if (severity === 'critical') {
      return {
        border: '1px solid rgba(248, 113, 113, 0.5)',
        bg: 'rgba(127, 29, 29, 0.28)',
      };
    }
    if (severity === 'warning') {
      return {
        border: '1px solid rgba(251, 191, 36, 0.5)',
        bg: 'rgba(120, 53, 15, 0.28)',
      };
    }
    return {
      border: '1px solid rgba(56, 189, 248, 0.4)',
      bg: 'rgba(14, 116, 144, 0.2)',
    };
  };

  const recommendationSummary = useMemo<RecommendationSummary | null>(() => {
    if (!results) {
      return null;
    }

    if (results.recommendation_summary) {
      return results.recommendation_summary;
    }

    const fallbackLabel = (results.policy_analysis.recommendation || 'conditional').toLowerCase();
    const fallbackStatus =
      fallbackLabel === 'implement'
        ? 'good_to_go'
        : fallbackLabel === 'do_not_implement'
        ? 'not_recommended'
        : 'needs_changes';

    const fallbackBadge =
      fallbackStatus === 'good_to_go'
        ? 'Good to Go'
        : fallbackStatus === 'not_recommended'
        ? 'Not Recommended'
        : 'Needs Changes';

    return {
      status: fallbackStatus,
      badge: fallbackBadge,
      headline:
        fallbackStatus === 'good_to_go'
          ? 'Proceed with rollout'
          : fallbackStatus === 'not_recommended'
          ? 'Do not launch yet'
          : 'Refine before launch',
      plain_summary:
        results.policy_analysis.recommendation_reasoning ||
        'The simulation completed, but a simplified recommendation summary was not returned.',
      confidence: results.policy_analysis.recommendation_confidence ?? 0.5,
      key_impact: 'Review trend cards for expected population impact.',
      key_risk:
        (results.policy_analysis.recommendation_key_risks || [])[0] ||
        'Open Advanced Details to inspect potential risks and diagnostics.',
      reasons: (
        results.policy_analysis.recommendation_key_risks || [
          'The detailed recommendation did not include plain-language reasons in this run.',
        ]
      ).slice(0, 3),
      next_actions: (
        results.policy_analysis.recommendation_conditions || [
          'Review affected groups and rerun after adjusting policy design.',
          'Use Advanced Details to validate model and governance diagnostics.',
        ]
      ).slice(0, 2),
      source: results.policy_analysis.recommendation_source,
    };
  }, [results]);

  const decisionStatus = recommendationSummary?.status ?? 'needs_changes';
  const recommendationLabel = recommendationSummary?.badge ?? 'Needs Changes';

  const recommendationPalette =
    decisionStatus === 'good_to_go'
      ? {
          border: 'rgba(34, 197, 94, 0.5)',
          bg: 'rgba(20, 83, 45, 0.28)',
          chipBg: 'rgba(34, 197, 94, 0.2)',
        }
      : decisionStatus === 'not_recommended'
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

  const finalSupportValue = supportSeries.length > 0 ? supportSeries[supportSeries.length - 1] : 0;
  const finalHappinessValue = happinessSeries.length > 0 ? happinessSeries[happinessSeries.length - 1] : 0;
  const incomeDelta = results
    ? results.population_stats.avg_income_end - results.population_stats.avg_income_start
    : 0;

  const cardSx = {
    background: colors.cardBg,
    backdropFilter: 'blur(14px)',
    borderRadius: 4,
    border: `1px solid ${colors.cardBorder}`,
    overflow: 'hidden',
    minWidth: 0,
    height: '100%',
    display: 'flex',
    flexDirection: 'column',
    boxShadow: '0 20px 40px rgba(2, 8, 23, 0.35)',
    transition: 'transform 0.24s ease, border-color 0.24s ease, box-shadow 0.24s ease',
    '&:hover': {
      borderColor: colors.cardBorderHover,
      boxShadow: '0 24px 48px rgba(14, 165, 233, 0.22)',
    },
  };

  const cardContentSx = {
    p: { xs: 1.8, sm: 2.2, md: 2.6 },
    '&:last-child': {
      pb: { xs: 1.8, sm: 2.2, md: 2.6 },
    },
  };

  const chartBoxSx = {
    minHeight: { xs: 260, sm: 300, md: 340 },
    maxHeight: { xs: 340, sm: 380, md: 420 },
    overflow: 'auto',
    pr: 0.5,
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
      <Container maxWidth="xl" sx={{ overflowX: 'hidden', px: { xs: 1.4, sm: 2.3, md: 3 } }}>
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

            <Typography variant="h6" sx={{ color: colors.text, mb: 1 }}>
              Simulation Tuning
            </Typography>
            <Typography variant="body2" sx={{ color: '#fbbf24', mb: 2, display: 'flex', alignItems: 'center', gap: 0.5 }}>
              ⚠️ Groq free tier limit: 12,000 tokens/min. Keep <strong style={{ margin: '0 4px' }}>LLM Sample ≤ 80</strong> to avoid timeouts. Upgrade Groq for larger samples.
            </Typography>
            <Grid container spacing={{ xs: 1.5, sm: 2 }} sx={{ mb: 3 }}>
              <Grid size={{ xs: 12, sm: 6, md: 3 }}>
                <TextField
                  fullWidth
                  type="number"
                  label="Population"
                  value={populationSize}
                  onChange={(event) => {
                    setPopulationSize(Number(event.target.value));
                    setTuningErrors((prev) => ({ ...prev, populationSize: undefined }));
                  }}
                  disabled={loading}
                  error={Boolean(tuningErrors.populationSize)}
                  helperText={
                    tuningErrors.populationSize ||
                    `Range ${tuningLimits.populationSize.min}-${tuningLimits.populationSize.max}.`
                  }
                  slotProps={{
                    htmlInput: {
                      min: tuningLimits.populationSize.min,
                      max: tuningLimits.populationSize.max,
                    },
                  }}
                  sx={tuningFieldSx}
                />
              </Grid>
              <Grid size={{ xs: 12, sm: 6, md: 3 }}>
                <TextField
                  fullWidth
                  type="number"
                  label="LLM Sample"
                  value={sampleSize}
                  onChange={(event) => {
                    setSampleSize(Number(event.target.value));
                    setTuningErrors((prev) => ({ ...prev, sampleSize: undefined }));
                  }}
                  disabled={loading}
                  error={Boolean(tuningErrors.sampleSize)}
                  helperText={
                    tuningErrors.sampleSize ||
                    `Range ${tuningLimits.sampleSize.min}-${tuningLimits.sampleSize.max}.`
                  }
                  slotProps={{
                    htmlInput: {
                      min: tuningLimits.sampleSize.min,
                      max: tuningLimits.sampleSize.max,
                    },
                  }}
                  sx={tuningFieldSx}
                />
              </Grid>
              <Grid size={{ xs: 12, sm: 6, md: 3 }}>
                <TextField
                  fullWidth
                  type="number"
                  label="Simulation Steps"
                  value={simulationSteps}
                  onChange={(event) => {
                    setSimulationSteps(Number(event.target.value));
                    setTuningErrors((prev) => ({ ...prev, simulationSteps: undefined }));
                  }}
                  disabled={loading}
                  error={Boolean(tuningErrors.simulationSteps)}
                  helperText={
                    tuningErrors.simulationSteps ||
                    `Range ${tuningLimits.simulationSteps.min}-${tuningLimits.simulationSteps.max}.`
                  }
                  slotProps={{
                    htmlInput: {
                      min: tuningLimits.simulationSteps.min,
                      max: tuningLimits.simulationSteps.max,
                    },
                  }}
                  sx={tuningFieldSx}
                />
              </Grid>
              <Grid size={{ xs: 12, sm: 6, md: 3 }}>
                <TextField
                  fullWidth
                  type="number"
                  label="Training Epochs"
                  value={trainingEpochs}
                  onChange={(event) => {
                    setTrainingEpochs(Number(event.target.value));
                    setTuningErrors((prev) => ({ ...prev, trainingEpochs: undefined }));
                  }}
                  disabled={loading}
                  error={Boolean(tuningErrors.trainingEpochs)}
                  helperText={
                    tuningErrors.trainingEpochs ||
                    `Range ${tuningLimits.trainingEpochs.min}-${tuningLimits.trainingEpochs.max}.`
                  }
                  slotProps={{
                    htmlInput: {
                      min: tuningLimits.trainingEpochs.min,
                      max: tuningLimits.trainingEpochs.max,
                    },
                  }}
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
                '& > .MuiGrid-root': { minWidth: { xs: 0, md: 280 } },
                '& > *': { alignSelf: 'stretch' },
                mb: 2,
              }}
            >
              <Grid size={{ xs: 12, md: 8 }}>
                <motion.div whileHover={{ scale: 1.005, y: -2 }} transition={{ duration: 0.2 }}>
                  <Card
                    sx={{
                      ...cardSx,
                      borderColor: recommendationPalette.border,
                      background: recommendationPalette.bg,
                    }}
                  >
                    <CardContent sx={cardContentSx}>
                      <Box
                        sx={{
                          display: 'flex',
                          flexWrap: 'wrap',
                          alignItems: { xs: 'flex-start', sm: 'center' },
                          gap: 1.2,
                          mb: 1,
                        }}
                      >
                        <Typography variant="h5" sx={{ color: colors.text }}>
                          Policy Decision
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
                          label={`Confidence: ${((recommendationSummary?.confidence ?? 0.5) * 100).toFixed(0)}%`}
                          sx={{
                            border: `1px solid ${recommendationPalette.border}`,
                            backgroundColor: recommendationPalette.chipBg,
                            ...wrappedChipSx,
                          }}
                        />
                        {recommendationSummary?.source && (
                          <Chip
                            label={`Source: ${recommendationSummary.source}`}
                            sx={{
                              border: `1px solid ${recommendationPalette.border}`,
                              backgroundColor: recommendationPalette.chipBg,
                              ...wrappedChipSx,
                            }}
                          />
                        )}
                      </Box>

                      <Typography variant="h6" sx={{ color: colors.text, mb: 0.8, ...wrappedTextSx }}>
                        {recommendationSummary?.headline || 'Review decision summary'}
                      </Typography>
                      <Typography sx={{ color: colors.textMuted, mb: 1.2, lineHeight: 1.5, ...wrappedTextSx }}>
                        {recommendationSummary?.plain_summary ||
                          'The simulation completed, but a plain-language summary is not available for this run.'}
                      </Typography>

                      <Typography variant="body2" sx={{ color: colors.textMuted, ...wrappedTextSx }}>
                        Main impact: {recommendationSummary?.key_impact || 'Impact summary not available.'}
                      </Typography>
                      <Typography variant="body2" sx={{ color: colors.textMuted, mt: 0.6, ...wrappedTextSx }}>
                        Main risk: {recommendationSummary?.key_risk || 'Risk summary not available.'}
                      </Typography>
                    </CardContent>
                  </Card>
                </motion.div>
              </Grid>

              <Grid size={{ xs: 12, md: 4 }}>
                <motion.div whileHover={{ scale: 1.01, y: -2 }} transition={{ duration: 0.2 }}>
                  <Card sx={cardSx}>
                    <CardContent sx={cardContentSx}>
                      <Typography variant="h6" sx={{ color: colors.text, mb: 1.4 }}>
                        Quick Snapshot
                      </Typography>
                      <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
                        <Chip label={`Support: ${toDisplayPercent(finalSupportValue)}`} sx={wrappedChipSx} />
                        <Chip label={`Wellbeing: ${toDisplayPercent(finalHappinessValue)}`} sx={wrappedChipSx} />
                        <Chip
                          label={`Income change: ${incomeDelta >= 0 ? '+' : '-'}Rs ${Math.abs(incomeDelta).toFixed(0)}`}
                          sx={wrappedChipSx}
                        />
                        <Chip label={`Population: ${results.population_stats.total}`} sx={wrappedChipSx} />
                      </Box>
                    </CardContent>
                  </Card>
                </motion.div>
              </Grid>

              <Grid size={{ xs: 12, md: 6 }}>
                <motion.div whileHover={{ scale: 1.01, y: -2 }} transition={{ duration: 0.2 }}>
                  <Card sx={cardSx}>
                    <CardContent sx={cardContentSx}>
                      <Typography variant="h6" sx={{ color: colors.text, mb: 1 }}>
                        Why This Decision
                      </Typography>
                      {(recommendationSummary?.reasons || []).length > 0 ? (
                        (recommendationSummary?.reasons || []).slice(0, 3).map((reason, index) => (
                          <Typography
                            key={`${reason}-${index}`}
                            variant="body2"
                            sx={{ color: colors.textMuted, mb: 0.7, lineHeight: 1.45, ...wrappedTextSx }}
                          >
                            {index + 1}. {reason}
                          </Typography>
                        ))
                      ) : (
                        <Typography variant="body2" sx={{ color: colors.textMuted }}>
                          No plain-language reasons were returned for this run.
                        </Typography>
                      )}
                    </CardContent>
                  </Card>
                </motion.div>
              </Grid>

              <Grid size={{ xs: 12, md: 6 }}>
                <motion.div whileHover={{ scale: 1.01, y: -2 }} transition={{ duration: 0.2 }}>
                  <Card sx={cardSx}>
                    <CardContent sx={cardContentSx}>
                      <Typography variant="h6" sx={{ color: colors.text, mb: 1 }}>
                        Next Actions
                      </Typography>
                      {(recommendationSummary?.next_actions || []).length > 0 ? (
                        (recommendationSummary?.next_actions || []).slice(0, 3).map((action, index) => (
                          <Typography
                            key={`${action}-${index}`}
                            variant="body2"
                            sx={{ color: colors.textMuted, mb: 0.7, lineHeight: 1.45, ...wrappedTextSx }}
                          >
                            {index + 1}. {action}
                          </Typography>
                        ))
                      ) : (
                        <Typography variant="body2" sx={{ color: colors.textMuted }}>
                          No next-step actions were returned for this run.
                        </Typography>
                      )}
                    </CardContent>
                  </Card>
                </motion.div>
              </Grid>

              <Grid size={{ xs: 12 }}>
                <Box sx={{ display: 'flex', justifyContent: 'center' }}>
                  <Button
                    variant="outlined"
                    onClick={() => setShowAdvancedDetails((previous) => !previous)}
                    sx={{
                      borderColor: colors.cardBorderHover,
                      color: colors.text,
                      borderRadius: 999,
                      px: 3,
                      py: 1,
                      '&:hover': {
                        borderColor: colors.accentCyan,
                        backgroundColor: 'rgba(56, 189, 248, 0.12)',
                      },
                    }}
                  >
                    {showAdvancedDetails ? 'Hide Advanced Details' : 'Show Advanced Details'}
                  </Button>
                </Box>
              </Grid>
            </Grid>

            <Collapse in={showAdvancedDetails} timeout="auto" unmountOnExit={false}>

            <Grid
              container
              spacing={{ xs: 2, sm: 2.5, md: 3 }}
              sx={{
                '& > .MuiGrid-root': { minWidth: { xs: 0, md: 300 } },
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
                    <CardContent sx={cardContentSx}>
                      <Box sx={{ display: 'flex', flexWrap: 'wrap', alignItems: { xs: 'flex-start', sm: 'center' }, gap: 1.2, mb: 1 }}>
                        <Typography variant="h5" sx={{ color: colors.text }}>
                          Detailed Recommendation Notes
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
                          'Detailed recommendation notes were not returned for this run.'}
                      </Typography>

                      {(results.policy_analysis.recommendation_key_risks || []).length > 0 && (
                        <Typography variant="body2" sx={{ color: colors.textMuted, mb: 0.8, ...wrappedTextSx }}>
                          Main risks: {(results.policy_analysis.recommendation_key_risks || []).join(' | ')}
                        </Typography>
                      )}

                      {(results.policy_analysis.recommendation_conditions || []).length > 0 && (
                        <Typography variant="body2" sx={{ color: colors.textMuted, ...wrappedTextSx }}>
                          Required conditions: {(results.policy_analysis.recommendation_conditions || []).join(' | ')}
                        </Typography>
                      )}
                    </CardContent>
                  </Card>
                </motion.div>
              </Grid>

              <Grid size={{ xs: 12, md: 6 }}>
                <motion.div whileHover={{ scale: 1.01, y: -2 }} transition={{ duration: 0.22 }}>
                  <Card sx={cardSx}>
                    <CardContent sx={cardContentSx}>
                      <Typography variant="h5" sx={{ color: colors.text, mb: 2 }}>
                        Wellbeing Trend (Happiness)
                      </Typography>
                      <Box sx={chartBoxSx}>
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

              {metaAgentSummary && (
                <Grid size={{ xs: 12 }}>
                  <motion.div whileHover={{ scale: 1.005, y: -2 }} transition={{ duration: 0.2 }}>
                    <Card
                      sx={{
                        ...cardSx,
                        minHeight: { xs: 'auto', md: 680 },
                      }}
                    >
                      <CardContent
                        sx={{
                          ...cardContentSx,
                          overflowY: { xs: 'visible', md: 'auto' },
                          maxHeight: { xs: 'none', md: 760 },
                        }}
                      >
                        <Typography variant="h5" sx={{ color: colors.text, mb: 1.2 }}>
                          System Checks and Audit
                        </Typography>
                        <Typography variant="body2" sx={{ color: colors.textMuted, mb: 1.6, ...wrappedTextSx }}>
                          Tracks policy guardrails, unusual data patterns, and a run log for traceability.
                        </Typography>

                        <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1, mb: 2 }}>
                          <Chip label={`Run status: ${formatLabel(metaAgentSummary.status)}`} sx={wrappedChipSx} />
                          <Chip label={`Events logged: ${metaAgentSummary.event_count}`} sx={wrappedChipSx} />
                          <Chip label={`Guardrail alerts: ${governanceIssues.length}`} sx={wrappedChipSx} />
                          <Chip label={`Data warnings: ${anomalyFlags.length}`} sx={wrappedChipSx} />
                        </Box>

                        <Typography variant="subtitle2" sx={{ color: colors.text, mb: 0.8 }}>
                          Guardrail Alerts
                        </Typography>
                        {governanceIssues.length > 0 ? (
                          governanceIssues.slice(0, 4).map((issue, index) => {
                            const style = severityStyles(issue.severity);
                            return (
                              <Box
                                key={`${issue.code}-${index}`}
                                sx={{
                                  mb: 1.5,
                                  p: { xs: 1.4, sm: 1.7 },
                                  borderRadius: 2,
                                  border: style.border,
                                  backgroundColor: style.bg,
                                }}
                              >
                                <Typography variant="body2" sx={{ color: colors.text, lineHeight: 1.5, ...wrappedTextSx }}>
                                  {formatSeverityLabel(issue.severity)} priority - {formatLabel(issue.stage)}: {issue.message}
                                </Typography>
                              </Box>
                            );
                          })
                        ) : (
                          <Typography variant="body2" sx={{ color: colors.textMuted, mb: 1.2 }}>
                            No guardrail alerts were detected for this run.
                          </Typography>
                        )}

                        <Typography variant="subtitle2" sx={{ color: colors.text, mt: 1.5, mb: 0.8 }}>
                          Data Warnings
                        </Typography>
                        {anomalyFlags.length > 0 ? (
                          anomalyFlags.slice(0, 4).map((flag, index) => {
                            const style = severityStyles(flag.severity);
                            return (
                              <Box
                                key={`${flag.code}-${index}`}
                                sx={{
                                  mb: 1.5,
                                  p: { xs: 1.4, sm: 1.7 },
                                  borderRadius: 2,
                                  border: style.border,
                                  backgroundColor: style.bg,
                                }}
                              >
                                <Typography variant="body2" sx={{ color: colors.text, lineHeight: 1.5, ...wrappedTextSx }}>
                                  {formatSeverityLabel(flag.severity)} priority - {formatLabel(flag.stage)}: {flag.message}
                                </Typography>
                              </Box>
                            );
                          })
                        ) : (
                          <Typography variant="body2" sx={{ color: colors.textMuted, mb: 1.2 }}>
                            No data warnings were detected for this run.
                          </Typography>
                        )}

                        <Typography variant="subtitle2" sx={{ color: colors.text, mt: 1.5, mb: 0.8 }}>
                          Recent Run Log
                        </Typography>
                        {auditTrailPreview.length > 0 ? (
                          auditTrailPreview.slice(-6).map((event, index) => {
                            const style = severityStyles(event.severity);
                            return (
                              <Box
                                key={`${event.stage}-${index}-${event.timestamp}`}
                                sx={{
                                  mb: 1.4,
                                  p: { xs: 1.4, sm: 1.6 },
                                  borderRadius: 2,
                                  border: style.border,
                                  backgroundColor: style.bg,
                                }}
                              >
                                <Typography variant="body2" sx={{ color: colors.text, lineHeight: 1.45, ...wrappedTextSx }}>
                                  Step: {formatLabel(event.stage)} | Status: {formatLabel(event.status)}
                                  {event.duration_ms != null ? ` (${toDisplayMs(event.duration_ms)})` : ''}
                                </Typography>
                                <Typography variant="body2" sx={{ color: colors.textMuted, ...wrappedTextSx }}>
                                  {event.message}
                                </Typography>
                              </Box>
                            );
                          })
                        ) : (
                          <Typography variant="body2" sx={{ color: colors.textMuted }}>
                            No run log entries are available for this simulation.
                          </Typography>
                        )}
                      </CardContent>
                    </Card>
                  </motion.div>
                </Grid>
              )}

              <Grid size={{ xs: 12, md: 6 }}>
                <motion.div whileHover={{ scale: 1.01, y: -2 }} transition={{ duration: 0.22 }}>
                  <Card sx={cardSx}>
                    <CardContent sx={cardContentSx}>
                      <Typography variant="h5" sx={{ color: colors.text, mb: 2 }}>
                        Public Support Trend
                      </Typography>
                      <Box sx={chartBoxSx}>
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
                    <CardContent sx={cardContentSx}>
                      <Typography variant="h5" sx={{ color: colors.text, mb: 2 }}>
                        Jobs In Population Sample
                      </Typography>
                      <Box sx={chartBoxSx}>
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

              <Grid size={{ xs: 12, md: 7 }}>
                <motion.div whileHover={{ scale: 1.01, y: -2 }} transition={{ duration: 0.22 }}>
                  <Card sx={cardSx}>
                    <CardContent sx={cardContentSx}>
                      <Typography variant="h5" sx={{ color: colors.text, mb: 2 }}>
                        Policy Parsing Details
                      </Typography>
                      <Typography sx={{ color: colors.textMuted, mb: 1.5, ...wrappedTextSx }}>
                        {results.policy_analysis.summary}
                      </Typography>
                      <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1, mb: 2 }}>
                        <Chip label={`Policy area: ${results.policy_analysis.domain}`} sx={wrappedChipSx} />
                        <Chip label={`Delivery method: ${results.policy_analysis.mechanism}`} sx={wrappedChipSx} />
                        <Chip label={`Parsing method: ${results.policy_analysis.parsed_by}`} sx={wrappedChipSx} />
                        <Chip label={`Expected timing: ${results.policy_analysis.time_effect}`} sx={wrappedChipSx} />
                      </Box>

                      <Typography variant="subtitle2" sx={{ color: colors.text, mb: 0.5 }}>
                        Groups Affected Most
                      </Typography>
                      <Typography variant="body2" sx={{ color: colors.textMuted, mb: 1.5, ...wrappedTextSx }}>
                        {results.policy_analysis.affected_groups.length > 0
                          ? results.policy_analysis.affected_groups.join(', ')
                          : 'No clearly affected groups were identified in this run.'}
                      </Typography>

                      <Typography variant="subtitle2" sx={{ color: colors.text, mb: 0.5 }}>
                        Signals Used For Simulation
                      </Typography>
                      <Typography variant="body2" sx={{ color: colors.textMuted, ...wrappedTextSx }}>
                        {results.policy_analysis.key_attributes.length > 0
                          ? results.policy_analysis.key_attributes.join(', ')
                          : 'No key simulation signals were extracted in this run.'}
                      </Typography>

                      <Typography variant="subtitle2" sx={{ color: colors.text, mt: 1.5, mb: 0.5 }}>
                        Groups Likely To Benefit
                      </Typography>
                      <Typography variant="body2" sx={{ color: colors.textMuted, ...wrappedTextSx }}>
                        {(results.policy_analysis.potential_winners || []).length > 0
                          ? (results.policy_analysis.potential_winners || []).join(', ')
                          : 'No clear benefit groups were identified.'}
                      </Typography>

                      <Typography variant="subtitle2" sx={{ color: colors.text, mt: 1.5, mb: 0.5 }}>
                        Groups Likely To Face Downside
                      </Typography>
                      <Typography variant="body2" sx={{ color: colors.textMuted, ...wrappedTextSx }}>
                        {(results.policy_analysis.potential_losers || []).length > 0
                          ? (results.policy_analysis.potential_losers || []).join(', ')
                          : 'No clear downside groups were identified.'}
                      </Typography>
                    </CardContent>
                  </Card>
                </motion.div>
              </Grid>

              <Grid size={{ xs: 12, md: 8 }}>
                <motion.div whileHover={{ scale: 1.01, y: -2 }} transition={{ duration: 0.22 }}>
                  <Card
                    sx={{
                      ...cardSx,
                      minHeight: { xs: 'auto', md: 430 },
                    }}
                  >
                    <CardContent sx={cardContentSx}>
                      <Typography variant="h5" sx={{ color: colors.text, mb: 2 }}>
                        Technical Run Details
                      </Typography>
                      <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1, mb: 2 }}>
                        <Chip label={`LLM mode: ${results.pipeline.llm_mode}`} sx={wrappedChipSx} />
                        {results.pipeline.run_id && <Chip label={`Run ID: ${results.pipeline.run_id.slice(0, 8)}`} sx={wrappedChipSx} />}
                        <Chip
                          label={`Population used: ${results.pipeline.population_size}${results.pipeline.requested_population_size != null ? ` (requested ${results.pipeline.requested_population_size})` : ''}`}
                          sx={wrappedChipSx}
                        />
                        <Chip
                          label={`Citizens sampled: ${results.pipeline.sample_size}${results.pipeline.requested_sample_size != null ? ` (requested ${results.pipeline.requested_sample_size})` : ''}`}
                          sx={wrappedChipSx}
                        />
                        <Chip label={`Timeline steps: ${results.pipeline.steps}`} sx={wrappedChipSx} />
                        <Chip
                          label={`Training cycles: ${results.pipeline.training_epochs}${results.pipeline.requested_training_epochs != null ? ` (requested ${results.pipeline.requested_training_epochs})` : ''}`}
                          sx={wrappedChipSx}
                        />
                        <Chip
                          label={`Batch size: ${results.pipeline.batch_size}${results.pipeline.requested_batch_size != null ? ` (requested ${results.pipeline.requested_batch_size})` : ''}`}
                          sx={wrappedChipSx}
                        />
                        {results.pipeline.random_seed != null && (
                          <Chip label={`Seed: ${results.pipeline.random_seed}`} sx={wrappedChipSx} />
                        )}
                        {results.pipeline.sample_strategy && (
                          <Chip label={`Sampling: ${results.pipeline.sample_strategy}`} sx={wrappedChipSx} />
                        )}
                      </Box>

                      {results.pipeline.sample_size_capped && (
                        <Typography variant="body2" sx={{ color: '#fbbf24', mb: 0.8, ...wrappedTextSx }}>
                          Requested sample exceeded available population, so the sample size was reduced.
                        </Typography>
                      )}

                      {results.pipeline.sampling_diagnostics?.consistency_mae != null && (
                        <Typography variant="body2" sx={{ color: colors.textMuted, mb: 0.8, ...wrappedTextSx }}>
                          Reaction consistency check (lower is better): {results.pipeline.sampling_diagnostics.consistency_mae.toFixed(4)}
                          {' '}(sampled {results.pipeline.sampling_diagnostics.consistency_sample_size} records)
                        </Typography>
                      )}

                      <Typography variant="body2" sx={{ color: colors.textMuted, mb: 0.8, ...wrappedTextSx }}>
                        Total runtime: {toDisplayMs(results.pipeline.timings_ms.total_ms)}
                      </Typography>
                      <Typography variant="body2" sx={{ color: colors.textMuted, ...wrappedTextSx }}>
                        Policy parsing: {toDisplayMs(results.pipeline.timings_ms.parse_policy_ms)} | Attribute mapping: {toDisplayMs(results.pipeline.timings_ms.map_attributes_ms)}
                      </Typography>
                      <Typography variant="body2" sx={{ color: colors.textMuted, ...wrappedTextSx }}>
                        Population generation: {toDisplayMs(results.pipeline.timings_ms.population_generation_ms)} | LLM sampling: {toDisplayMs(results.pipeline.timings_ms.llm_sampling_ms)}
                      </Typography>
                      <Typography variant="body2" sx={{ color: colors.textMuted, ...wrappedTextSx }}>
                        Model training: {toDisplayMs(results.pipeline.timings_ms.model_training_ms)} | Timeline simulation: {toDisplayMs(results.pipeline.timings_ms.simulation_ms)}
                      </Typography>

                      {results.pipeline.model_validation && (
                        <>
                          <Typography variant="subtitle2" sx={{ color: colors.text, mt: 1.4, mb: 0.6 }}>
                            Model Quality Checks
                          </Typography>
                          <Typography variant="body2" sx={{ color: colors.textMuted, ...wrappedTextSx }}>
                            Samples used: total {results.pipeline.model_validation.samples_total}, training {results.pipeline.model_validation.samples_train}, validation {results.pipeline.model_validation.samples_validation}
                          </Typography>
                          <Typography variant="body2" sx={{ color: colors.textMuted, ...wrappedTextSx }}>
                            Training error (loss): {results.pipeline.model_validation.train_loss.toFixed(4)} | Training error (MAE): {results.pipeline.model_validation.train_mae.toFixed(4)}
                          </Typography>
                          <Typography variant="body2" sx={{ color: colors.textMuted, ...wrappedTextSx }}>
                            Validation error (loss): {results.pipeline.model_validation.validation_loss != null ? results.pipeline.model_validation.validation_loss.toFixed(4) : 'n/a'} | Validation error (MAE): {results.pipeline.model_validation.validation_mae != null ? results.pipeline.model_validation.validation_mae.toFixed(4) : 'n/a'}
                          </Typography>
                          {results.pipeline.model_validation.early_stopped != null && (
                            <Typography variant="body2" sx={{ color: colors.textMuted, ...wrappedTextSx }}>
                              Early stopping: {results.pipeline.model_validation.early_stopped ? 'yes' : 'no'}
                              {results.pipeline.model_validation.best_epoch != null
                                ? ` | Best epoch: ${results.pipeline.model_validation.best_epoch}`
                                : ''}
                              {results.pipeline.model_validation.train_validation_mae_gap != null
                                ? ` | Train-Val MAE gap: ${results.pipeline.model_validation.train_validation_mae_gap.toFixed(4)}`
                                : ''}
                            </Typography>
                          )}
                        </>
                      )}
                    </CardContent>
                  </Card>
                </motion.div>
              </Grid>

              <Grid size={{ xs: 12, md: 4 }}>
                <motion.div whileHover={{ scale: 1.01, y: -2 }} transition={{ duration: 0.22 }}>
                  <Card sx={cardSx}>
                    <CardContent sx={cardContentSx}>
                      <Typography variant="h5" sx={{ color: colors.text, mb: 2 }}>
                        Generated Population Summary
                      </Typography>
                      <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1, mb: 1 }}>
                        <Chip label={`Total: ${results.population_stats.total}`} sx={wrappedChipSx} />
                      </Box>
                      <Typography variant="subtitle2" sx={{ color: colors.text, mt: 1.5, mb: 0.8 }}>
                        Top caste groups in generated population
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

              <Grid size={{ xs: 12 }}>
                <motion.div whileHover={{ scale: 1.01, y: -2 }} transition={{ duration: 0.22 }}>
                  <Card
                    sx={{
                      ...cardSx,
                      minHeight: { xs: 'auto', md: 420 },
                    }}
                  >
                    <CardContent sx={cardContentSx}>
                      <Typography variant="h5" sx={{ color: colors.text, mb: 2 }}>
                        Sample Citizen Reactions
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
                            Citizen #{reaction.citizen_id} | {reaction.occupation} ({reaction.location})
                          </Typography>
                          <Typography variant="body2" sx={{ color: colors.textMuted, mb: 0.4, ...wrappedTextSx }}>
                            Happiness change: {reaction.happiness_change.toFixed(3)} | Support change: {reaction.support_change.toFixed(3)}
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
            </Collapse>
          </motion.div>
        )}

        <Box sx={{ mt: 4, mb: 4 }}>
          <Typography variant="h5" sx={{ color: colors.text, mb: 3 }}>
            Recent Simulation Runs
          </Typography>
          {recentRuns.length > 0 ? (
            <Grid container spacing={2}>
              {recentRuns.map((run) => (
                  <Grid size={{ xs: 12, md: 6 }} key={run.run_id}>
                    <Card sx={{ ...cardSx, minHeight: 'auto' }}>
                      <CardContent sx={cardContentSx}>
                        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 1 }}>
                          <Typography variant="subtitle2" sx={{ color: colors.text, ...wrappedTextSx }}>
                            Run ID: {run.run_id.substring(0, 8)}
                          </Typography>
                          <Button 
                            variant="outlined" 
                            size="small" 
                            onClick={() => handleLoadRun(run.run_id)}
                            disabled={loading}
                            sx={{ borderColor: colors.accentBlue, color: colors.accentBlue, '&:hover': { backgroundColor: 'rgba(59, 130, 246, 0.1)' } }}
                          >
                            Load This Run
                          </Button>
                        </Box>
                        <Typography variant="body2" sx={{ color: colors.textMuted, mb: 1.5 }}>
                          {new Date(run.created_at).toLocaleString()}
                        </Typography>
                        <Typography variant="body2" sx={{ color: colors.text, mb: 1.5, ...wrappedTextSx, opacity: 0.9 }}>
                          "{run.policy_text.length > 100 ? run.policy_text.substring(0, 100) + '...' : run.policy_text}"
                        </Typography>
                        <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1, mb: 2 }}>
                          <Chip label={`Pop: ${run.population_size || 'N/A'}`} sx={{ backgroundColor: 'rgba(56, 189, 248, 0.1)', color: colors.text }} size="small" />
                          <Chip label={`Sample: ${run.sample_size || 'N/A'}`} sx={{ backgroundColor: 'rgba(56, 189, 248, 0.1)', color: colors.text }} size="small" />
                          <Chip label={`Steps: ${run.steps || 'N/A'}`} sx={{ backgroundColor: 'rgba(56, 189, 248, 0.1)', color: colors.text }} size="small" />
                        </Box>
                        <Box sx={{ p: 1.5, borderRadius: 2, backgroundColor: 'rgba(12, 24, 42, 0.55)', border: '1px solid rgba(56, 189, 248, 0.3)' }}>
                          <Typography variant="body2" sx={{ color: colors.text, ...wrappedTextSx }}>
                            <strong>Domain:</strong> {run.domain || 'N/A'} <br />
                            <strong>Recommendation:</strong> {run.recommendation || 'N/A'} <br />
                            <strong>Final Happiness:</strong> {toDisplayPercent(run.final_happiness)} <br />
                            <strong>Final Support:</strong> {toDisplayPercent(run.final_support)}
                          </Typography>
                        </Box>
                      </CardContent>
                    </Card>
                  </Grid>
                )
              )}
            </Grid>
          ) : (
            <Typography sx={{ color: colors.textMuted }}>
              No recent simulation runs found. Run a simulation to see history here.
            </Typography>
          )}
        </Box>
      </Container>
    </Box>
  );
};

export default Dashboard;
