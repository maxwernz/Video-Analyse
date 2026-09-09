# Use versioned JSON for Analysis files

New Analysis files use schema-versioned UTF-8 JSON under the existing `.analysis` extension, while an isolated restricted importer reads supported legacy pickle files and requires Save As before conversion. This advances the compatibility promise in ADR 0002 without retaining executable pickle as the writable format, and keeps large Source videos external to the document.

## Consequences

- Content detection distinguishes JSON from legacy pickle; the extension does not select an unsafe decoder. The legacy importer allowlists only the exact historical `ClipItem` representation and required safe built-ins, preserves all legacy Clip data and order, creates stable IDs, derives Categories by normalized name, and maps the legacy path to one Source video.
- The application writes only the current JSON schema. An integer schema version selects explicit stepwise in-memory migrations for every supported older JSON version; unknown newer versions are rejected without modifying the file.
- Decoding, migration, and complete model validation happen before replacing the active Analysis document. Malformed, unsupported, or invalid files produce specific user-facing diagnostics while preserving the current document.
- AnalysisFileCodec owns JSON encoding, decoding, validation, and migration. LegacyAnalysisImporter owns restricted conversion. AnalysisDocument owns file location, content revision, dirty state, atomic saving, Recovery snapshots, and detection of external file changes.
- Durable content changes mark the Analysis document dirty. Playback position, active Source video, selection, Clip-view sorting, and expanded UI sections are transient.
- Writes use an atomic replacement. A save failure leaves the document dirty. If the Analysis file changed externally since loading, saving offers reload or Save As instead of silently overwriting it.
- A debounced Recovery snapshot is stored separately after durable changes and removed after a successful save, clean close, or deliberate discard. It is offered only after abnormal termination and never counts as a successful save.
