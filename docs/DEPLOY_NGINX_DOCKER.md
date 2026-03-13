# Docker Nginx Deployment

This setup serves `frontend/` through Nginx and proxies backend routes to the Flask app running on the host at `127.0.0.1:8000`.

## Files

- `docker-compose.nginx.yml`
- `deploy/nginx/default.conf`

## Backend requirements

Run the Flask backend on the host:

```bash
cd /path/to/trace-demo
python backend/app.py
```

Or:

```bash
cd /path/to/trace-demo
bash scripts/run_backend.sh
```

The backend must listen on `0.0.0.0:8000`.

## Environment

Recommended backend `.env` values:

```env
PUBLIC_BASE_URL=http://YOUR_SERVER_IP
CORS_ALLOWED_ORIGINS=http://YOUR_SERVER_IP
```

If you access the site through a domain, use the domain instead:

```env
PUBLIC_BASE_URL=https://your-domain.com
CORS_ALLOWED_ORIGINS=https://your-domain.com
```

## Start Nginx

```bash
cd /path/to/trace-demo
docker compose -f docker-compose.nginx.yml up -d
```

## Stop Nginx

```bash
cd /path/to/trace-demo
docker compose -f docker-compose.nginx.yml down
```

## Logs

```bash
docker logs -f trace-demo-nginx
```
