import React from 'react';
import { createRoot } from 'react-dom/client';
import { PopupApp } from './PopupApp';
import './popup.css';
import { initSentry } from '../shared/sentry';

// Initialize Sentry early
initSentry({
  dsn: import.meta.env.VITE_SENTRY_DSN || '',
  environment: import.meta.env.MODE || 'development',
  release: import.meta.env.VITE_APP_VERSION || '0.1.0',
  debug: import.meta.env.DEV,
});

const container = document.getElementById('root');
if (!container) throw new Error('popup root missing');
createRoot(container).render(
  <React.StrictMode>
    <PopupApp />
  </React.StrictMode>,
);
