import React from 'react';
import { createRoot } from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

import App from './App';
import { AuthProvider } from './context/AuthContext';
import { ThemeProvider } from './context/ThemeContext';
import { ToastProvider } from './context/ToastContext';
import './styles/theme.css';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      // Backend errors (500s from unreachable Mongo, etc.) shouldn't sit in a
      // multi-attempt retry loop with 5-second timeouts each — surface the
      // failure to the UI immediately so the ErrorState can render.
      retry: 0,
      refetchOnWindowFocus: false,
      staleTime: 30_000,
    },
  },
});

// Enable theme-crossfade transitions only after first paint, so the initial
// load never animates its own colors in.
requestAnimationFrame(() => document.documentElement.classList.add('theme-ready'));

createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <BrowserRouter>
      <QueryClientProvider client={queryClient}>
        <ThemeProvider>
          <ToastProvider>
            <AuthProvider>
              <App />
            </AuthProvider>
          </ToastProvider>
        </ThemeProvider>
      </QueryClientProvider>
    </BrowserRouter>
  </React.StrictMode>,
);
