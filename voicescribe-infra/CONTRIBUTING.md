# Contribuire a VoiceScribe Infra

## Workflow branch
- `main`: branch stabile.
- `feat/<scope>-<descrizione>`: nuove funzionalita.
- `fix/<scope>-<descrizione>`: correzioni bug.
- `chore/<scope>-<descrizione>`: manutenzione tecnica.

## Commit message (Conventional Commits)
Usare il formato:

```text
type(scope): short summary
```

Esempi:
- `feat(infra): add prometheus alerts for gpu availability`
- `fix(nginx): harden tls and security headers`
- `docs(setup): update ubuntu prerequisites`

## Pull request
1. Aprire PR piccole e focalizzate.
2. Descrivere contesto, cambiamenti e rollback plan.
3. Includere evidenze test (`docker compose config`, smoke test, script healthcheck).
4. Non committare segreti (`.env`, chiavi, certificati reali).

## Dipendenze
- Aggiornare dipendenze solo quando necessario e documentare il motivo.
- Preferire versioni stabili e compatibili con documento tecnico v2.
- Verificare impatti di sicurezza prima del merge.
