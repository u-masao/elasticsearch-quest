#!/bin/bash
# サーバー初期化スクリプト
#   - コンテナの初期化(volume を削除します)
#   - 証明書ファイルの取得
#   - 管理者パスワードの取得

CERTS_DIR=certs
CONFIG_FILE=.env
USERNAME=elastic
RETRY_TIMES=20

# 証明書ファイルをコピー
copy_certs() {
    mkdir -p $CERTS_DIR
    for i in $(seq 1 $RETRY_TIMES)
    do
        echo 証明書ファイルをコンテナ内部からホスト側へコピーします。
        echo コンテナが起動するまでリトライします: $i/$RETRY_TIMES 回目
        docker compose cp \
            elasticsearch:/usr/share/elasticsearch/config/certs/http_ca.crt \
            $CERTS_DIR/http_ca.crt
        if [ $? -eq 0 ]; then
            return 0
        fi
        sleep 5
    done
}

# ファイルの設定をアップデート
update_credentials (){
    KEY=$1
    VALUE=$2
    grep "^$KEY=" $CONFIG_FILE > /dev/null
    if [ $? -eq 0 ] ; then
        echo $CONFIG_FILE の $KEY を修正
        sed -i "s/^$KEY=.*/$KEY=$VALUE/" $CONFIG_FILE
    else
        echo $CONFIG_FILE に $KEY を追加
        echo $KEY=$VALUE >> $CONFIG_FILE
    fi
}

# パスワードをリセット
reset_admin_password() {
    for i in $(seq 1 $RETRY_TIMES)
    do
        echo 管理者アカウントをリセットします。
        echo コンテナが起動するまでリトライします: $i/$RETRY_TIMES 回目
        PASSWORD=$(docker compose exec -it elasticsearch \
            /usr/share/elasticsearch/bin/elasticsearch-reset-password \
            -b -s -u $USERNAME)
        if [ $? -eq 0 ]; then
            update_credentials ELASTICSEARCH_USERNAME $USERNAME
            update_credentials ELASTICSEARCH_PASSWORD $PASSWORD
            return 0
        fi
        sleep 5
    done
}

# docker コンテナとボリュームを削除
docker compose down --volumes

# docker コンテナを作成
docker compose up -d

# 証明書をコピー
copy_certs
if [ $? -ne 0 ] ; then
    echo 証明書ファイルのコピーに失敗しました。
    exit 1
fi

# 管理者パスワードをリセット
reset_admin_password
if [ $? -ne 0 ] ; then
    echo 管理者アカウントのリセットに失敗しました。
    exit 1
fi
