import * as Sentry from '@sentry/react';
import { browserTracingIntegration } from '@sentry/browser';

interface SentryConfig {
  dsn: string;
  environment: string;
  release: string;
  tracesSampleRate: number;
  debug: boolean;
}

const DEFAULT_CONFIG: SentryConfig = {
  dsn: '',
  environment: 'development',
  release: '0.1.0',
  tracesSampleRate: 0.1,
  debug: false,
};

export function initSentry(config: Partial<SentryConfig> = {}) {
  const finalConfig = { ...DEFAULT_CONFIG, ...config };

  if (!finalConfig.dsn) {
    console.warn('Sentry DSN not provided, skipping initialization');
    return;
  }

  Sentry.init({
    dsn: finalConfig.dsn,
    environment: finalConfig.environment,
    release: finalConfig.release,
    tracesSampleRate: finalConfig.tracesSampleRate,
    debug: finalConfig.debug,
    integrations: [
      browserTracingIntegration({
        // Only trace navigation events, not all XHR/fetch
        tracePropagationTargets: ['localhost', /^https:\/\/.*\.supabase\.co/],
      }),
    ],
    beforeSend(event) {
      // Filter out health check noise
      if (event.request?.url) {
        const url = event.request.url;
        if (
          url.endsWith('/health') ||
          url.endsWith('/health/ready') ||
          url.endsWith('/health/live') ||
          url.endsWith('/metrics') ||
          url.endsWith('/favicon.ico')
        ) {
          return null;
        }
      }
      return event;
    },
    initialScope: {
      tags: {
        platform: 'extension',
        app: 'annex',
      },
    },
  });
}

export function captureException(error: Error, context?: Record<string, unknown>) {
  return Sentry.captureException(error, {
    extra: context,
  });
}

export function captureMessage(message: string, level: Sentry.SeverityLevel = 'info', context?: Record<string, unknown>) {
  return Sentry.captureMessage(message, level, {
    extra: context,
  });
}

export function setUserContext(user: { id: string; email?: string; username?: string }) {
  Sentry.setUser(user);
}

export function clearUserContext() {
  Sentry.setUser(null);
}

export function addBreadcrumb(message: string, category: string = 'custom', data?: Record<string, unknown>) {
  Sentry.addBreadcrumb({
    message,
    category,
    data,
    level: 'info',
  });
}

export function startTransaction(name: string, op?: string) {
  return Sentry.startSpan({
    name,
    op: op || 'ui.action',
  });
}

export function withSentryScope<T>(
  callback: (scope: Sentry.Scope) => T
): T {
  return Sentry.withScope(callback);
}