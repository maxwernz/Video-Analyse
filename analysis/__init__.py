from .codec import AnalysisFileCodec, AnalysisFileFormat
from .document import AnalysisDocument, ExternalChangeChoice, UnsavedChangesChoice
from .errors import (
    AnalysisError,
    AnalysisFileError,
    EmptyAnalysisError,
    ExternalModificationError,
    InvalidAnalysisDataError,
    LegacySourceOverwriteError,
    MalformedJSONError,
    SaveAsRequiredError,
    UnknownEntityError,
    UnsafeLegacyAnalysisError,
    UnsupportedContentError,
    UnsupportedSchemaVersionError,
)
from .legacy import LegacyAnalysisImporter
from .model import Analysis, Category, Clip, SourceVideo, normalize_category_name
from .recovery import RecoverySnapshot, RecoverySnapshotStore
from .template import (
    CategoryTemplateStore,
    DEFAULT_CATEGORY_TEMPLATE,
    apply_category_template,
    new_analysis_document,
)

__all__ = [
    "Analysis",
    "AnalysisDocument",
    "AnalysisError",
    "AnalysisFileCodec",
    "AnalysisFileError",
    "AnalysisFileFormat",
    "apply_category_template",
    "Category",
    "CategoryTemplateStore",
    "Clip",
    "DEFAULT_CATEGORY_TEMPLATE",
    "EmptyAnalysisError",
    "ExternalChangeChoice",
    "ExternalModificationError",
    "InvalidAnalysisDataError",
    "LegacySourceOverwriteError",
    "LegacyAnalysisImporter",
    "MalformedJSONError",
    "new_analysis_document",
    "normalize_category_name",
    "RecoverySnapshot",
    "RecoverySnapshotStore",
    "SaveAsRequiredError",
    "SourceVideo",
    "UnknownEntityError",
    "UnsafeLegacyAnalysisError",
    "UnsavedChangesChoice",
    "UnsupportedContentError",
    "UnsupportedSchemaVersionError",
]
