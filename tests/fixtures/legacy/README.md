# Legacy Analysis compatibility fixtures

`cup-final.analysis` is a representative Analysis file written by the original
single-Source-video application. Its pickle contains the historical
`treewidget_item.ClipItem` values exactly as the application wrote them: named
Clips, timestamps, notes, categories, and one external Source-video path.

The fixture deliberately names media that is absent from the repository. The
compatibility test must therefore prove both that the saved Analysis opens with
its analytical content intact and that relinking supplies a new external
location without embedding media in the Analysis file.

It is test data for the restricted legacy reader only. Never open a pickle-based
Analysis from an unknown source: Python cannot safely vet an unknown pickle
before deserializing it.
