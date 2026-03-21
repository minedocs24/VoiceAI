# Certificati sviluppo

## Self-signed locale
```bash
bash certs/generate-dev-certs.sh 365 localhost
```

## Produzione con Let's Encrypt
Esempio con `certbot` su host Linux:

```bash
sudo apt install -y certbot
sudo certbot certonly --standalone -d your-domain.example
```

Poi impostare in `.env`:
- `NGINX_TLS_CERT=/etc/letsencrypt/live/your-domain.example/fullchain.pem`
- `NGINX_TLS_KEY=/etc/letsencrypt/live/your-domain.example/privkey.pem`

Configurare rinnovo automatico:

```bash
sudo systemctl enable --now certbot.timer
```
