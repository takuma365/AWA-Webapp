# 古いHTML自動削除機能のセットアップ

生成から指定日数が経過したHTMLデータを自動的に削除する機能です。

## 概要

- **対象**: `ConversionOutput`テーブルの古いレコード
- **削除内容**: 
  - DBレコード
  - 保存されたHTMLファイル
- **デフォルト保持期間**: 7日

---

## 使い方

### 1. 手動実行（テスト）

```bash
# プロジェクトルートで実行
cd /home/ubuntu/AWA-Webapp/backend

# DRY RUNで削除対象を確認（実際には削除しない）
python app/manage.py delete_old_conversions --days=7 --dry-run

# 実際に削除を実行
python app/manage.py delete_old_conversions --days=7
```

### 2. パラメータ

| パラメータ | 説明 | デフォルト |
|----------|------|----------|
| `--days` | 削除対象とする日数 | 7 |
| `--dry-run` | 削除せずに対象のみ表示 | なし |

### 3. 実行例

```bash
# 30日以上前のデータを削除
python app/manage.py delete_old_conversions --days=30

# 3日以上前のデータを削除（短期保存の場合）
python app/manage.py delete_old_conversions --days=3

# 削除対象を確認（実際には削除しない）
python app/manage.py delete_old_conversions --days=7 --dry-run
```

---

## 定期実行（cron）のセットアップ

### ステップ1: cronエディタを開く

```bash
crontab -e
```

### ステップ2: cron設定を追加

以下の行を追加します：

```bash
# 毎日午前3時に7日以上前のHTMLデータを削除
0 3 * * * cd /home/ubuntu/AWA-Webapp/backend && /usr/bin/python3 app/manage.py delete_old_conversions --days=7 >> /var/log/awa-webapp-cleanup.log 2>&1
```

**説明**:
- `0 3 * * *`: 毎日午前3時に実行
- `cd /home/ubuntu/AWA-Webapp/backend`: プロジェクトディレクトリに移動
- `/usr/bin/python3 app/manage.py ...`: コマンド実行
- `>> /var/log/awa-webapp-cleanup.log 2>&1`: ログファイルに出力

### ステップ3: cron設定を確認

```bash
# 設定を確認
crontab -l

# cronサービスが起動しているか確認
sudo systemctl status cron
```

---

## 実行結果の例

### DRY RUN（削除なし）

```bash
$ python app/manage.py delete_old_conversions --days=7 --dry-run

7日以上前の変換結果: 15件

  - ID: 123, ファイル: sample.docx, 作成日: 2025-12-01 14:30, 経過日数: 10日
  - ID: 124, ファイル: test.docx, 作成日: 2025-12-02 09:15, 経過日数: 9日
  ... 他 13件

[DRY RUN] 実際には削除されませんでした。
--dry-run を外して実行すると削除されます。
```

### 実際の削除

```bash
$ python app/manage.py delete_old_conversions --days=7

7日以上前の変換結果: 15件

  - ID: 123, ファイル: sample.docx, 作成日: 2025-12-01 14:30, 経過日数: 10日
  - ID: 124, ファイル: test.docx, 作成日: 2025-12-02 09:15, 経過日数: 9日
  ... 他 13件

 完了:
  - DBレコード削除: 15件
  - HTMLファイル削除: 15件
```

---

## トラブルシューティング

### エラー: `No module named 'api.models'`

**原因**: Djangoの設定が読み込まれていない

**解決方法**:
```bash
# manage.pyがあるディレクトリで実行
cd /home/ubuntu/AWA-Webapp/backend
python app/manage.py delete_old_conversions --days=7
```

### cronが実行されない

**確認手順**:

```bash
# 1. cronサービスの状態確認
sudo systemctl status cron

# 2. cronログを確認
grep CRON /var/log/syslog

# 3. 手動実行してエラーを確認
cd /home/ubuntu/AWA-Webapp/backend && python app/manage.py delete_old_conversions --days=7
```

### ログファイルの確認

```bash
# クリーンアップログを確認
tail -f /var/log/awa-webapp-cleanup.log

# ログディレクトリが存在しない場合は作成
sudo touch /var/log/awa-webapp-cleanup.log
sudo chmod 666 /var/log/awa-webapp-cleanup.log
```

---

## カスタマイズ例

### 保持期間を変更

```bash
# crontabを編集
crontab -e

# 30日保持に変更
0 3 * * * cd /home/ubuntu/AWA-Webapp/backend && /usr/bin/python3 app/manage.py delete_old_conversions --days=30 >> /var/log/awa-webapp-cleanup.log 2>&1
```

### 実行頻度を変更

```bash
# 週1回（日曜日午前3時）に変更
0 3 * * 0 cd /home/ubuntu/AWA-Webapp/backend && /usr/bin/python3 app/manage.py delete_old_conversions --days=7 >> /var/log/awa-webapp-cleanup.log 2>&1

# 毎時実行（1日保持の場合）
0 * * * * cd /home/ubuntu/AWA-Webapp/backend && /usr/bin/python3 app/manage.py delete_old_conversions --days=1 >> /var/log/awa-webapp-cleanup.log 2>&1
```

---

## 注意事項

1. **バックアップ**: 削除されたデータは復元できません。重要なデータは事前にバックアップしてください。

2. **テスト実行**: 本番環境で初めて実行する前に、必ず `--dry-run` でテストしてください。

3. **ディスク容量**: 定期実行を設定しないと、ディスク容量が不足する可能性があります。

4. **タイムゾーン**: `created_at`はUTC基準です。タイムゾーン設定を確認してください。

---

## 推奨設定

| 用途 | 保持期間 | cron設定 |
|------|---------|---------|
| 本番環境 | 30日 | 毎日午前3時 |
| 開発環境 | 7日 | 毎日午前3時 |
| テスト環境 | 3日 | 毎日午前3時 |

---

## 関連ファイル

- **コマンド本体**: `backend/api/management/commands/delete_old_conversions.py`
- **モデル**: `backend/api/models.py` (ConversionOutput)
- **このドキュメント**: `AUTO_DELETE_SETUP.md`

