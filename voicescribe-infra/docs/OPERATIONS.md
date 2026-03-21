# Runbook Operativo

## Job bloccato in stato intermedio (> 1h)
**Sintomi**: Job in PREPROCESSING, TRANSCRIBING, DIARIZING o EXPORTING da oltre 1 ora.
**Causa probabile**: Worker Celery bloccato, servizio downstream non risponde, timeout.
**Diagnosi**: `GET /v1/jobs/{job_id}` per stato; log worker; Prometheus `celery_queue_depth`.
**Risoluzione**: Re-queue job bloccato (vedi sotto). Se necessario restart worker.
**Verifica**: Job riprende e arriva a DONE.

## Ramdisk pieno
1. Verificare uso: `df -h /mnt/ramdisk`.
2. Eseguire cleanup: `bash scripts/cleanup-ramdisk.sh 4`.
3. Se persiste, aumentare size tmpfs o ridurre retention job temporanei.

## Re-queue job bloccato
1. Individuare `job_id` e `celery_task_id`.
2. Revocare task bloccato dal worker.
3. Innescare endpoint di retry su SVC-05 (`/jobs/{job_id}/retry`).

## Worker GPU non risponde
**Sintomi**: Nessun job completato da 2+ ore, servizi SVC-06/SVC-07 down.
**Causa probabile**: OOM GPU, driver crash, modello non caricato.
**Diagnosi**: `nvidia-smi`, log container SVC-06/SVC-07, `/gpu/status`.
**Risoluzione**: Restart container; verificare VRAM; ridurre batch size.
**Verifica**: `up{job=~"voicescribe_svc06|voicescribe_svc07"}` = 1.

## Stato code Celery
- Verificare metriche Prometheus (`celery_queue_depth`).
- Con worker attivi: controllare `active`, `reserved`, `scheduled`.

## Diagnosi performance GPU
1. Controllare latenza inference dashboard pipeline.
2. Verificare stato GPU (`nvidia-smi`, temperatura, memoria).
3. Verificare carico code `gpu_tasks` e possibili colli CPU in pre-processing.

## Contatori Redis e PostgreSQL inconsistenti
**Sintomi**: Alert `QuotaRedisPostgresInconsistent`; quota Free Tier errata.
**Causa probabile**: Crash durante consume/rollback, TTL Redis scaduto in modo anomalo.
**Diagnosi**: Confrontare `voicescribe_quota_redis_count` e `voicescribe_quota_postgres_count` in Prometheus.
**Risoluzione**: Script di riconciliazione (allineare Redis a PostgreSQL); in casi estremi reset chiavi quota Redis.
**Verifica**: Differenza < 5.

## Certificato TLS scaduto
**Sintomi**: Client non si connettono, errore certificato.
**Risoluzione**: Rinnovo Let's Encrypt (`certbot renew`) o sostituzione cert PKI; reload nginx.

## Backup e ripristino database
**Backup**: `make backup` o `bash scripts/db-backup.sh`.
**Restore**: `make restore FILE=/path/backup.dump` o `bash scripts/db-restore.sh FILE`.
**Verifica**: Test restore su ambiente staging almeno mensilmente.

## Rotazione API key senza disservizio
1. Generare nuova key e hash.
2. Abilitare doppia validazione temporanea.
3. Distribuire nuova key ai client.
4. Revocare key precedente a finestra scaduta.
