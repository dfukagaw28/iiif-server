# iiif-server

Simple IIIF Image server

## How to use

Clone the repository:

```
$ sudo mkdir -p /home/docker/compose

$ sudo cd /home/docker/compose

$ sudo git clone https://github.com/dfukagaw28/iiif-server.git

$ cd iiif-server
```

Setup the config file:

```
$ sudo cp docker-compose.sample.yml docker-compose.yml

$ sudo vi docker-compose.yml
```

Create and start containers (in detached mode):

```
$ sudo docker-compose pull

$ sudo docker-compose build

$ sudo docker-compose up -d
```

Access via HTTP:

```
$ curl -si http://iiif.tiramis2.doshisha.ac.jp/hyaku2017A/manifest.json

$ curl -si http://iiif.tiramis2.doshisha.ac.jp/v3/image/hyaku2017/002.tif/info.json

$ curl -Oi https://iiif.tiramis2.doshisha.ac.jp/v3/image/hyaku2017/002.tif/full/max/0/default.jpg
$ du -h default.jpg
492K    default.jpg
```

## For developers

### Update Pipfile

```
$ podman run --rm -it -v $(pwd):/code -w /code python:3.11-alpine /bin/sh
$ pipenv install tornado
```
