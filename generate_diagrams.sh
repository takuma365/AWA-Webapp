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
DRAWIO_FILES=(
    "architecture.drawio"
    "er_diagram.drawio"
    "xml_to_html_converter_flow.drawio"
    "word_to_html_accurate_flow.drawio"
)

for file in "${DRAWIO_FILES[@]}"; do
    if [ ! -f "diagrams/$file" ]; then
        echo " 警告: diagrams/$file が見つかりません（スキップします）"
    fi
done

echo " Draw.ioファイルを確認しました"
echo ""

# 生成するファイル数をカウント
TOTAL_FILES=0
for file in "${DRAWIO_FILES[@]}"; do
    if [ -f "diagrams/$file" ]; then
        TOTAL_FILES=$((TOTAL_FILES + 1))
    fi
done

# Dockerを使用してPNG生成
echo " PNG画像を生成中... (全${TOTAL_FILES}ファイル)"
echo ""

CURRENT=0

# architecture.png 生成
if [ -f "diagrams/architecture.drawio" ]; then
    CURRENT=$((CURRENT + 1))
    echo "$CURRENT/$TOTAL_FILES: architecture.png を生成中..."
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
fi

# er_diagram.png 生成
if [ -f "diagrams/er_diagram.drawio" ]; then
    CURRENT=$((CURRENT + 1))
    echo "$CURRENT/$TOTAL_FILES: er_diagram.png を生成中..."
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
fi

# xml_to_html_converter_flow.png 生成
if [ -f "diagrams/xml_to_html_converter_flow.drawio" ]; then
    CURRENT=$((CURRENT + 1))
    echo "$CURRENT/$TOTAL_FILES: xml_to_html_converter_flow.png を生成中..."
    docker run --rm \
        -v "$(pwd)/diagrams:/data" \
        rlespinasse/drawio-export:latest \
        --format png \
        --quality 100 \
        --transparent \
        --border 10 \
        --output /data \
        /data/xml_to_html_converter_flow.drawio
    
    if [ -f "diagrams/xml_to_html_converter_flow.png" ]; then
        echo "    xml_to_html_converter_flow.png を生成しました"
        ls -lh diagrams/xml_to_html_converter_flow.png | awk '{print "   ファイルサイズ:", $5}'
    else
        echo "    xml_to_html_converter_flow.png の生成に失敗しました"
    fi
    echo ""
fi

# word_to_html_accurate_flow.png 生成
if [ -f "diagrams/word_to_html_accurate_flow.drawio" ]; then
    CURRENT=$((CURRENT + 1))
    echo "$CURRENT/$TOTAL_FILES: word_to_html_accurate_flow.png を生成中..."
    docker run --rm \
        -v "$(pwd)/diagrams:/data" \
        rlespinasse/drawio-export:latest \
        --format png \
        --quality 100 \
        --transparent \
        --border 10 \
        --output /data \
        /data/word_to_html_accurate_flow.drawio
    
    if [ -f "diagrams/word_to_html_accurate_flow.png" ]; then
        echo "    word_to_html_accurate_flow.png を生成しました"
        ls -lh diagrams/word_to_html_accurate_flow.png | awk '{print "   ファイルサイズ:", $5}'
    else
        echo "    word_to_html_accurate_flow.png の生成に失敗しました"
    fi
    echo ""
fi

echo "=========================================="
echo " 完了！"
echo "=========================================="
echo ""
echo "生成されたファイル:"
ls -1 diagrams/*.png 2>/dev/null | sed 's/^/  - /' || echo "  (PNG画像が見つかりませんでした)"
echo ""
echo "確認方法:"
echo "  ls -lh diagrams/*.png"
echo ""

