# Security - VoiceScribe Infra

## Modello di minaccia
- Accesso non autorizzato a endpoint pubblici.
- Esfiltrazione segreti da file/versionamento.
- Movimento laterale tra container.
- Abuso quota free tier e burst di richieste.
- Denial of Service su upload/transcoding.

## Controlli implementati
- Nginx come unico punto pubblico su 80/443.
- Header HTTP di sicurezza + TLS moderno.
- Rate limiting differenziato upload/read.
- Redis con auth obbligatoria.
- PostgreSQL/Redis non esposti all'esterno.
- Segreti su `.env` non versionato.
- Alerting su errori 5xx, saturazione code, ramdisk, servizi GPU.

## Incident response
1. Identificazione: alert e log strutturati JSON.
2. Contenimento: blocco IP/rate stricter, isolamento servizio impattato.
3. Eradicazione: rotazione segreti, patch config, restart controllato.
4. Ripristino: test health end-to-end e monitoraggio intensivo.
5. Post-mortem: RCA documentata e azioni preventive.

## Linee guida sviluppatori
- Non hardcodare segreti nel codice.
- Validare input e MIME/estensioni lato ingestion.
- Rispettare principle of least privilege.
- Applicare review sicurezza su PR sensibili.
- Aggiornare dipendenze con patch security tempestive.
