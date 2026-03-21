# GPU Requirements

## Stack consigliato

- NVIDIA Driver: compatibile con CUDA 12.4+
- CUDA Runtime: 12.4
- Python: 3.11

## VRAM minima consigliata

- tiny/base: >= 2 GB
- small: >= 4 GB
- medium: >= 8 GB
- large-v3: >= 16 GB consigliati

## Verifica compatibilit?

```bash
nvidia-smi
python -c "import torch; print(torch.cuda.is_available(), torch.version.cuda)"
```
