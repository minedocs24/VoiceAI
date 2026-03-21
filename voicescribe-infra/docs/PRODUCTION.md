# Produzione - Checklist e Guida

## TLS e certificati reali
- Usare Let's Encrypt (certbot) o PKI aziendale.
- Configurare `NGINX_TLS_CERT` e `NGINX_TLS_KEY` con path reali.
- Abilitare rinnovo automatico certificati.

## Hardening PostgreSQL
- Password forti e rotazione periodica.
- Accesso rete limitato al network interno Docker.
- Backup schedulati e test restore periodici.

## Hardening Redis
- `requirepass` obbligatorio.
- Nessuna esposizione pubblica porta 6379.
- Monitoraggio memoria e policy eviction.

## Firewall
- Esporre solo 80/443 pubblicamente.
- Bloccare porte 5432, 6379, 9090, 3000 dall'esterno.

## Backup automatici
- Schedulare `scripts/db-backup.sh` via cron/systemd timer.
- Retention in linea con policy aziendale.
- Validare restore almeno mensilmente.

## Monitoring e alerting
- Prometheus con `alerts.yml` attivo.
- Configurare canali notifica (email/Slack/PagerDuty).
- Dashboard Grafana versionate e revisionate.

## Aggiornamenti senza downtime
- Rolling restart servizi stateless.
- Migrazioni DB backward-compatible.
- Verifica health ad ogni step e rollback plan pronto.
