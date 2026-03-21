# ADR-001: scelta compute type int8_float16

## Stato
Accepted

## Contesto

Per workload enterprise servono throughput elevato e uso VRAM sostenibile.

## Decisione

Usare `int8_float16` come default.

## Trade-off

- `int8_float16`: migliore compromesso memoria/velocit?, minima perdita qualit?
- `float16`: qualit? alta ma VRAM pi? elevata
- `float32`: qualit? massima teorica ma costo VRAM/latenza non adatto in produzione

## Benchmark sintetico (indicativo)

- large-v3 + int8_float16: RTF 0.04-0.08, VRAM ~10-14GB
- large-v3 + float16: RTF 0.05-0.10, VRAM ~14-18GB
- large-v3 + float32: RTF >0.10, VRAM >20GB
