FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

RUN mkdir -p /data
RUN apt-get update && apt-get install -y --no-install-recommends nginx fail2ban iptables && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY tests ./tests
COPY --from=security / /opt/security/
COPY --from=security jail.local /etc/fail2ban/jail.local
COPY --from=security http-flood.conf /etc/fail2ban/filter.d/http-flood.conf
COPY nginx.conf /etc/nginx/nginx.conf
COPY security-processes.json /etc/security-processes.json
RUN mkdir -p /var/log/security

EXPOSE 8000

ENV HEALTH_URL=http://127.0.0.1:8000/health
ENTRYPOINT ["python3", "/opt/security/supervise.py"]
HEALTHCHECK CMD python3 /opt/security/health.py
