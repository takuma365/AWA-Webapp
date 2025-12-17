# 図表ディレクトリ

このディレクトリには、AWA-Webappのシステム構成図とER図のDraw.ioファイルが格納されています。

## ファイル一覧

### 1. architecture.drawio
**システム構成図（アーキテクチャ図）**

VPN、Nginx、Frontend、Backend、PostgreSQLの構成を図示しています。

### 2. er_diagram.drawio
**ER図（データベース設計図）**

Site、ConversionSetting、ConversionRule、ConversionOutputのテーブル構造とリレーションを図示しています。

### 3. xml_to_html_converter_flow.drawio
**XML→HTML変換処理フロー**

`backend/api/services/xml_to_html_converter.py`の関数連携図です。

- **対象**: 開発者、保守担当者
- **内容**: 
  - メイン関数 `parse_xml_to_html()` の処理フロー
  - 初期化・設定グループ
  - コメント処理グループ
  - 表処理グループ
  - 見出し処理グループ
  - 青色/赤色テキスト処理グループ
  - リスト生成グループ
  - 後処理グループ
  - 各関数の呼び出し関係（実線=処理フロー、破線=関数呼び出し）
  
**用途**: 
- コード理解の補助（5233行の巨大ファイルを把握）
- バグ修正時の影響範囲の確認
- リファクタリング計画の策定

### 4. word_to_html_accurate_flow.drawio
**Word→HTML変換処理 実際のフロー**

実際のシステムで行われている2ステップ処理を正確に示した図です。

- **対象**: 開発者、運用担当者、新規参画者
- **内容**:
  - **ステップ1**: Wordファイルアップロード
    - `POST /api/convert/` → `converter.py`
    - XMLを抽出・保存（`xml_data/`）
    - シンプルHTMLも生成するが**使われない** ⚠️
  - **ステップ2**: カスタムHTML生成（実際に使用）
    - `POST /api/generate-html/` → `xml_to_html_converter.py`
    - 保存されたXMLを読み込み
    - ElementTreeで直接パース
    - カスタムルール適用 → HTML出力 ✅
  - 自動削除機能の推奨設定

**用途**:
- 実際の処理フローの正確な理解
- 2ステップ処理の把握
- どのHTMLが使われているか明確化
- 自動削除機能の理解

## 使い方

### 1. Draw.io Webで開く

1. [Draw.io](https://app.diagrams.net/) にアクセス
2. 「File」→「Open from」→「Device」
3. `architecture.drawio` または `er_diagram.drawio` を選択

### 2. VSCode/Cursorでグラフィカルに開く（推奨）

Draw.io Integration拡張機能をインストールすることで、VSCode/Cursor内で直接編集できます。

```bash
# 拡張機能のインストール
code --install-extension hediet.vscode-drawio
```

インストール後、`.drawio`ファイルをクリックするだけで図が表示されます。

### 3. VSCode/CursorでXML形式（テキスト）で開く

Draw.ioファイルは実際にはXMLベースのテキストファイルです。以下の方法でXMLとして閲覧・編集できます：

**方法A: 右クリックメニューから**
```
1. `.drawio`ファイルを右クリック
2. 「Open With...」を選択
3. 「Text Editor」を選択
```

**方法B: エディタ分割で両方表示**
```
1. `.drawio`ファイルをDraw.io形式で開く
2. `Ctrl+\`（またはCmd+\）でエディタを分割
3. 分割した側で右クリック → 「Reopen Editor With...」→ 「Text Editor」
```

**方法C: コマンドパレットから**
```
1. `.drawio`ファイルを選択
2. `Ctrl+Shift+P`（またはCmd+Shift+P）でコマンドパレットを開く
3. 「View: Reopen Editor With...」を検索
4. 「Text Editor」を選択
```

**XMLの構造例**:
```xml
<mxfile host="app.diagrams.net">
  <diagram id="architecture" name="システム構成図">
    <mxGraphModel dx="1422" dy="794" grid="1">
      <root>
        <mxCell id="0"/>
        <mxCell id="1" parent="0"/>
        
        <!-- VPN Layer -->
        <mxCell id="vpn" value="VPN (IP制限)" 
                style="rounded=1;whiteSpace=wrap;html=1"
                vertex="1" parent="1">
          <mxGeometry x="200" y="40" width="760" height="60"/>
        </mxCell>
        
        <!-- その他の要素 -->
      </root>
    </mxGraphModel>
  </diagram>
</mxfile>
```

**XML形式で開くメリット**:
- **Git差分確認**: どの要素が追加・変更・削除されたか正確に把握
- **一括編集**: 検索・置換で複数の要素を一度に変更
- **デバッグ**: 図が正しく表示されない場合の原因調査
- **手動調整**: 座標やスタイルを直接編集（上級者向け）

**注意点**:
- XML構造を壊すと図が開けなくなる可能性があります
- 編集後は必ずDraw.io形式で開いて正常に表示されるか確認してください
- Git管理する場合、XML形式なので差分が見やすくなります

### 画像としてエクスポート

#### 方法1: Draw.io Webでエクスポート

1. [https://app.diagrams.net/](https://app.diagrams.net/) で`.drawio`ファイルを開く
2. 「File」→「Export as」→「PNG」または「SVG」
3. 設定:
   - 解像度: 300 DPI（高品質）
   - Transparent Background: チェック（背景透過）
   - Border Width: 10px（余白）
4. `architecture.png` または `er_diagram.png` として保存

#### 方法2: VSCode Draw.io拡張機能

VSCodeで`.drawio`ファイルを開いた状態で：
1. 右クリック → "Export Diagram"
2. フォーマット: PNG
3. 保存先: `diagrams/` ディレクトリ

#### 方法3: コマンドライン（Docker）

```bash
# プロジェクトルートディレクトリで実行
cd /home/ubuntu/AWA-Webapp

# architecture.png を生成
docker run --rm -v $(pwd)/diagrams:/data rlespinasse/drawio-export:latest \
  --format png --quality 100 --transparent --output /data /data/architecture.drawio

# er_diagram.png を生成
docker run --rm -v $(pwd)/diagrams:/data rlespinasse/drawio-export:latest \
  --format png --quality 100 --transparent --output /data /data/er_diagram.drawio

# SVGで生成（ベクター形式、拡大しても綺麗）
docker run --rm -v $(pwd)/diagrams:/data rlespinasse/drawio-export:latest \
  --format svg --output /data /data/architecture.drawio
```

#### PNG画像が必要な場面

- GitHubやGitLabでドキュメントを閲覧する場合
- Markdownプレビューで図を即座に表示したい場合
- プレゼンテーション資料に使用する場合

**注意**: 
- PNG画像は約2-5MBのサイズになります
- `.drawio`ファイルがあれば、いつでもPNG画像を再生成できます
- Git管理する場合、PNG画像は`.gitignore`に追加することも検討してください

## 更新履歴

- 2025-12-17: 
  - 初版作成（システム構成図、ER図）
  - 関数連携図追加（`xml_to_html_converter_flow.drawio`）
  - 実際のフロー図追加（`word_to_html_accurate_flow.drawio`）
  - 自動削除機能の実装とドキュメント追加

---

**注意**: 
- 図を更新した場合は、`./generate_diagrams.sh`を実行してPNG画像も更新してください
- PNG画像は約2-5MBのサイズになります（大きな図の場合）
- `.drawio`ファイルさえあれば、いつでもPNG画像を再生成できます

