# Riutilizzo del servizio di export

L'Export Service è progettato per essere usato in contesti diversi da VoiceScribe: pipeline di report automatici, meeting recorder, generazione documenti da qualsiasi sorgente con segmenti temporali.

## Template DOCX per brand diversi

I parametri del documento Word sono configurabili in `config/export.yml`:

```yaml
docx:
  header:
    title: "Trascrizione"
    subtitle_template: "Progetto: {project_name}"
  typography:
    font_family: "Calibri"
    font_size_pt: 11
    speaker_colors:
      - "#2E75B6"
      - "#C55A11"
      # ...
```

Per un brand diverso, crea un file `config/export-brand.yml` e caricalo al posto di `export.yml`, oppure usa variabili d'ambiente per il path del config.

## Aggiungere nuovi formati

1. Crea un generatore in `app/generators/` (es. `pdf_generator.py`) con una classe che espone `generate(data, **kwargs) -> str | bytes`
2. Aggiungi il formato a `TIER_FORMATS` in `app/services/export_service.py` (se dipende dal tier)
3. Aggiungi il flag `ENABLE_PDF` in `app/core/config.py` e il blocco di generazione in `run_export()`
4. Documenta il nuovo formato in `docs/FORMAT-REFERENCE.md`

L'interfaccia pubblica `POST /export` non cambia: il body accetta già `formats` come lista, quindi aggiungere un nuovo valore è retrocompatibile.

## Pipeline di report automatici

Il servizio può essere usato come step finale di una pipeline:

1. **Input**: qualsiasi sorgente che produca segmenti con `start`, `end`, `text` (e opzionalmente `speaker`)
2. **Chiamata**: `POST /export` con `transcript` = struttura dati
3. **Output**: file scritti in `{OUTPUT_BASE_PATH}/{tenant_id}/{job_id}/`

Esempio con script Python:

```python
import httpx

data = {
    "job_id": "report-001",
    "tenant_id": "analytics",
    "tier": "PRO",
    "transcript": {
        "job_id": "report-001",
        "language": "en",
        "duration": 300,
        "segments": [
            {"start": 0, "end": 10, "text": "Quarterly results..."},
            {"start": 10, "end": 25, "text": "Revenue increased by 15%.", "speaker": "SPEAKER_00"},
        ],
    },
    "formats": ["txt", "docx"],
}
r = httpx.post(
    "http://export-service:8007/export",
    json=data,
    headers={"X-Internal-Token": "..."},
)
print(r.json()["download_urls"])
```

## Integrazione con VoiceScribe

Nella pipeline VoiceScribe, SVC-05 (Job Orchestrator) invia un task Celery sulla coda `export_tasks`. Il worker SVC-08 consuma il task, genera i documenti, invia callback a SVC-05, pubblica su Redis per il WebSocket, e invia il webhook al tenant (se configurato).
