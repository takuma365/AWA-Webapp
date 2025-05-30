# バックエンド起動手順

このドキュメントでは、バックエンドの起動方法と基本的な操作手順について説明します。

## 前提条件

- Dockerがインストールされていること
- Docker Composeがインストールされていること

## 起動手順

1. Dockerコンテナを起動します：
```bash
docker-compose up -d
```

2. バックエンドコンテナ内に入ります：
```bash
docker-compose exec backend bash
```

3. コンテナ内で`curl`をインストールします：
```bash
apt-get update && apt-get install -y curl
```

4. 別のターミナルでDjangoサーバーを起動します：
```bash
docker-compose exec backend bash -c "cd /app/app && python manage.py runserver 0.0.0.0:8001"
```

## Wordファイル変換テスト

コンテナ内で以下のコマンドを実行して、Wordファイルの変換をテストできます：

```bash
# 1. まず変換リクエストを送信し、変換IDを取得
curl -X POST http://localhost:8001/api/convert/ \
  -H "Content-Type: multipart/form-data" \
  -F "file=@/app/test_data/test.docx" \
  -F "setting_id=2"

# 2. レスポンスから変換IDを確認し、HTMLをダウンロード（IDは上記レスポンスの"id"フィールドの値に置き換えてください）
curl -X GET "http://localhost:8001/api/download/?id=5" -o output.html
```

注意：
- これらのコマンドは、コンテナ内で実行する必要があります。
- 1つ目のコマンドのレスポンスに含まれる`id`フィールドの値を使用して、2つ目のコマンドを実行してください。
- 例：レスポンスの`id`が5の場合は`curl -X GET "http://localhost:8001/api/download/?id=5" -o output.html`
- 変換結果のHTMLは`output.html`として保存されます。ファイル名は任意に変更可能です。
- `setting_id`は、データベースに登録されている変換設定のIDを指定してください。

## トラブルシューティング

- サーバーが起動しない場合は、Dockerコンテナが正常に起動しているか確認してください。
- ファイル変換に失敗する場合は、指定したファイルパスが正しいか、また`setting_id`が存在するか確認してください。

## 開発環境の停止

開発を終了する場合は、以下のコマンドでコンテナを停止できます：

```bash
docker-compose down
``` 