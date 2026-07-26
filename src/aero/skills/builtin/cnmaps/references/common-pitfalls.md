# Common Pitfalls

- Do not invent a `cnmaps` CLI workflow when the task is really about Python APIs.
- Do not assume `level='国'` means China only.
- Do not add `source='世界银行'` or `source='高德'` unless the user actually needs source filtering.
- Do not confuse `MapRecord` metadata rows with raster arrays.
- Do not forget Cartopy projection and axes setup in map code.
- Do not recompute centroids from geometry before checking whether `longitude` / `latitude` are already available on the returned record.
- Do not use `MapPolygon.get_extent()` merely to add visual padding around a complex foreign boundary. It calls a geometric buffer operation; use `.bounds` and add degrees numerically, and never retry the same timed-out `get_extent()` command.
- Do not assume the current sandbox Python environment matches the user's already-configured environment.
- Do not guess return types or parameter names when the reference files can clarify them.
