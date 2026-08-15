/// Sentry configuration for ANNEX Flutter apps.

class SentryConfig {
  final String dsn;
  final String environment;
  final String release;
  final double tracesSampleRate;
  final double profilesSampleRate;
  final bool enableAutoSessionTracking;
  final bool debug;

  const SentryConfig({
    required this.dsn,
    this.environment = 'development',
    this.release = '0.1.0',
    this.tracesSampleRate = 0.1,
    this.profilesSampleRate = 0.1,
    this.enableAutoSessionTracking = true,
    this.debug = false,
  });

  /// Create config from environment variables or defaults.
  factory SentryConfig.fromEnvironment({
    required String dsn,
    String? environment,
    String? release,
    double? tracesSampleRate,
    double? profilesSampleRate,
    bool? enableAutoSessionTracking,
    bool? debug,
  }) {
    return SentryConfig(
      dsn: dsn,
      environment: environment ?? 'development',
      release: release ?? '0.1.0',
      tracesSampleRate: tracesSampleRate ?? 0.1,
      profilesSampleRate: profilesSampleRate ?? 0.1,
      enableAutoSessionTracking: enableAutoSessionTracking ?? true,
      debug: debug ?? false,
    );
  }
}