PORT="${PORT:-8080}"
uvicorn world_seek.main:app --port $PORT --host 0.0.0.0 --forwarded-allow-ips '*' --reload