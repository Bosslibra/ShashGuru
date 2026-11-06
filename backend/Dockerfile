FROM ubuntu:24.04

WORKDIR /app

RUN apt-get update && apt-get install -y libcurl3-gnutls libstdc++6 build-essential python3 python3-pip python3-venv \
    && rm -rf /var/lib/apt/lists/*

RUN python3 -m venv /opt/venv

COPY backend/requirements.txt .
RUN /opt/venv/bin/pip install --no-cache-dir -r requirements.txt

COPY backend/ .
RUN chmod +x /app/docker-entrypoint.sh \
    && useradd --system --home /app --shell /usr/sbin/nologin shashguru \
    && chown -R shashguru /app

# The chess engines may write learning files next to themselves, hence a writable /app.
USER shashguru
EXPOSE 5000

ENTRYPOINT ["sh", "/app/docker-entrypoint.sh"]
