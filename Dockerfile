# app/Dockerfile

FROM execengine-compilers AS compilers

FROM python:3.11 AS api

RUN apt-get update && apt-get install -y build-essential libpq-dev netcat-openbsd libxml2 libffi8 libssl3 libstdc++6 zlib1g libbz2-1.0 libncursesw6 systemd && rm -rf /var/lib/apt/lists/*

WORKDIR .

COPY requirements.txt .

RUN pip install --upgrade pip
RUN pip install -r requirements.txt

COPY . .

COPY --from=compilers /usr/local/bin/isolate /usr/local/bin/isolate
COPY --from=compilers /usr/local/etc/isolate /usr/local/etc/isolate
COPY --from=compilers /tmp /tmp

ENV PYTHONUNBUFFERED=1

EXPOSE 8000

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]

#CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload", "--reload-dir", "."]
