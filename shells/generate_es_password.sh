#!/bin/bash

USERNAME=elastic
PASSWORD=`docker compose exec -it elasticsearch /usr/share/elasticsearch/bin/elasticsearch-reset-password -b -s -u $USERNAME`

KIBANA_TOKEN=`docker compose exec -it elasticsearch /usr/share/elasticsearch/bin/elasticsearch-create-enrollment-token -f -s kibana`

DOTENV=.env
echo '### スクリプトで追加 ###' >> $DOTENV
echo ELASTICSEARCH_USERNAME=$USERNAME >> $DOTENV
echo ELASTICSEARCH_PASSWORD=$PASSWORD >> $DOTENV
echo KIBANA_TOKEN=$KIBANA_TOKEN>> $DOTENV

echo '# .env ファイルの末尾に以下を追加しました'
echo ELASTICSEARCH_USERNAME=$USERNAME
echo ELASTICSEARCH_PASSWORD=$PASSWORD
echo KIBANA_TOKEN=$KIBANA_TOKEN
