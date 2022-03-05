FROM ubuntu:18.04
# (if you use oracle Ampere A1) FROM anasty17/mltb-oracle:latest

WORKDIR /usr/src/app
RUN chmod 777 /usr/src/app
RUN apt-get -qq update
RUN apt-get -qq install -y git python3 python3-pip \
    locales python3-lxml aria2 \
    curl pv jq nginx npm
COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt && \
    apt-get -qq purge git
COPY . .
RUN chmod +x start.sh
RUN chmod +x gclone
CMD ["bash","start.sh"]
