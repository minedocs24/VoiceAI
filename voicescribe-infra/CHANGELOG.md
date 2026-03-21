# Changelog

Tutte le modifiche rilevanti a questo progetto sono documentate in questo file.

Il formato segue [Keep a Changelog](https://keepachangelog.com/it/1.1.0/)
e il versionamento segue [Semantic Versioning](https://semver.org/lang/it/).

## [1.0.0] - 2026-03-14

### Added
- Inizializzazione repository `voicescribe-infra`.
- Setup infrastruttura condivisa FASE_00 (Compose, DB schema, Redis, Nginx, Prometheus, Grafana, script, documentazione).
- FASE_08: Docker Compose completo con tutti gli 8 servizi (SVC-01..08).
- Test e2e (scenari Free Tier, PRO, Resilienza, Carico).
- Script `verify-openapi-consistency.sh`, `security-audit.sh`.
- `.gitleaks.toml` per prevenzione segreti.
- Test di penetrazione basilari in `tests/security/`.
- Dashboard Grafana aggiornata, alert rules con runbook link.
- Documentazione: ARCHITECTURE (pattern, state machine, ADR), OPERATIONS (runbook emergenze).
