# Video Analyse

Video Analyse is a desktop application for reviewing video and producing analysis data and clips.

## Language

**Internal distribution**:
Self-service delivery of the desktop application to its owner and a small group of trusted users on unmanaged macOS and Windows devices.
_Avoid_: Enterprise deployment, managed deployment, public distribution

**Analysis**:
A user's editable body of analytical work spanning zero or more Source videos. It has a user-controlled title, contains Clips and Analysis-wide Categories, and may be used for either own-match review or opponent preparation without changing its type.
_Avoid_: Project, workspace

**Opponent preparation**:
The review of one or more previous matches involving an upcoming opponent, performed to prepare the user's team to play against that opponent.
_Avoid_: Analysis type, mode

**Analysis file**:
A durable on-disk representation of an Analysis, which newer application releases must continue to open.
_Avoid_: Project file, save file

**Analysis document**:
The lifecycle of one Analysis while it is being edited, including its file location, dirty state, loading, saving, and recovery.
_Avoid_: Analysis file, editor session

**Recovery snapshot**:
A temporary, separately stored representation of unsaved Analysis changes used after an abnormal application exit. It is not an Analysis file or a successful save.
_Avoid_: Autosave, backup

**Source video**:
A video recording referenced by an Analysis but stored outside its Analysis file. It has an editable display name, and its identity remains stable when the media file is moved and relinked.
_Avoid_: Video file, media asset

**Active Source video**:
The single Source video currently loaded in the one player. Navigating to a Clip makes that Clip's Source video active. It is transient presentation state and is never stored in an Analysis file.
_Avoid_: Current video, selected video

**Clip**:
A named, editable time interval belonging to exactly one Source video, with optional notes and an optional Category.
_Avoid_: Segment, marker

**Pending Clip**:
A temporary Clip boundary state after a start has been set on the Active Source video but before an end has been set. It is not part of the Analysis and cannot move to another Source video.
_Avoid_: Recording, unsaved Clip

**Category**:
An ordered, color-coded, Analysis-wide classification that can group Clips from different Source videos. Renaming a Category preserves its relationship to existing Clips.
_Avoid_: Folder, tag

**Category template**:
A reusable starting collection of Categories that is copied into an Analysis and may then be customized without changing the template. The initial template is designed for handball analysis.
_Avoid_: Fixed categories, category preset

**Combined export**:
A single presentation video assembled from selected Clips. Its ordering and presentation settings are independent of the ordering stored in the Analysis.
_Avoid_: Full video export, source export

**Export list**:
The temporary ordered collection of Clips used to produce a Combined export. It initially groups Clips by Category and may be rearranged without changing the Analysis.
_Avoid_: Playlist, Clip list
