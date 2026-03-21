# Algoritmo di merge trascrizione + diarizzazione

Il servizio riceve da un lato i **segmenti di trascrizione** (es. Whisper: start, end, text) e dall’altro la **timeline speaker** prodotta da Pyannote (segmenti temporali con etichetta SPEAKER_00, SPEAKER_01, …). L’obiettivo è assegnare a ogni segmento di trascrizione **un’unica** etichetta speaker.

## Regola: massima sovrapposizione temporale

Per ogni segmento Whisper (intervallo `[s_start, s_end]`):

1. Si considerano tutti i segmenti speaker della timeline Pyannote.
2. Per ogni segmento speaker `[p_start, p_end]` si calcola la **lunghezza della sovrapposizione** con `[s_start, s_end]`:
   - `overlap_start = max(s_start, p_start)`
   - `overlap_end = min(s_end, p_end)`
   - `overlap_length = max(0, overlap_end - overlap_start)`
3. Si assegna al segmento Whisper l’etichetta dello **speaker con overlap_length massima**.
4. Se nessuno speaker ha sovrapposizione > 0, si assegna **`speaker: null`** (es. silenzio nella diarizzazione).

## Casi edge

### Segmento a cavallo tra due speaker (es. 50%–50%)

Se un segmento Whisper si sovrappone in egual misura a due segmenti speaker (stessa overlap_length), l’implementazione assegna lo speaker del **primo** segmento (in ordine temporale) che realizza quel massimo. Il risultato è quindi determinístico ma arbitrario sul confine; per segmenti brevi al cambio speaker è accettabile.

### Nessuna sovrapposizione

Segmenti Whisper che ricadono in intervalli senza speaker (silenzio, rumore) ricevono `speaker: null`. Il client può gestirli come “speaker non identificato” o filtrarli.

### Lista speaker nel risultato

La lista **`speakers`** nel risultato è deduplicata e ordinata per **prima apparizione** nel documento. Per ogni speaker si riporta il **conteggio degli interventi** (numero di segmenti a cui è stato assegnato).

## Complessità

- Per ogni segmento Whisper si itera su tutti i segmenti speaker (o si può ottimizzare con sweep temporale).
- Complessità naive: O(N × M) con N = segmenti Whisper, M = segmenti speaker. Per trascrizioni lunghe (centinaia di segmenti) resta gestibile; per scale maggiori si può ordinare per tempo e ridurre le confronti con un sweep line.

## Implementazione

L’algoritmo è implementato come **funzione pura** in `app/services/merge.py` (`merge_transcript_with_diarization`), senza I/O né dipendenze da GPU, così da essere testabile in isolamento con test unitari (casi sintetici con segmenti e timeline note).
