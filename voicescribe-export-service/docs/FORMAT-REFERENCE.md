# Riferimento formati di output

## TXT (transcript.txt)

Testo plain con le seguenti regole:

- **Con diarizzazione**: ogni cambio di speaker è preceduto da una riga dedicata con il nome dello speaker, es. `[SPEAKER_00]`
- **Senza diarizzazione**: i segmenti sono separati da righe vuote
- **Timestamp**: opzionali, attivabili con `include_timestamps_txt: true`; formato `HH:MM:SS.mmm` prima del testo
- **Normalizzazione**: spazi multipli rimossi, prima lettera di ogni segmento capitalizzata

### Esempio con speaker

```
[SPEAKER_00]
Buongiorno a tutti, benvenuti alla riunione.

[SPEAKER_01]
Grazie per averci invitato.
```

### Esempio senza speaker

```
Buongiorno a tutti, benvenuti alla riunione.

Grazie per averci invitato.
```

---

## SRT (transcript.srt)

Formato SRT standard compatibile con VLC, YouTube e player principali.

- **Timestamp**: `HH:MM:SS,mmm --> HH:MM:SS,mmm`
- **Numerazione**: progressiva da 1
- **Splitting**: segmenti > 80 caratteri o > 3 secondi vengono divisi in sottotitoli più brevi
- **Speaker**: se presente diarizzazione, il nome dello speaker è prefisso al testo (es. `SPEAKER_00: Buongiorno`)

### Esempio

```
1
00:00:00,000 --> 00:00:02,500
SPEAKER_00: Buongiorno a tutti.

2
00:00:02,500 --> 00:00:05,000
SPEAKER_01: Grazie per essere qui.
```

---

## JSON (transcript.json)

Serializzazione del TranscriptResult o DiarizationResult arricchita con metadata:

- `job_id`, `tenant_id`, `tier`
- `processed_at` (ISO 8601)
- `rtf`, `inference_ms`
- `segments` con `start`, `end`, `text`, `speaker` (se diarizzazione)
- `speakers` (se diarizzazione)

Pretty-print con indentazione 2 spazi.

### Esempio (struttura)

```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "tenant_id": "tenant1",
  "tier": "PRO",
  "processed_at": "2025-03-14T12:00:00Z",
  "language": "it",
  "duration": 120.5,
  "rtf": 0.05,
  "inference_ms": 6000,
  "segments": [
    {
      "start": 0.0,
      "end": 2.5,
      "text": "Buongiorno a tutti.",
      "speaker": "SPEAKER_00"
    }
  ],
  "speakers": [
    {"speaker": "SPEAKER_00", "utterance_count": 5},
    {"speaker": "SPEAKER_01", "utterance_count": 3}
  ]
}
```

---

## DOCX (transcript.docx)

Documento Word professionale generato con python-docx.

### Struttura

1. **Intestazione**: titolo, sottotitolo (nome progetto), metadata (data, durata, modello)
2. **Indice**: se il documento ha più di ~10 pagine (stimato da parole), viene inserito un placeholder TOC che Word aggiorna all'apertura
3. **Contenuto**:
   - Con diarizzazione: sezione per ogni speaker con colore distintivo (blu, arancione, verde, ecc.)
   - Timestamp nel margine destro per ogni paragrafo (formato `HH:MM:SS.xx`)
4. **Footer**: data di export, numero di pagina

### Colori speaker (default)

- SPEAKER_00: Blu (#2E75B6)
- SPEAKER_01: Arancione (#C55A11)
- SPEAKER_02: Verde (#70AD47)
- SPEAKER_03: Azzurro (#5B9BD5)
- SPEAKER_04: Giallo (#FFC000)
- SPEAKER_05: Viola (#7030A0)

Configurabili in `config/export.yml` → `docx.typography.speaker_colors`.
