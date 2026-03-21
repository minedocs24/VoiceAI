# Configurazione token HuggingFace per Pyannote

Il modello **pyannote/speaker-diarization-3.1** è ospitato su Hugging Face e richiede un token valido e l’accettazione dei termini d’uso.

## 1. Creare un account Hugging Face

Se non ce l’hai già: [https://huggingface.co/join](https://huggingface.co/join).

## 2. Creare un token di accesso

1. Vai su [https://huggingface.co/settings/tokens](https://huggingface.co/settings/tokens).
2. Clicca **“Create new token”**.
3. Assegna un nome (es. `voicescribe-diarization`) e permessi **Read**.
4. Copia il token (inizia con `hf_...`). Non condividerlo e non committarlo nel codice.

## 3. Accettare i termini d’uso del modello

1. Vai alla pagina del modello: [https://huggingface.co/pyannote/speaker-diarization-3.1](https://huggingface.co/pyannote/speaker-diarization-3.1).
2. Accetta i **terms of use** della pagina (pulsante “Agree and access repository”).
3. Se richiesto, accetta anche i termini per il modello di segmentazione dipendente: [https://huggingface.co/pyannote/segmentation-3.0](https://huggingface.co/pyannote/segmentation-3.0).

## 4. Configurare il servizio

- **Ambiente locale**: crea un file `.env` nella root del progetto (es. `voicescribe-diarization-engine/`) e imposta:
  ```env
  HUGGINGFACE_TOKEN=hf_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
  ```
- **Docker**: passa il token come variabile d’ambiente al container (non metterlo nel Dockerfile):
  ```bash
  docker run -e HUGGINGFACE_TOKEN=hf_xxx ... voicescribe-diarization-engine
  ```
- **Build Docker con pre-download**: usa il secret BuildKit (vedi README):
  ```bash
  docker build --secret id=hf_token,env=HUGGINGFACE_TOKEN -t ...
  ```

## 5. Verifica

- Avvia il servizio e controlla `GET /models/status`: `model_loaded` e `hf_token_valid` devono essere `true` quando il modello è caricato.
- Se il token è mancante o non valido, il servizio parte in modalità degradata e `POST /diarize` risponde con **503** e un messaggio che rimanda a questa guida.

## Sicurezza

- Non loggare mai il token e non esporlo in API (es. `/models/status` restituisce solo un booleano `hf_token_valid`).
- In produzione usa segreti (environment, secret manager) e non file committati.
