# VoiceScribe Diarization Engine (SVC-07)

Servizio standalone per **speaker diarization**: risponde a "chi ha parlato e quando?" assegnando etichette speaker ai segmenti temporali (e opzionalmente ai segmenti di una trascrizione esistente).

## Obiettivo

Fornire un motore di diarizzazione riutilizzabile in qualsiasi progetto, indipendente da VoiceScribe AI: meeting recorder, call center QA, trascrizione legale, analisi conversazioni.

## Endpoint principali

- `POST /diarize` — diarizzazione su file audio; body opzionale `segments` per allineare alla trascrizione (merge)
- `GET /models/status` — stato modello (caricato, token HF valido, VRAM, tempo di caricamento)
- `GET /health` — health check
- `GET /metrics` — metriche Prometheus

## Uso con e senza trascrizione

- **Con trascrizione**: invia `segments` (es. output di Whisper/SVC-06); il servizio allinea la timeline speaker ai segmenti e restituisce ogni segmento con `speaker` (es. `SPEAKER_00`, `SPEAKER_01`).
- **Senza trascrizione**: omettere `segments`; il servizio restituisce solo la timeline speaker (intervalli temporali + etichetta), utile per contesti in cui non c’è una trascrizione da allineare.

## Avvio rapido standalone

1. Copia `.env.example` in `.env`.
2. Configura **`HUGGINGFACE_TOKEN`** (obbligatorio): vedi [docs/HUGGINGFACE-SETUP.md](docs/HUGGINGFACE-SETUP.md).
3. Configura `INTERNAL_SERVICE_TOKEN` e `SVC05_URL` se usi callback (pipeline VoiceScribe).
4. Avvio API:
   ```bash
   python run.py
   ```
5. Worker Celery (coda `gpu_tasks`, concorrenza 1):
   ```bash
   celery -A app.celery_app worker -Q gpu_tasks -c 1 --loglevel=info
   ```

## Docker

- Build con token HF come secret (non in layer history):
  ```bash
  docker build --secret id=hf_token,env=HUGGINGFACE_TOKEN -t voicescribe-diarization-engine .
  ```
- Porta 8006.

## Requisiti

- Python 3.11+
- GPU NVIDIA con CUDA (consigliato); Pyannote richiede ~2–3 GB VRAM.
- Token HuggingFace con termini d’uso accettati per il modello Pyannote.

## Documentazione

- [docs/HUGGINGFACE-SETUP.md](docs/HUGGINGFACE-SETUP.md) — token e termini d’uso
- [docs/REUSABILITY.md](docs/REUSABILITY.md) — uso standalone e integrazione con altre fonti
- [docs/MERGE-ALGORITHM.md](docs/MERGE-ALGORITHM.md) — algoritmo di merge trascrizione + diarizzazione
