# Preserve Analysis files across releases

Analysis files are durable user data, so each application release must continue to open files produced by the current application and later supported versions. The current pickle representation remains temporarily, backed by representative legacy fixtures and compatibility tests; replacing it with a versioned format is separate work and must retain a legacy reader. Users may exchange files within the trusted internal group, but must not open pickle-based Analysis files from unknown sources because deserialization can execute code.

When an Analysis file's source video is no longer at its recorded location, the application should let the user locate and relink the video without embedding the video itself. This behavior belongs to the Analysis-file contract and does not prescribe how a future storage format represents the reference.
