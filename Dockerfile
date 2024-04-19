FROM pypy:3.10-bookworm

WORKDIR /usr/src/app

RUN apt-get update && apt-get -y install gdal-bin --no-install-recommends && apt-get clean && rm -rf /var/lib/apt/lists/*
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD [ "pypy3", "./osm_diff.py" ]
