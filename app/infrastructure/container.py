from __future__ import annotations

from app.core.ports.ai_provider import AIProvider
from app.core.ports.auth import AuthProvider
from app.core.ports.repositories import AnalysisRepository, MediaRepository
from app.core.ports.storage import StorageProvider
from app.core.use_cases.analyze_media import AnalyzeMediaUseCase
from app.core.use_cases.ingest_media import SubmitMediaUseCase
from app.core.use_cases.query_analysis import AnalysisQueryUseCase
from app.core.use_cases.query_media import MediaQueryUseCase
from app.infrastructure.ai.openai_provider import OpenAIProvider
from app.infrastructure.auth.supabase_auth import SupabaseAuthProvider
from app.infrastructure.config import Settings, get_settings
from app.infrastructure.db.supabase_repositories import (
    SupabaseAnalysisRepository,
    SupabaseMediaRepository,
)
from app.infrastructure.storage.supabase_storage import SupabaseStorageProvider


class Container:
    """Composition root: wires concrete adapters into the use cases.

    Dependencies can be overridden for tests via the keyword arguments.
    """

    def __init__(
        self,
        settings: Settings,
        *,
        media_repository: MediaRepository | None = None,
        analysis_repository: AnalysisRepository | None = None,
        ai_provider: AIProvider | None = None,
        storage_provider: StorageProvider | None = None,
        auth_provider: AuthProvider | None = None,
    ):
        self.settings = settings
        self.media_repository = media_repository or SupabaseMediaRepository(settings)
        self.analysis_repository = analysis_repository or SupabaseAnalysisRepository(settings)
        self.ai_provider = ai_provider or OpenAIProvider(settings)
        self.storage_provider = storage_provider or SupabaseStorageProvider(settings)
        self.auth_provider = auth_provider or SupabaseAuthProvider(settings)

        self.submit_media_use_case = SubmitMediaUseCase(
            self.media_repository, self.analysis_repository
        )
        self.analyze_media_use_case = AnalyzeMediaUseCase(
            self.media_repository,
            self.analysis_repository,
            self.ai_provider,
            self.storage_provider,
        )
        self.media_query_use_case = MediaQueryUseCase(self.media_repository)
        self.analysis_query_use_case = AnalysisQueryUseCase(self.analysis_repository)

    @classmethod
    def build(cls) -> Container:
        return cls(get_settings())
