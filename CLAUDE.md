# WeChat Tools

## Project Overview

Local-first toolkit for decrypting and analyzing WeChat PC chat history. Primary interface is the `/wechat` Claude Code skill; also usable as a standalone CLI (`wxtools`). Single data source (WeChat), DDD-inspired layered architecture.

## Document References

All project documents are in `Project_docs/` (git-ignored, local-only). v1 docs in `Project_docs/v1/`, v2 docs in `Project_docs/v2/`, shared docs at `Project_docs/` root.

### Shared (Cross-version)

| Document | Path | Purpose |
|----------|------|---------|
| `Questions.md` | `Project_docs/` | Living audit checklist — only unresolved items remain |
| `glossary.md` | `Project_docs/` | Unified terminology (wxid, MsgSvrID, shard, etc.) |
| `legal_and_compliance_notes.md` | `Project_docs/` | User responsibility, ToS, process memory reading implications |

### v1 — Planning & Requirements

| Document | Path | Purpose |
|----------|------|---------|
| `project_plan.md` | `v1/` | ⚠️ Historical draft — superseded by architecture_overview.md |
| `product_requirements.md` | `v1/` | PRD: personas, use cases, MVP scope, non-goals, acceptance criteria |
| `decisions_log.md` | `v1/` | All design decisions (DEC-01 to DEC-25) with rationale |
| `roadmap_and_milestones.md` | `v1/` | Phase 1/2/3 deliverables, DoD, risks, estimated effort |

### v1 — Architecture & Contracts

| Document | Path | Purpose |
|----------|------|---------|
| `architecture_overview.md` | `v1/` | Layer diagram, module boundaries, runtime call chains, v1 vs future |
| `cli_contract.md` | `v1/` | CLI commands, args, JSON envelope schema, error codes |
| `skill_contract.md` | `v1/` | `/wechat` skill trigger rules, command mapping, error handling, security |
| `local_storage_layout.md` | `v1/` | `~/.wxtools/` directory structure, file naming, ACL, cache metadata |

### v1 — Technical Research

| Document | Path | Purpose |
|----------|------|---------|
| `wechat_key_research.md` | `v1/` | SQLCipher params, key extraction method, memory scan algorithm, validation |
| `wechat_db_schema.md` | `v1/` | DB file inventory, table schemas, message type mapping, cross-DB joins |
| `sqlcipher_backend_decision.md` | `v1/` | pysqlcipher3 vs CLI vs bundled DLL comparison |

### v1 — Security

| Document | Path | Purpose |
|----------|------|---------|
| `security_model.md` | `v1/` | Key/cache/log protection design, DPAPI/Fernet, redaction rules, read-only guarantees |
| `threat_model.md` | `v1/` | STRIDE-based analysis, 9 threats, risk matrix, accepted risks |

### v1 — Testing & Compatibility

| Document | Path | Purpose |
|----------|------|---------|
| `test_plan.md` | `v1/` | Test layers, unit/integration/system test plans, mock seams, edge cases |
| `test_data_strategy.md` | `v1/` | Synthetic DB fixtures, golden outputs, real data prohibition |
| `compatibility_matrix.md` | `v1/` | WeChat/Windows/Python/SQLCipher version support matrix |

### v1 — Engineering & Release

| Document | Path | Purpose |
|----------|------|---------|
| `config_schema.md` | `v1/` | All config keys, types, defaults, validation, env overrides |
| `logging_and_observability.md` | `v1/` | Log levels, stream routing, redaction, progress, debug modes |
| `export_formats.md` | `v1/` | v1 JSON export schema, manifest, filename rules, streaming write |
| `packaging_and_release.md` | `v1/` | pyproject.toml structure, versioning, install path, release checklist |
| `development_process.md` | `v1/` | Branch/commit conventions, design change process, doc sync rules |
| `troubleshooting.md` | `v1/` | Common issues: key extraction, decryption, queries, paths, skill |

### v1 — Implementation Plans

| Document | Path | Purpose |
|----------|------|---------|
| `2026-04-04-wxtools-v1-implementation.md` | `v1/plans/` | v1 full implementation plan with task breakdown |

### v2 — Design & Implementation

| Document | Path | Purpose |
|----------|------|---------|
| `2026-04-04-project_audit_v1_status_and_v2_design.md` | `v2/` | v1 completion audit + v2 scope definition |
| `2026-04-04-wxtools-v2-design-spec.md` | `v2/` | v2 detailed design: key lifecycle, export scaling, attachments, future roadmap |
| `2026-04-04-wxtools-v2-hardening-and-capability-completion.md` | `v2/` | v2 hardening decisions and capability gap analysis |
| `2026-04-04-wxtools-v2-implementation-plan.md` | `v2/` | v2 implementation plan with phased task breakdown (A/B/C) |

### Naming Convention

- Descriptive names: `<topic>.md` (e.g., `security_model.md`)
- Dated notes: `YYYY-MM-DD-<topic>.md` (e.g., `2026-04-04-wxtools-v2-design-spec.md`)
- `changelog.md` — create when development starts

## Key Technical Facts

- WeChat DB encryption: SQLCipher 4 (AES-256-CBC), key is permanent per account
- Key extraction requires admin privileges + WeChat running (one-time)
- All data stays local by default
- Target WeChat version: 4.1.7.59
- WeChat 4.x data path: `C:\Users\<user>\Documents\xwechat_files\wxid_<hash>\db_storage\`
- WeChat 3.x fallback: `C:\Users\<user>\Documents\WeChat Files\<wxid>\Msg\`
- Auto-discovery checks 4.x location first

## Skill

- **Name:** `wechat`
- **Invocation:** `/wechat` in Claude Code
- **Install:** `wxtools install-skill` copies skill template to `~/.claude/skills/wechat/SKILL.md`
- **CLI:** `wxtools key | query | export | cache | config` (monitor deferred to v2)

## Project Structure

```
wxtools/
├── src/wxtools/                  # Python package
│   ├── domain/                   # Core models (schema.py) and error hierarchy (errors.py)
│   ├── runtime/                  # Config, logging, platform detection, bootstrap, app_host, paths
│   ├── infrastructure/
│   │   ├── wechat/               # WeChat data access: account discovery, key extraction, decryption, DB reading
│   │   ├── secrets/              # Keystore, unlock session, secret backends (DPAPI, Keychain, etc.)
│   │   ├── storage/              # ACL, workspace/export storage
│   │   └── exporters/            # Export format writers (JSON, CSV, HTML)
│   ├── application/              # Business services (shared by all interfaces)
│   ├── interfaces/
│   │   ├── cli/                  # Click CLI entry point (thin adapter)
│   │   ├── api/                  # FastAPI REST API with ApiEnvelope response model
│   │   └── desktop/              # Electron desktop backend entry point
│   └── adapters/                 # AI agent skill templates (Claude Code, Codex)
├── web/                          # React SPA (Vite + TypeScript)
├── desktop/                      # Electron desktop shell + build pipeline
│   ├── build/                    # PyInstaller spec
│   └── scripts/                  # Build orchestration
├── tests/
├── docs/
├── evals/
├── pyproject.toml
└── CLAUDE.md
```

### Dependency direction (strict one-way)

```
interfaces/cli/ ─┐
interfaces/api/ ─┤──→ application/ ──→ infrastructure/wechat/ ──→ domain/
interfaces/desktop/─┘       │                    │
                            └──→ infrastructure/exporters/ ──→ domain/
                            └──→ infrastructure/secrets/   ──→ domain/
```

## Development Rules

- `Project_docs/` is git-ignored — design docs are local-only
- Core package lives under `src/wxtools/`
- `interfaces/cli/` and `interfaces/api/` are thin adapters — all business logic lives in `application/`
- `infrastructure/exporters/` is a shared module used by application services
- All CLI commands support `--json` flag for programmatic output
- V6 dual-track: `main` branch = public CLI + skill; `desktop-local` branch = private Electron app
- Plugin abstraction removed in V6 — single data source (WeChat), no multi-source registry
- All API routes return `ApiEnvelope` wrapper: `{"ok": bool, "data": T, "error": {...}}`
- Web UI exports default to browser download (.zip via temp dir); CLI exports write to specified `output_dir`
- Export download endpoint (`/api/export/download/{id}`) uses query-param token auth (not header) since browsers navigate directly
- `app start` auto-reclaims port if a previous server didn't shut down cleanly
- Session token injected server-side into HTML (`window.__WXTOOLS_TOKEN__`), no localStorage dependency
- **Auto-push rule:** 在 implementation 过程中，当代码变更已成熟（bug fix、feature 完成、配置修正等不需要用户额外决策的改动），完成 commit 后应立即 `git push` 到 GitHub，无需每次询问用户确认

## Questions.md Maintenance Rule

`Project_docs/Questions.md` is the living audit checklist. When an item is fully addressed by a design document or decision, **delete it from Questions.md immediately** — do not mark it DONE, just remove the row. Only unresolved items remain in the file.
