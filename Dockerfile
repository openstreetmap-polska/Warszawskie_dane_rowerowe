FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && \
    apt-get -y install \
        make \
        git \
    --no-install-recommends && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*
RUN pip install uv
COPY requirements.txt ./
RUN uv venv venv && . venv/bin/activate && uv pip sync requirements.txt

COPY . .

CMD [ "make", "run" ]
