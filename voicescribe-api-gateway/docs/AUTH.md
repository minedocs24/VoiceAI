# Autenticazione VoiceScribe API Gateway

## Meccanismi

Il gateway supporta due meccanismi paralleli:

### 1. JWT (Free Tier)

- Login con email e password
- Password hashata con bcrypt, mai salvata in chiaro
- Access token: JWT con scadenza configurabile (default 24 ore)
- Payload: `tenant_id`, `tier`, `iat`, `exp`, `jti`
- Refresh token: scadenza più lunga (default 7 giorni), salvato in Redis con TTL
- Revoca: cancellazione refresh token da Redis

### 2. API Key (PRO/Enterprise)

- Formato: `vs_live_{32 caratteri alfanumerici}`
- Salvato in DB come SHA-256, mai in chiaro
- Header: `X-API-Key`
- Verifica: hash della chiave ricevuta confrontato con DB
- Cache Redis 60s per ridurre query
- Revoca: aggiornamento `api_key_hash` in DB (nuova chiave)

## Ciclo di vita JWT

1. **Login**: POST /v1/auth/login → access_token + refresh_token
2. **Uso**: Header `Authorization: Bearer <access_token>`
3. **Refresh**: POST /v1/auth/refresh con refresh_token → nuovo access_token
4. **Logout**: POST /v1/auth/logout con refresh_token → invalida refresh in Redis

## Generazione e rotazione API Key

- Le API key vengono generate con `secrets.token_hex(16)` → `vs_live_` + 32 caratteri
- Per rotare: generare nuova chiave, salvare SHA-256 in `tenants.api_key_hash`, comunicare nuova chiave al cliente
- La vecchia chiave cessa di funzionare immediatamente (cache Redis 60s max)

## Dependency unificata

Tutti i router usano `get_authenticated_tenant` che accetta:
- `Authorization: Bearer <jwt>` oppure
- `X-API-Key: vs_live_...`

e restituisce `AuthenticatedTenant(tenant_id, tier, permissions)`.
