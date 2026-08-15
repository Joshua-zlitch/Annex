/// Sentry-backed observability service for ANNEX Flutter apps.
///
/// Handles error tracking, performance monitoring, and user context
/// management across web and mobile platforms.
library;

import 'package:sentry_flutter/sentry_flutter.dart';
import 'sentry_config.dart';

class ObservabilityService {
  static bool _initialized = false;
  static SentryConfig? _config;

  /// Initialize Sentry with the given configuration.
  ///
  /// Must be called once at app startup before any other observability calls.
  static Future<void> initialize(SentryConfig config) async {
    if (_initialized) {
      return;
    }

    _config = config;

    await SentryFlutter.init(
      (options) {
        options.dsn = config.dsn;
        options.environment = config.environment;
        options.release = config.release;
        options.tracesSampleRate = config.tracesSampleRate;
        options.profilesSampleRate = config.profilesSampleRate;
        options.enableAutoSessionTracking = config.enableAutoSessionTracking;
        options.debug = config.debug;

        // Attach Flutter-specific integrations
        options.enableAutoPerformanceTracking = true;
        options.enableTimeToFullDisplayTracking = true;

        // Filter out health check noise
        options.beforeSend = (event, hint) {
          // Drop health check requests
          final request = event.request;
          if (request != null) {
            final url = request.url ?? '';
            if (url.endsWith('/health') ||
                url.endsWith('/health/ready') ||
                url.endsWith('/health/live') ||
                url.endsWith('/metrics') ||
                url.endsWith('/favicon.ico')) {
              return null;
            }
          }
          return event;
        };

        // Add custom tags
        options.setTag('platform', 'flutter');
        options.setTag('app', 'annex');
      },
      appRunner: () => throw UnsupportedError('App runner must be provided by platform'),
    );

    _initialized = true;
  }

  /// Initialize with app runner (required for Flutter).
  static Future<void> initializeWithRunner(
    SentryConfig config,
    Future<void> Function() appRunner,
  ) async {
    if (_initialized) {
      return;
    }

    _config = config;

    await SentryFlutter.init(
      (options) {
        options.dsn = config.dsn;
        options.environment = config.environment;
        options.release = config.release;
        options.tracesSampleRate = config.tracesSampleRate;
        options.profilesSampleRate = config.profilesSampleRate;
        options.enableAutoSessionTracking = config.enableAutoSessionTracking;
        options.debug = config.debug;

        options.enableAutoPerformanceTracking = true;
        options.enableTimeToFullDisplayTracking = true;

        options.beforeSend = (event, hint) {
          final request = event.request;
          if (request != null) {
            final url = request.url ?? '';
            if (url.endsWith('/health') ||
                url.endsWith('/health/ready') ||
                url.endsWith('/health/live') ||
                url.endsWith('/metrics') ||
                url.endsWith('/favicon.ico')) {
              return null;
            }
          }
          return event;
        };

        options.setTag('platform', 'flutter');
        options.setTag('app', 'annex');
      },
      appRunner: appRunner,
    );

    _initialized = true;
  }

  /// Check if observability is initialized.
  static bool get isInitialized => _initialized;

  /// Capture an exception with optional context.
  static SentryId captureException(
    dynamic exception, {
    StackTrace? stackTrace,
    Map<String, dynamic>? context,
    Map<String, String>? tags,
    SentryLevel level = SentryLevel.error,
  }) {
    if (!_initialized) {
      return SentryId.empty();
    }

    return Sentry.captureException(
      exception,
      stackTrace: stackTrace,
      withScope: (scope) {
        _applyContext(scope, context, tags, level);
      },
    );
  }

  /// Capture a message with optional context.
  static SentryId captureMessage(
    String message, {
    Map<String, dynamic>? context,
    Map<String, String>? tags,
    SentryLevel level = SentryLevel.info,
  }) {
    if (!_initialized) {
      return SentryId.empty();
    }

    return Sentry.captureMessage(
      message,
      level: level,
      withScope: (scope) {
        _applyContext(scope, context, tags, level);
      },
    );
  }

  /// Add a breadcrumb for debugging.
  static void addBreadcrumb(
    String message, {
    String category = 'custom',
    Map<String, dynamic>? data,
    SentryLevel level = SentryLevel.info,
  }) {
    if (!_initialized) {
      return;
    }

    Sentry.addBreadcrumb(
      Breadcrumb(
        message: message,
        category: category,
        level: level,
        data: data?.cast<String, dynamic>(),
      ),
    );
  }

  /// Set user context for Sentry.
  static void setUserContext({
    required String userId,
    String? email,
    String? username,
    Map<String, String>? extra,
  }) {
    if (!_initialized) {
      return;
    }

    Sentry.configureScope((scope) {
      scope.setUser(SentryUser(
        id: userId,
        email: email,
        username: username,
        data: extra?.cast<String, dynamic>(),
      ));
    });
  }

  /// Clear user context.
  static void clearUserContext() {
    if (!_initialized) {
      return;
    }

    Sentry.configureScope((scope) {
      scope.setUser(null);
    });
  }

  /// Set a tag on the current scope.
  static void setTag(String key, String value) {
    if (!_initialized) {
      return;
    }

    Sentry.configureScope((scope) {
      scope.setTag(key, value);
    });
  }

  /// Set extra data on the current scope.
  static void setExtra(String key, dynamic value) {
    if (!_initialized) {
      return;
    }

    Sentry.configureScope((scope) {
      scope.setExtra(key, value);
    });
  }

  /// Start a transaction for performance monitoring.
  static SentryTransaction? startTransaction(
    String name, {
    String? operation,
    Map<String, String>? tags,
  }) {
    if (!_initialized) {
      return null;
    }

    return Sentry.startTransaction(
      name,
      operation: operation ?? 'ui.action',
      withScope: (scope) {
        if (tags != null) {
          for (final entry in tags.entries) {
            scope.setTag(entry.key, entry.value);
          }
        }
      },
    );
  }

  /// Measure a function execution time.
  static Future<T> measureAsync<T>(
    String name,
    Future<T> Function() function, {
    String? operation,
    Map<String, String>? tags,
  }) async {
    final transaction = startTransaction(name, operation: operation, tags: tags);
    try {
      final result = await function();
      transaction?.finish(status: const SpanStatus.ok());
      return result;
    } catch (e, stackTrace) {
      transaction?.finish(status: SpanStatus.internalError());
      captureException(e, stackTrace: stackTrace, tags: tags);
      rethrow;
    }
  }

  static void _applyContext(
    Scope scope,
    Map<String, dynamic>? context,
    Map<String, String>? tags,
    SentryLevel level,
  ) {
    if (context != null) {
      for (final entry in context.entries) {
        scope.setExtra(entry.key, entry.value);
      }
    }
    if (tags != null) {
      for (final entry in tags.entries) {
        scope.setTag(entry.key, entry.value);
      }
    }
    scope.setLevel(level);
  }
}

/// Mixin for classes that want to easily capture errors.
mixin ObservabilityMixin {
  void captureError(
    dynamic error, {
    StackTrace? stackTrace,
    Map<String, dynamic>? context,
    String? feature,
  }) {
    ObservabilityService.captureException(
      error,
      stackTrace: stackTrace,
      context: context,
      tags: feature != null ? {'feature': feature} : null,
    );
  }

  void logInfo(
    String message, {
    Map<String, dynamic>? context,
    String? feature,
  }) {
    ObservabilityService.captureMessage(
      message,
      context: context,
      tags: feature != null ? {'feature': feature} : null,
      level: SentryLevel.info,
    );
  }

  void logWarning(
    String message, {
    Map<String, dynamic>? context,
    String? feature,
  }) {
    ObservabilityService.captureMessage(
      message,
      context: context,
      tags: feature != null ? {'feature': feature} : null,
      level: SentryLevel.warning,
    );
  }

  void addBreadcrumb(
    String message, {
    String category = 'custom',
    Map<String, dynamic>? data,
  }) {
    ObservabilityService.addBreadcrumb(message, category: category, data: data);
  }
}