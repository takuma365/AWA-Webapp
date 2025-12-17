#!/bin/bash

# AWA-Webapp 図表PNG生成スクリプト
# Draw.ioファイルからPNG画像を自動生成します

set -e

echo "=========================================="
echo "AWA-Webapp 図表PNG生成"
echo "=========================================="
echo ""

# プロジェクトルートディレクトリに移動
cd "$(dirname "$0")"

# diagramsディレクトリの確認
if [ ! -d "diagrams" ]; then
    echo " エラー: diagramsディレクトリが見つかりません"
    exit 1
fi

# Draw.ioファイルの確認
if [ ! -f "diagrams/architecture.drawio" ]; then
    echo " エラー: diagrams/architecture.drawio が見つかりません"
    exit 1
fi

if [ ! -f "diagrams/er_diagram.drawio" ]; then
    echo " エラー: diagrams/er_diagram.drawio が見つかりません"
    exit 1
fi

echo " Draw.ioファイルを確認しました"
echo ""

# Dockerを使用してPNG生成
echo " PNG画像を生成中..."
echo ""

# architecture.png 生成
echo "1/2: architecture.png を生成中..."
docker run --rm \
    -v "$(pwd)/diagrams:/data" \
    rlespinasse/drawio-export:latest \
    --format png \
    --quality 100 \
    --transparent \
    --border 10 \
    --output /data \
    /data/architecture.drawio

if [ -f "diagrams/architecture.png" ]; then
    echo "    architecture.png を生成しました"
    ls -lh diagrams/architecture.png | awk '{print "   ファイルサイズ:", $5}'
else
    echo "    architecture.png の生成に失敗しました"
fi
echo ""

# er_diagram.png 生成
echo "2/2: er_diagram.png を生成中..."
docker run --rm \
    -v "$(pwd)/diagrams:/data" \
    rlespinasse/drawio-export:latest \
    --format png \
    --quality 100 \
    --transparent \
    --border 10 \
    --output /data \
    /data/er_diagram.drawio

if [ -f "diagrams/er_diagram.png" ]; then
    echo "    er_diagram.png を生成しました"
    ls -lh diagrams/er_diagram.png | awk '{print "   ファイルサイズ:", $5}'
else
    echo "    er_diagram.png の生成に失敗しました"
fi
echo ""

echo "=========================================="
echo " 完了！"
echo "=========================================="
echo ""
echo "生成されたファイル:"
echo "  - diagrams/architecture.png"
echo "  - diagrams/er_diagram.png"
echo ""
echo "確認方法:"
echo "  ls -lh diagrams/*.png"
echo ""

