# CA Render Package String `.get()` Hotfix V1

Fixes a Competitive Analysis Task 2 crash where normalized KPI rows could be held as a `{brand: row}` mapping and then passed into the shared `_leader()` helper. Iterating the mapping directly yielded brand-name strings, causing `'str' object has no attribute 'get'` during PPT package generation after the audience gate.

The helper now accepts either a list of row mappings or a mapping of row mappings, ignores malformed non-mapping entries, and returns `None` safely when no valid rows exist.
