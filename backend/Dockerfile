FROM ubuntu:24.04

WORKDIR /app

RUN apt-get update && apt-get install -y libcurl3-gnutls libstdc++6 build-essential python3 python3-pip python3-venv

RUN python3 -m venv /opt/venv

COPY backend/requirements.txt .
RUN /opt/venv/bin/pip install --no-cache-dir -r requirements.txt

COPY backend/ .

EXPOSE 5000

CMD ["/opt/venv/bin/python", "ShashGuruBackend.py"]
