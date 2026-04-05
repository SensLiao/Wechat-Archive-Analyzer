# Errors

Command failures and integration errors.

---

## [ERR-20260405-001] pytest startup encoding

**Logged**: 2026-04-05T00:00:00Z
**Priority**: medium
**Status**: pending
**Area**: tests

### Summary
`pytest` failed before collecting tests because Python started in GBK mode and could not decode a `.pth` file.

### Error
```text
Fatal Python error: init_import_site: Failed to import the site module
UnicodeDecodeError: 'gbk' codec can't decode byte 0xa5 in position 13: illegal multibyte sequence
```

### Context
- Command attempted: `pytest ...`
- Environment: Windows + Anaconda default Python startup
- Relevant repo guidance already exists in `README.md`: use `python -X utf8 -m ...` when the environment is not UTF-8 safe

### Suggested Fix
Run tests and CLI commands with `python -X utf8 -m ...` in this environment.

### Metadata
- Reproducible: yes
- Related Files: README.md

---
