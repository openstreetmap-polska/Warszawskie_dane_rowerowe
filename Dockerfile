FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && \
    apt-get -y install \
        make \
        git \
    --no-install-recommends && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

ARG UID=1000
ARG GID=1000

RUN mkdir -p /home/appuser && \
    groupadd -f -g $GID appgroup && \
    useradd -r -u $UID -g appgroup appuser --home /home/appuser && \
    chown -R appuser:appgroup /home/appuser && \
    chmod 0755 /home/appuser

USER appuser
RUN pip install uv
COPY requirements.txt ./
RUN uv venv venv && . venv/bin/activate && uv pip sync requirements.txt

COPY . .

CMD [ "make", "run" ]
