/**
 * Theme state. Toggles data-theme on <html> and persists to localStorage,
 * exactly as the old base.html script did. Dark ("Ember", red) is the default.
 */
import { createContext, useContext, useEffect, useState, useCallback } from 'react';

const STORAGE_KEY = 'smartserve-theme';
const ThemeContext = createContext(null);

function readStoredTheme() {
  try {
    return localStorage.getItem(STORAGE_KEY) === 'light' ? 'light' : 'dark';
  } catch {
    return 'dark';
  }
}

export function ThemeProvider({ children }) {
  const [theme, setTheme] = useState(readStoredTheme);

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
    try {
      localStorage.setItem(STORAGE_KEY, theme);
    } catch {
      /* private browsing — theme just won't persist */
    }
  }, [theme]);

  const toggleTheme = useCallback(() => {
    setTheme((current) => (current === 'dark' ? 'light' : 'dark'));
  }, []);

  return (
    <ThemeContext.Provider value={{ theme, toggleTheme, isDark: theme === 'dark' }}>
      {children}
    </ThemeContext.Provider>
  );
}

export function useTheme() {
  const ctx = useContext(ThemeContext);
  if (!ctx) throw new Error('useTheme must be used inside ThemeProvider');
  return ctx;
}

/**
 * Resolve live CSS custom-property values so charts can re-read theme colors
 * on toggle (Recharts needs concrete color strings, not var() references).
 */
export function useChartColors() {
  const { theme } = useTheme();
  const [colors, setColors] = useState(() => readChartColors());

  useEffect(() => {
    // Next frame, so the new data-theme attribute has been applied.
    const id = requestAnimationFrame(() => setColors(readChartColors()));
    return () => cancelAnimationFrame(id);
  }, [theme]);

  return colors;
}

function readChartColors() {
  if (typeof window === 'undefined') return {};
  const s = getComputedStyle(document.documentElement);
  const get = (name, fallback) => s.getPropertyValue(name).trim() || fallback;
  return {
    brand: get('--brand', '#950101'),
    brandMid: get('--brand-mid', '#B30202'),
    brandSoft: get('--brand-soft', '#3D0000'),
    success: get('--success', '#5FB85C'),
    warning: get('--warning', '#F0A828'),
    info: get('--info', '#5AA2E8'),
    danger: get('--danger', '#FF0000'),
    text: get('--text-primary', '#F4ECEC'),
    muted: get('--text-muted', '#B39E9E'),
    hairline: get('--hairline', 'rgba(255,255,255,.08)'),
    surface: get('--bg-elev-1', '#0B0607'),
  };
}
