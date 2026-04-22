import { ThemeProvider, createTheme } from '@mui/material/styles';
import CssBaseline from '@mui/material/CssBaseline';
import Dashboard from './components/Dashboard';
import './style.css';

/**
 * Sovereign Intelligence MUI Theme
 * Aligned with the Stitch-generated "CiviSim Midnight" design system.
 */
const theme = createTheme({
  palette: {
    mode: 'dark',
    primary:    { main: '#38bdf8' },
    secondary:  { main: '#0566d9' },
    background: { default: '#0f131d', paper: '#1b2029' },
    text:       { primary: '#dee2f0', secondary: '#bdc8d1' },
    success:    { main: '#4ade80' },
    warning:    { main: '#fbbf24' },
    error:      { main: '#f87171' },
  },
  shape: { borderRadius: 16 },
  typography: {
    fontFamily: '"Inter", "Space Grotesk", sans-serif',
    h1: { fontWeight: 800, letterSpacing: '-0.03em' },
    h2: { fontWeight: 800, letterSpacing: '-0.025em' },
    h3: { fontWeight: 700, letterSpacing: '-0.02em' },
    h4: { fontWeight: 700, letterSpacing: '-0.015em' },
    h5: { fontWeight: 700, letterSpacing: '-0.01em' },
    h6: { fontWeight: 600 },
    button: { fontWeight: 700, letterSpacing: '0.02em', textTransform: 'none' },
  },
  components: {
    MuiCssBaseline: {
      styleOverrides: {
        body: { overflowX: 'hidden' },
        '#root': { overflowX: 'hidden' },
      },
    },
    MuiButton: {
      styleOverrides: {
        root: {
          borderRadius: 999,
          transition: 'transform 0.2s ease, box-shadow 0.25s ease, background-color 0.2s ease',
        },
      },
    },
    MuiOutlinedInput: {
      styleOverrides: {
        root: {
          borderRadius: 12,
          transition: 'box-shadow 0.2s ease, border-color 0.2s ease',
          '&:hover .MuiOutlinedInput-notchedOutline': {
            borderColor: 'rgba(56, 189, 248, 0.4)',
          },
          '&.Mui-focused .MuiOutlinedInput-notchedOutline': {
            borderColor: '#38bdf8',
          },
        },
        notchedOutline: {
          borderColor: 'rgba(141, 213, 255, 0.14)',
        },
      },
    },
    MuiChip: {
      styleOverrides: {
        root: { fontFamily: '"Space Grotesk", monospace', fontWeight: 500 },
      },
    },
    MuiLinearProgress: {
      styleOverrides: {
        root: { borderRadius: 999 },
        bar: {
          background: 'linear-gradient(90deg, #38bdf8, #0566d9, #38bdf8)',
          backgroundSize: '200% 100%',
          animation: 'progress-shimmer 1.6s linear infinite',
        },
      },
    },
  },
});

function App() {
  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      {/* Atmospheric background layers */}
      <div className="civic-bg" aria-hidden="true">
        <div className="civic-bg-grid" />
        <div className="civic-bg-orb3" />
      </div>
      <Dashboard />
    </ThemeProvider>
  );
}

export default App;