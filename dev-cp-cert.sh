#!/bin/bash
export $(grep -v '^#' .env | xargs)
docker cp ${PROJECT_NAME}-elasticsearch:/usr/share/elasticsearch/config/certs/ca/ca.crt ./ca.crt