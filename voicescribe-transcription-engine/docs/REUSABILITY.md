# Reusability Use Cases

## Pipeline subtitling

- Input: video/audio
- Output: transcript JSON o SRT
- Config: `WHISPER_MODEL=large-v3`, callback opzionale

## IT helpdesk voice tickets

- Input: ticket vocali
- Output: testo indicizzabile per ricerca
- Config: `POST /transcribe/async` + polling task status

## CRM note vocali

- Input: memo venditori
- Output: testo per CRM activity feed
- Config: token interno e device `cuda`

## Legal recording

- Input: registrazioni udienze
- Output: transcript con word timestamps per audit
- Config: word timestamps attivi (default)
