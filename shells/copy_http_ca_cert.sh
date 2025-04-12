#!/bin/bash

mkdir -p certs
docker compose cp elasticsearch:/usr/share/elasticsearch/config/certs/http_ca.crt certs/
