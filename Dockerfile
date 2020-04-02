FROM python:2.7-alpine

RUN apk add pkgconfig\
    alpine-sdk \
    python-dev \
    ffmpeg-dev \
    libxslt-dev \
    libxml2-dev \
    autoconf \
    automake \
    freetype-dev \
    g++ \
    gcc \
    jpeg-dev \
    lcms2-dev \
    libffi-dev \
    libpng-dev \
    libwebp-dev \
    linux-headers \
    make \
    openjpeg-dev \
    openssl-dev \
    python3-dev \
    tiff-dev \
    zlib-dev

RUN pip install av


WORKDIR /usr/src/webservice-v3

COPY requirements.txt .

RUN pip install -r requirements.txt

COPY . .
