# Security Model - File Ingestion Service

## Threat model

- Upload di file malevoli rinominati con estensioni lecite
- Path traversal tramite header tenant/job manipolati
- Escalation via symlink nella gerarchia storage
- Disk exhaustion tramite upload ripetuti o upload interrotti
- Corruzione dati in transito

## Mitigazioni implementate

1. **Autenticazione inter-servizio**
   - Header obbligatorio `X-Internal-Token` su endpoint protetti.

2. **Validazione payload file**
   - Extension whitelist da configurazione.
   - Validazione magic bytes indipendente dal filename.
   - Coerenza extension dichiarata vs formato rilevato.

3. **Path traversal prevention**
   - `tenant_id` validato come slug alfanumerico.
   - `job_id` validato come UUID.
   - Verifica percorso risolto sempre sotto `STORAGE_BASE_PATH`.

4. **Symlink checks**
   - Blocco salvataggio finale se componenti path esistenti sono symlink.

5. **Disk safeguards**
   - Check spazio disponibile minimo `2 * UPLOAD_MAX_BYTES` prima dell'upload.
   - Health report con stato degraded oltre soglia configurabile.

6. **Checksum verification (opzionale)**
   - Header `X-Expected-SHA256` confrontato con hash streaming calcolato server-side.

7. **Temp files cleanup**
   - Task periodico rimuove file temporanei più vecchi di 1 ora (default).

## Note operative

- Montare `/data/input` su volume persistente.
- Eseguire container come utente non-root.
- Rotare `INTERNAL_SERVICE_TOKEN` periodicamente.