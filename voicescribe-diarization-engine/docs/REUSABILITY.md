# Riutilizzo del servizio di diarizzazione

Il Diarization Engine è progettato per essere usato in contesti diversi da VoiceScribe: meeting recorder, call center, trascrizione legale, qualsiasi pipeline che richieda “chi ha parlato quando”.

## Solo diarizzazione (senza trascrizione)

Se non hai una trascrizione e ti serve solo la **timeline speaker** (intervalli temporali con etichetta speaker):

- Chiama `POST /diarize` con solo `job_id` e `input_path` (file audio).
- Lascia **`segments`** vuoto o omesso.
- La risposta conterrà `segments` vuoto e, se supportato dall’implementazione, una timeline speaker (o puoi derivare gli speaker dalla risposta).

In questo modo il servizio funziona come diarizzatore puro, indipendente da Whisper o da SVC-06.

## Integrazione con qualsiasi fonte di segmenti

Se hai segmenti temporali (start, end, testo opzionale) da **qualsiasi** sorgente (Whisper, altro STT, sottotitoli):

- Invia in `POST /diarize` il body con `input_path`, `job_id` e **`segments`** = lista di oggetti con almeno `start`, `end` e opzionalmente `text`, `confidence`, `words`, ecc.
- Il servizio esegue la diarizzazione sull’audio e allinea gli speaker ai tuoi segmenti con l’algoritmo di merge (massima sovrapposizione temporale).
- In risposta ricevi gli stessi segmenti arricchiti con il campo **`speaker`** (es. `SPEAKER_00`, `SPEAKER_01`) e la lista **`speakers`** con il conteggio degli interventi.

Non è necessario usare SVC-06: qualsiasi client che produca segmenti con timestamp può inviare `segments` a SVC-07.

## Pipeline VoiceScribe

Nella pipeline VoiceScribe, SVC-05 (Job Orchestrator) invia a SVC-07 un task Celery sulla coda `gpu_tasks` con `transcription_raw` (output di SVC-06). Il worker SVC-07 esegue la diarizzazione, fa il merge con i segmenti trascrizione e invia il callback a SVC-05. In questo caso l’integrazione è tramite coda e callback; l’API REST `POST /diarize` resta disponibile per uso diretto o per altri orchestrator.

## Coda GPU condivisa

Trascrizione (SVC-06) e diarizzazione (SVC-07) condividono la coda **`gpu_tasks`** con concorrenza 1 per evitare OOM sulla stessa GPU. In deployment puoi avere un unico worker che consuma `gpu_tasks` e registra sia i task di trascrizione che di diarizzazione, così da serializzare l’uso della GPU.
