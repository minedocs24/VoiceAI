# Setup Sviluppo (Ubuntu 22.04)

## 1) Prerequisiti
```bash
sudo apt update
sudo apt install -y ca-certificates curl gnupg lsb-release ffmpeg make jq
```

Installare Docker Engine + plugin compose (documentazione ufficiale Docker).

Per host GPU (servizi futuri SVC-06/SVC-07):
- Driver NVIDIA compatibili
- NVIDIA Container Toolkit
- Verifica: `nvidia-smi`

## 2) Clonazione repository
```bash
git clone <repo-url> voicescribe-infra
cd voicescribe-infra
```

## 3) Variabili ambiente
```bash
cp .env.example .env
# Modifica .env con valori locali
```

## 4) Certificati dev
```bash
bash certs/generate-dev-certs.sh 365 localhost
```

## 5) Permessi script
```bash
make chmod-scripts
```

## 6) Setup ramdisk
```bash
make ramdisk-setup
```

## 7) Avvio infrastruttura
```bash
make up
make status
```

## 8) Verifica funzionamento
```bash
make health
curl -k https://localhost/health
```

## 9) Accesso dashboard
- Grafana: `http://localhost:3000`
- Prometheus: `http://localhost:9090`

Credenziali Grafana da `.env` (`GRAFANA_ADMIN_USER`, `GRAFANA_ADMIN_PASSWORD`).
