/// ANNEX shared Flutter features (Phase 12).
///
/// The cross-platform feature layer reused by every Flutter app: the API
/// client + mock, the runtime i18n controller, the auth gateway + mock,
/// the feature controllers and screens, the observability service, and the
/// [AppScope] composition root. Apps contribute only their platform-specific
/// shell and entry point (ADR-0003, ADR-0005, ADR-0007).
library;

export 'src/api/analysis_api.dart';
export 'src/api/mock_analysis_api.dart';
export 'src/app/app_scope.dart';
export 'src/features/analysis/analysis_controller.dart';
export 'src/features/analysis/analysis_screen.dart';
export 'src/features/auth/auth_controller.dart';
export 'src/features/auth/auth_gateway.dart';
export 'src/features/auth/mock_auth_gateway.dart';
export 'src/features/auth/sign_in_screen.dart';
export 'src/features/classes/classes_controller.dart';
export 'src/features/classes/classes_screen.dart';
export 'src/features/lessons/lessons_controller.dart';
export 'src/features/lessons/lessons_screen.dart';
export 'src/features/settings/settings_controller.dart';
export 'src/features/settings/settings_screen.dart';
export 'src/features/sources/sources_controller.dart';
export 'src/features/sources/sources_screen.dart';
export 'src/features/suggestions/suggestions_controller.dart';
export 'src/features/suggestions/suggestions_screen.dart';
export 'src/i18n/i18n_controller.dart';
export 'src/observability/observability.dart';
