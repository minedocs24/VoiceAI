# ADR-001: Atomicità quota con Redis INCR

## Stato

Accettato

## Contesto

Il Quota Manager deve garantire che il conteggio delle operazioni consumate non superi mai il limite giornaliero, anche in presenza di decine di richieste simultanee (race condition).

## Decisione

Utilizzare Redis con operazione `INCR` atomica in una pipeline insieme a `EXPIRE` per il TTL. La chiave ha formato `quota:{tenant_id}:{YYYY-MM-DD}` e il TTL è calcolato come secondi mancanti alla mezzanotte UTC.

## Alternative considerate

### 1. Lock su database (PostgreSQL)

- **Pro**: Persistenza garantita, transazioni ACID
- **Contro**: Latenza maggiore, rischio di deadlock, non ottimale per alta concorrenza

### 2. Lua script Redis

- **Pro**: Atomicità garantita, logica complessa possibile
- **Contro**: Maggiore complessità, manutenzione script, INCR+EXPIRE è sufficiente

### 3. Contatore in memoria (Python)

- **Contro**: Non distribuito, perso al restart, non scalabile

## Rischi

- **Redis non disponibile**: Il servizio risponde 503. Il check quota fallisce in modo conservativo (denied).
- **Scrittura PostgreSQL fallita**: Loggata ma non propagata. Redis è fonte di verità; PostgreSQL è solo per analytics.

## Trade-off accettati

- Redis è dipendenza critica per le operazioni in tempo reale
- PostgreSQL è opzionale per il funzionamento core (solo analytics)
- Il TTL alla mezzanotte UTC richiede che tutti i client usino timezone coerente
