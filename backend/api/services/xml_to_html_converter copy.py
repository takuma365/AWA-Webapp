import xml.etree.ElementTree as ET
import re
import os
import colorsys
from collections import defaultdict

# サイト設定の定義
SITE_CONFIGS = {
    'webapp_custom': {
        'name': 'Webアプリカスタム設定',
        'heading_1': {
            'before': '',
            'tag': '',  # 空の初期値（自動解析で設定される）
            'after': '',
            'id_format': '',  # 空の初期値（自動解析で設定される）
        },
        'h4_template': '<h4 id="{id}">{content}</h4>',#見出し2
        'heading_2_format': 'heading_{main_number}-{sub_number}',
        'client_domain': '',  # 追加: 内部リンク判定用
        'client_domain_omit': False,  # 追加: ドメイン省略フラグ
    },
}

# 使用するサイト設定を選択
CURRENT_SITE = 'webapp_custom'  # Webアプリ連携用設定のみ使用

# 選択されたサイト設定を取得
def get_site_config():
    return SITE_CONFIGS[CURRENT_SITE]

def parse_html_tag_and_extract_id_pattern(tag_string):
    """
    HTMLタグを解析してid内の数字を変数化し、テンプレート化する
    
    Args:
        tag_string (str): HTMLタグ文字列（例：'<h2 id="rtoc-1" class="wp-block-heading">'）
    
    Returns:
        tuple: (template_tag, id_format)
               template_tag: {content}と{id}を含むテンプレート
               id_format: 数字部分を{number}に変換したフォーマット
    """
    # 数字を含むidパターンを探す正規表現
    id_pattern = re.compile(r'id\s*=\s*["\']([^"\']*?)(\d+)([^"\']*?)["\']')
    
    # idの数字部分を{number}に置換
    id_format = ""
    template_tag = tag_string
    
    match = id_pattern.search(tag_string)
    if match:
        # id全体、数字の前部分、数字、数字の後部分を取得
        full_id = match.group(0)  # id="section01"
        prefix = match.group(1)   # section
        number_str = match.group(2)   # 01
        suffix = match.group(3)   # （空文字列）
        
        # 数字部分から実際の数値を取得（先頭の0を除去）
        actual_number = int(number_str)
        
        # ゼロパディングの検出
        if len(number_str) > 1 and number_str.startswith('0'):
            # ゼロパディングがある場合（01, 02, 001など）
            padding_length = len(number_str)
            id_format = f"{prefix}{{number:0{padding_length}d}}{suffix}"
        else:
            # 通常の数字の場合（1, 23など）
            id_format = f"{prefix}{{number}}{suffix}"
        
        # テンプレート内のidを{id}に置換
        # id="section01" を id="{id}" に変換
        new_id_attr = full_id.replace(prefix + number_str + suffix, '{id}')
        template_tag = tag_string.replace(full_id, new_id_attr)
    
    # {content}を挿入する位置を決定
    if '</h' in template_tag:
        # 完全なタグ（開始〜終了）の場合
        if '>' in template_tag and '</' in template_tag:
            parts = template_tag.split('>', 1)
            if len(parts) == 2:
                start_part = parts[0] + '>'
                end_part = parts[1]
                if '</' in end_part:
                    content_and_end = end_part.split('</', 1)
                    template_tag = start_part + '{content}</' + content_and_end[1]
    else:
        # 開始タグのみの場合、{content}と終了タグを追加
        if template_tag.startswith('<'):
            # タグ名を抽出
            tag_name_match = re.match(r'<(\w+)', template_tag)
            if tag_name_match:
                tag_name = tag_name_match.group(1)
                template_tag = template_tag.rstrip('>') + '>{content}</' + tag_name + '>'
    
    return template_tag, id_format

def set_heading1_from_webapp(tag_string, before_string="", after_string="", id_format=None):
    """
    Webアプリから受け取ったパラメータで見出し1の設定を更新
    
    Args:
        tag_string (str): 見出しタグの文字列（例：'<h2 id="rtoc-1" class="wp-block-heading has-text-color" style="color:#0ca5b0">'）
        before_string (str): タグの前に置く文字列
        after_string (str): タグの後に置く文字列
        id_format (str): IDのフォーマット（None の場合は自動解析）
    """
    global CURRENT_SITE
    
    # HTMLタグを解析してテンプレートとIDフォーマットを取得
    template_tag, auto_id_format = parse_html_tag_and_extract_id_pattern(tag_string)
    
    # IDフォーマットの決定（手動指定 > 自動解析 > デフォルト）
    final_id_format = id_format if id_format is not None else auto_id_format
    if not final_id_format:
        final_id_format = 'heading_{number}'  # デフォルト
    
    # webapp_custom設定を更新
    SITE_CONFIGS['webapp_custom']['heading_1'] = {
        'before': before_string,
        'tag': template_tag,
        'after': after_string,
        'id_format': final_id_format,
    }
    
    # 現在のサイトをwebapp_customに設定
    CURRENT_SITE = 'webapp_custom'
    
    # HTML_TAGSも更新
    update_html_tags()
    
    # デバッグ情報を出力
    print(f"[DEBUG] 解析結果:")
    print(f"  元のタグ: {tag_string}")
    print(f"  テンプレート: {template_tag}")
    print(f"  IDフォーマット: {final_id_format}")
    print(f"  前文字列: '{before_string}'")
    print(f"  後文字列: '{after_string}'")

def update_html_tags():
    """サイト設定が変更された場合にHTML_TAGSを更新"""
    site_config = get_site_config()
    HTML_TAGS['h3_template'] = site_config['heading_1']['tag']

# HTMLタグとスタイルの定義
HTML_TAGS = {
    'h3_template': get_site_config()['heading_1']['tag'],#見出し1
    'h4_template': get_site_config()['h4_template'],#見出し2
    'marker_template': '<span class="marker">{content}</span>',#黄色マーカー
    'bold_template': '<strong>{content}</strong>',#太字
    'div_bordered_template': '<div style="background:#ffffff;border:1px solid #cccccc;padding:5px 10px;">{content}</div>',#罫線
    'div_list_template': '<div style="background:#ffffff;border:1px solid #cccccc;padding:5px 10px;">\n<ul>\n{content}\n</ul>\n</div>',#リスト
    'paragraph_template': '<p>{content}</p>',#パラグラフ
    'link_template': '<a href="{url}"{target}>{text}</a>',#リンク
    'list_item_template': '\t<li>{content}</li>',#リスト項目
    'table_template': '<table style="width: 100%;">\n\t<tbody>\n{content}\t</tbody>\n</table>',#テーブル
    'table_row_template': '\t\t<tr>\n{content}\t\t</tr>\n',#テーブル行
    'table_cell_th_template': '\t\t\t<th{style}>{content}</th>\n',#テーブルセル（見出し）
    'table_cell_td_template': '\t\t\t<td{style}>{content}</td>\n',#テーブルセル（データ）
    'br_tag': '<br />',#改行
    'nbsp_paragraph': '<p>&nbsp;</p>',#空白パラグラフ
}

# スタイルとクラスの定義
STYLES = {
    'marker_class': 'marker',
    'bordered_div_style': 'background:#ffffff;border:1px solid #cccccc;padding:5px 10px;',
    'table_style': 'width: 100%;',
    'table_cell_center_style': 'text-align: center;',
    'table_cell_orange_bg': 'background-color: #ffe8d1;',
    'table_cell_blue_bg': 'background-color: #F0F8FF;',
}

# IDパターンの定義
ID_PATTERNS = {
    'heading_1_format': get_site_config()['heading_1']['id_format'],
    'heading_2_format': get_site_config()['heading_2_format'],
    'link_item_format': 'heading-{main_number}-{sub_number}',  # デフォルト値（設定で上書きされる）
}

# 句点分割フラグのグローバル設定
SPLIT_ON_PERIOD_FLAGS = {}

# ulフラグのグローバル設定
UL_FLAGS = {}

# olフラグのグローバル設定
OL_FLAGS = {}

def split_paragraph_on_period(content, section_name='テキスト', template='<p>{content}</p>'):
    """
    句点でコンテンツを分割してpタグを作成する
    
    Args:
        content (str): 分割するテキストコンテンツ
        section_name (str): セクション名（フラグ確認用）
        template (str): 使用するHTMLテンプレート
    
    Returns:
        str: 分割されたHTMLまたは元のHTML
    """
    # フラグが設定されていない場合は通常処理
    if not SPLIT_ON_PERIOD_FLAGS.get(section_name, False):
        return template.format(content=content)
    
    # HTMLタグが含まれている場合の処理
    if '<' in content and '>' in content:
        # HTMLタグの構造を保持しながら句点で分割
        import re
        
        # 句点で分割（。で分割）
        sentences = content.split('。')
        
        # 空文字列やスペースのみの文を除去し、句点を復元
        clean_sentences = []
        for i, sentence in enumerate(sentences):
            sentence = sentence.strip()
            if sentence:  # 空でない場合のみ追加
                # 最後の文以外、または元の文字列が句点で終わっている場合は句点を追加
                if i < len(sentences) - 1 or content.rstrip().endswith('。'):
                    clean_sentences.append(sentence + '。')
                else:
                    clean_sentences.append(sentence)
        
        # 分割された文が1つ以下の場合は通常処理
        if len(clean_sentences) <= 1:
            return template.format(content=content)
        
        # HTMLタグを保持しながら分割
        html_parts = []
        for sentence in clean_sentences:
            if sentence.strip():
                # HTMLタグが含まれている場合の処理
                if '<' in sentence and '>' in sentence:
                    # 句点の位置を確認
                    period_pos = sentence.find('。')
                    if period_pos != -1:
                        # 句点の前の部分を取得
                        before_period = sentence[:period_pos]
                        
                        # 句点の前にHTMLタグがあるかチェック
                        if '<' in before_period and '>' in before_period:
                            # 句点の前にHTMLタグがある場合、HTMLタグの開始タグと閉じタグの数を確認
                            # 自己終了タグは開始タグとしてカウントするが閉じタグは不要
                            open_tags = before_period.count('<')
                            close_tags = before_period.count('</')
                            # 自己終了タグの数を引く（閉じタグが不要）
                            self_closing_tags = before_period.count('<br') + before_period.count('<img') + before_period.count('<hr') + before_period.count('<input')
                            open_tags -= self_closing_tags
                            
                            if open_tags > close_tags:
                                # 閉じタグが不足している場合、不足分を追加
                                missing_closes = open_tags - close_tags
                                # 句点の前に不足している閉じタグを追加
                                corrected_sentence = sentence[:period_pos]
                                print("【DEBUG】before_period:", before_period)
                                print("【DEBUG】open_tags:", open_tags, "close_tags:", close_tags, "self_closing_tags:", self_closing_tags)
                                # 不足している閉じタグを追加（spanとstrongの順序で）
                                for _ in range(missing_closes):
                                    if '<span' in corrected_sentence and '</span>' not in corrected_sentence:
                                        corrected_sentence += '</span>'
                                    elif '<strong' in corrected_sentence and '</strong>' not in corrected_sentence:
                                        corrected_sentence += '</strong>'
                                corrected_sentence += sentence[period_pos:]  # 句点以降を追加
                                print("【DEBUG】corrected_sentence:", corrected_sentence)
                                html_parts.append(template.format(content=corrected_sentence))
                            else:
                                # HTMLタグが正しく閉じられている場合
                                html_parts.append(template.format(content=sentence))
                        else:
                            # 句点の前にHTMLタグがない場合、通常処理
                            html_parts.append(template.format(content=sentence))
                    else:
                        # 句点がない場合、通常処理
                        html_parts.append(template.format(content=sentence))
                else:
                    # HTMLタグが含まれていない場合、通常処理
                    html_parts.append(template.format(content=sentence))
        
        return '\n'.join(html_parts)
    
    # HTMLタグが含まれていない場合の処理
    else:
        # 句点で分割（。で分割）
        sentences = content.split('。')
        
        # 空文字列やスペースのみの文を除去し、句点を復元
        clean_sentences = []
        for i, sentence in enumerate(sentences):
            sentence = sentence.strip()
            if sentence:  # 空でない場合のみ追加
                # 最後の文以外、または元の文字列が句点で終わっている場合は句点を追加
                if i < len(sentences) - 1 or content.rstrip().endswith('。'):
                    clean_sentences.append(sentence + '。')
                else:
                    clean_sentences.append(sentence)
        
        # 分割された文が1つ以下の場合は通常処理
        if len(clean_sentences) <= 1:
            return template.format(content=content)
        
        # 各文をpタグで囲む
        html_parts = []
        for sentence in clean_sentences:
            html_parts.append(template.format(content=sentence))
        
        return '\n'.join(html_parts)

def generate_heading_html(level, heading_id, text_content, heading_number=None):
    """サイト設定に基づいて見出しHTMLを生成"""
    site_config = get_site_config()
    
    if level == 1:
        heading_config = site_config['heading_1']
        template = heading_config['tag']
        before = heading_config['before']
        after = heading_config['after']
        
        # テンプレートに応じて適切にフォーマット
        if '{number}' in template and heading_number is not None:
            # 複雑な構造の場合、番号を直接テンプレートに渡す
            if CURRENT_SITE == 'site_complex':
                formatted_tag = template.format(content=text_content, number=heading_number)
            else:
                formatted_tag = template.format(id=heading_id, content=text_content, number=heading_number)
        elif '{id}' in template and heading_id:
            formatted_tag = template.format(id=heading_id, content=text_content)
        else:
            formatted_tag = template.format(content=text_content)
        
        return before + formatted_tag + after
        
    elif level == 2:
        template = site_config['h4_template']
        before = site_config.get('heading_2_before', '')
        after = site_config.get('heading_2_after', '')
        
        if '{id}' in template and heading_id:
            formatted_tag = template.format(id=heading_id, content=text_content)
        else:
            formatted_tag = template.format(content=text_content)
            
        return before + formatted_tag + after
    
    return text_content

def generate_heading_id(level, main_number, sub_number=None):
    """サイト設定に基づいて見出しIDを生成（後方互換性のため残す）"""
    return generate_heading_id_advanced(level, main_number, sub_number)

# 色範囲の定義
orange_rgb_range = {
    'r': (245, 260),  # Rの範囲
    'g': (210, 240),  # Gの範囲
    'b': (175, 225)   # Bの範囲
}

fill_blue_rgb_range = {
    'r': (178, 205),  # Rの範囲
    'g': (207, 220),  # Gの範囲
    'b': (234, 244)   # Bの範囲
}

def rgb_to_hsv(rgb):
    """RGB形式からHSV形式に変換する関数"""
    r, g, b = rgb
    h, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
    return (h * 360, s * 100, v * 100)

def is_blue_color(hex_color):
    """16進数の色コードがHSV色空間で青色かどうか判定する"""
    try:
        # 16進数の色コードをRGBに変換
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)
        rgb = (r, g, b)
        
        # RGBをHSVに変換
        hsv = rgb_to_hsv(rgb)
        
        # 青色の範囲（Hue=200-260）であるかチェック
        return hsv[0] >= 200 and hsv[0] <= 260
    except (ValueError, IndexError):
        return False

def parse_xml_to_html(xml_file_path, output_file_path, json_config=None):
    """
    XMLをHTMLに変換する（JSONコンフィグ対応版）
    
    Args:
        xml_file_path (str): 入力XMLファイルパス
        output_file_path (str): 出力HTMLファイルパス  
        json_config (dict): サイト設定のJSONデータ（オプション）
    """
    print("=== parse_xml_to_html 関数が開始されました ===")
    
    # JSONコンフィグが提供された場合は動的設定を構築
    if json_config:
        configure_from_json_data(json_config)
    else:
        # デフォルト設定を使用
        set_heading1_from_webapp(
            tag_string='<h3 id="heading_1"></h3>',
            before_string='',
            after_string=''
        )
    
    # 単一数字カウンター（見出し2用）
    single_heading_counter = 0
    
    # 名前空間の登録
    namespaces = {
        'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main',
        'w14': 'http://schemas.microsoft.com/office/word/2010/wordml',
        'w15': 'http://schemas.microsoft.com/office/word/2012/wordml',
        'wp': 'http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing',
        'r': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships',
    }
    
    # ファイルを解析
    try:
        tree = ET.parse(xml_file_path)
        root = tree.getroot()
    except ET.ParseError as e:
        print(f"XMLの解析エラー: {e}")
        return
    
    # 見出し1と見出し2のカウンターを初期化
    heading_counters = defaultdict(int)
    
    # HTML出力用の文字列
    html_output = '<!DOCTYPE html>\n<html>\n<head>\n'
    html_output += '<meta charset="UTF-8">\n'
    html_output += '<title>変換されたドキュメント</title>\n'
    html_output += '<style>\n'
    html_output += f'.{STYLES["marker_class"]} {{ background-color: yellow; }}\n'
    html_output += '</style>\n'
    html_output += '</head>\n<body>\n'
    
    # 変換結果を一時的に格納するリスト
    html_elements = []
    
    # コメント情報を収集
    comment_info = collect_comments(xml_file_path, namespaces)
    
    # 処理済みのコメント参照IDを追跡
    processed_comment_refs = set()

    # 見出しを保存するリスト
    headings = []
    
    # テーブルとパラグラフを順番に処理
    body = root.find('.//w:body', namespaces)
    if body is None:
        print("文書本体が見つかりません")
        return
    
    # XMLの要素を処理する
    for element in body:
        tag = element.tag.split('}')[-1]
        
        # テーブルの処理
        if tag == 'tbl':
            # リンクリスト項目が蓄積されている場合は先に出力
            if hasattr(process_blue_text_links, 'link_list_items') and process_blue_text_links.link_list_items:
                link_list_html = generate_link_list_from_items(process_blue_text_links.link_list_items)
                html_elements.append(link_list_html)
                del process_blue_text_links.link_list_items
                
            html_elements.append(convert_table_to_html(element, namespaces))
            continue
        
        # パラグラフの処理
        if tag == 'p':
            p = element
            # スタイルを確認
            pStyle = p.find('.//w:pStyle', namespaces)
            
            # 見出し処理の前にリンクリストを出力
            if pStyle is not None and pStyle.get('{' + namespaces['w'] + '}val') in ['1', '2']:
                if hasattr(process_blue_text_links, 'link_list_items') and process_blue_text_links.link_list_items:
                    link_list_html = generate_link_list_from_items(process_blue_text_links.link_list_items)
                    html_elements.append(link_list_html)
                    del process_blue_text_links.link_list_items
            
            # 見出し1の処理
            if pStyle is not None and pStyle.get('{' + namespaces['w'] + '}val') == '1':
                print("【DEBUG】見出し1の処理に入りました")
                heading_counters[1] += 1
                heading_counters[2] = 0  # 見出し2のカウンターをリセット
                heading_counters['link_counter'] = 0  # リンク項目カウンターもリセット
                
                text_content = get_text_content(p, namespaces)
                if text_content:
                    heading_id = generate_heading_id_advanced(1, heading_counters[1])
                    heading_html_content = generate_heading_html(1, heading_id, text_content, heading_counters[1])
                    heading_html = f'{heading_html_content}\n'
                    html_elements.append(heading_html)
                    # headingsリストにはIDがある場合のみ追加
                    if heading_id:
                        headings.append((heading_id, text_content, 1))
                    else:
                        headings.append(('', text_content, 1))
            
            # TOC（目次）スタイルの処理
            elif pStyle is not None and pStyle.get('{' + namespaces['w'] + '}val') == '10':
                print("【DEBUG】TOC（目次）スタイルの処理に入りました")
                # TOCエントリを処理してリンクリストに変換
                toc_entry = process_toc_entry(p, namespaces)
                if toc_entry:
                    if not hasattr(process_toc_entry, 'toc_list'):
                        process_toc_entry.toc_list = []
                        process_toc_entry.in_toc_section = True
                    process_toc_entry.toc_list.append(toc_entry)
            
            # 見出し2の処理
            elif pStyle is not None and pStyle.get('{' + namespaces['w'] + '}val') == '2':
                print("【DEBUG】見出し2の処理に入りました")
                # TOCリストが存在する場合は、先に出力
                if hasattr(process_toc_entry, 'toc_list') and process_toc_entry.toc_list:
                    toc_html = generate_toc_links(process_toc_entry.toc_list)
                    html_elements.append(toc_html)
                    # TOCリストをリセット
                    del process_toc_entry.toc_list
                    
                if heading_counters[1] > 0:  # 見出し1が存在する場合のみ
                    site_config = get_site_config()
                    
                    # 単一数字パターンかどうかをチェック
                    if site_config.get('heading_2_single_counter', False):
                        single_heading_counter += 1
                        heading_id = generate_heading_id_advanced(2, heading_counters[1], None, single_heading_counter)
                    else:
                        heading_counters[2] += 1
                        heading_id = generate_heading_id_advanced(2, heading_counters[1], heading_counters[2])
                    
                    text_content = get_text_content(p, namespaces)
                    if text_content:
                        heading_html_content = generate_heading_html(2, heading_id, text_content)
                        heading_html = f'{heading_html_content}\n'
                        html_elements.append(heading_html)
                        # headingsリストに追加
                        if heading_id:
                            headings.append((heading_id, text_content, 2))
                        else:
                            headings.append(('', text_content, 2))
            
            # パラグラフ内の青色テキストとコメントのURLをリンクとして処理
            elif has_blue_text_and_url(p, comment_info, namespaces):
                print("【DEBUG】青色テキストとURLの処理に入りました")
                blue_text_segments = find_blue_text_segments(p, namespaces)
                comment_urls = get_urls_from_comments(p, comment_info, namespaces)
                if blue_text_segments and comment_urls:
                    # パラグラフ内のすべてのテキストを取得（青色部分も含む）
                    full_text = get_text_content(p, namespaces)
                    # 青色テキスト部分をリンクで置き換える
                    html_content = process_blue_text_links(full_text, blue_text_segments, comment_urls)
                    # aタグ外にテキストが出ないよう、html_content全体を<p>で囲むだけにする
                    paragraph_html = f'<p>{html_content}</p>'
                    html_elements.append(paragraph_html)
                else:
                    # 青色テキストかURLがない場合は通常のテキストとして処理
                    formatted_content = process_paragraph_runs(p, namespaces)
                    if formatted_content:
                        if '<' in formatted_content and '>' in formatted_content:
                            paragraph_html = HTML_TAGS['paragraph_template'].format(content=formatted_content)
                            html_elements.append(paragraph_html)
                        else:
                            paragraph_html = split_paragraph_on_period(
                                formatted_content, 
                                section_name='テキスト', 
                                template=HTML_TAGS['paragraph_template']
                            )
                            html_elements.append(paragraph_html)
            
            # 罫線内の青色テキストの場合は何もしない（見出し直後のリンクリストに任せる）
            elif is_paragraph_bordered(p, namespaces) and has_blue_text(p, namespaces):
                print("【DEBUG】罫線内の青色テキストを検出")
                print("【DEBUG】罫線内の青色テキストを検出")
                # 青色テキストの内容を確認
                text_content = get_text_content(p, namespaces)
                if text_content and text_content.strip().startswith('・'):
                    # 「・」で始まる青色テキストの場合は、リンクリスト項目として処理
                    # 「・」を除去してテキストを取得
                    link_text = text_content.strip()[1:].strip()
                    
                    # 動的にリンク項目番号をカウント
                    heading_counters['link_counter'] += 1
                    
                    # フォーマットに応じて適切なパラメータを渡す
                    link_format = ID_PATTERNS['link_item_format']
                    if '{main_number}' in link_format and '{sub_number}' in link_format:
                        # 複数数字パターン（例: heading_{main_number}-{sub_number}）
                        heading_id = link_format.format(main_number=heading_counters[1], sub_number=heading_counters['link_counter'])
                    elif '{number}' in link_format:
                        # 単一数字パターン（例: text{number}, heading{number}）
                        heading_id = link_format.format(number=heading_counters['link_counter'])
                    else:
                        # フォールバック
                        heading_id = link_format.format(main_number=heading_counters[1], sub_number=heading_counters['link_counter'])
                    
                    # リンク項目として保存
                    if not hasattr(process_blue_text_links, 'link_list_items'):
                        process_blue_text_links.link_list_items = []
                    
                    link_item = f'<a href="#{heading_id}">{link_text}</a>'
                    process_blue_text_links.link_list_items.append(link_item)
                elif text_content and re.match(r'^\d+\.', text_content.strip()):
                    # 「数字.」で始まる青色テキストの場合は、番号付きリンクリスト項目として処理
                    # 数字.を除去してテキストを取得
                    match = re.match(r'^\d+\.\s*(.*)', text_content.strip())
                    if match:
                        link_text = match.group(1)
                        
                        # 動的にリンク項目番号をカウント
                        heading_counters['link_counter'] += 1
                        
                        # フォーマットに応じて適切なパラメータを渡す
                        link_format = ID_PATTERNS['link_item_format']
                        if '{main_number}' in link_format and '{sub_number}' in link_format:
                            # 複数数字パターン（例: heading_{main_number}-{sub_number}）
                            heading_id = link_format.format(main_number=heading_counters[1], sub_number=heading_counters['link_counter'])
                        elif '{number}' in link_format:
                            # 単一数字パターン（例: text{number}, heading{number}）
                            heading_id = link_format.format(number=heading_counters['link_counter'])
                        else:
                            # フォールバック
                            heading_id = link_format.format(main_number=heading_counters[1], sub_number=heading_counters['link_counter'])
                        
                        # リンク項目として保存
                        if not hasattr(process_blue_text_links, 'numbered_link_list_items'):
                            process_blue_text_links.numbered_link_list_items = []
                        
                        link_item = f'<a href="#{heading_id}">{link_text}</a>'
                        process_blue_text_links.numbered_link_list_items.append(link_item)
                else:
                    # 「・」や「数字.」で始まらない罫線内青色テキストは何もしない
                    pass
            
            # マーカー、太字、罫線の処理
            else:
                print("【DEBUG】通常のパラグラフ処理に入りました")
                # 罫線の判定
                is_bordered = is_paragraph_bordered(p, namespaces)
                print("【DEBUG】罫線判定結果:", is_bordered)
                if is_bordered:
                    text_content = get_text_content(p, namespaces)
                    print("【DEBUG】罫線内テキスト:", repr(text_content))
                
                # パラグラフ内のテキスト実行を処理し、マーカーや太字を適切に適用
                formatted_content = process_paragraph_runs(p, namespaces)
                
                if formatted_content:
                    if is_bordered:
                        div_content = HTML_TAGS['div_bordered_template'].format(content=formatted_content)
                        html_elements.append(div_content)
                    else:
                        # HTMLタグが含まれている場合は句点分割をスキップ
                        if '<' in formatted_content and '>' in formatted_content:
                            paragraph_html = HTML_TAGS['paragraph_template'].format(content=formatted_content)
                            html_elements.append(paragraph_html)
                        else:
                            # 句点分割を適用
                            paragraph_html = split_paragraph_on_period(
                                formatted_content, 
                                section_name='テキスト', 
                                template=HTML_TAGS['paragraph_template']
                            )
                            html_elements.append(paragraph_html)
    
    # 処理の最後に残ったリンクリスト項目を出力
    if hasattr(process_blue_text_links, 'link_list_items') and process_blue_text_links.link_list_items:
        link_list_html = generate_link_list_from_items(process_blue_text_links.link_list_items)
        html_elements.append(link_list_html)
        del process_blue_text_links.link_list_items
    
    # 番号付きリンクリスト項目を出力
    if hasattr(process_blue_text_links, 'numbered_link_list_items') and process_blue_text_links.numbered_link_list_items:
        numbered_list_html = generate_numbered_link_list_from_items(process_blue_text_links.numbered_link_list_items)
        html_elements.append(numbered_list_html)
        del process_blue_text_links.numbered_link_list_items
    
    # 連続するdivの処理
    print("【DEBUG】combine_consecutive_divs呼び出し直前のhtml_elements:", repr(html_elements))
    processed_html = combine_consecutive_divs(html_elements)
    
    # 最終的なHTMLの修正
    processed_html = fix_consecutive_divs(processed_html)
    
    # pタグ内で句点がある場合に</p><p>を挿入する処理
    print("=== split_p_tags_on_period を呼び出します ===")
    processed_html = split_p_tags_on_period(processed_html)
    print("=== split_p_tags_on_period が完了しました ===")
    
    # HTML出力に結合
    html_output += processed_html
    html_output += '</body>\n</html>'
    
    # HTMLファイルを出力
    with open(output_file_path, 'w', encoding='utf-8') as f:
        f.write(html_output)
    
    print(f"変換完了: {output_file_path}")

def find_current_heading_number(html_elements):
    """最後のh3見出しの番号を取得"""
    h3_pattern = re.compile(r'<h3 id="heading_(\d+)">')
    
    # 逆順に検索して最後のh3を見つける
    for element in reversed(html_elements):
        match = h3_pattern.search(element)
        if match:
            return int(match.group(1))
    
    return 0

def generate_subheading_links(subheadings):
    """小見出しへのリンクリストを生成"""
    div_style = 'background:#ffffff;border:1px solid #cccccc;padding:5px 10px;'
    result = f'<div style="{div_style}">\n<ul>\n'
    
    for heading_id, heading_text in subheadings:
        result += f'\t<li><a href="#{heading_id}">{heading_text}</a></li>\n'
    
    result += '</ul>\n</div>\n'
    return result

def generate_heading_links(headings):
    """見出しへのリンクリストを生成する"""
    div_style = 'background:#ffffff;border:1px solid #cccccc;padding:5px 10px;'
    result = f'<div style="{div_style}">\n<ul>\n'
    
    for heading_id, heading_text, level in headings:
        result += f'\t<li><a href="#{heading_id}">{heading_text}</a></li>\n'
    
    result += '</ul>\n</div>\n'
    return result

def has_blue_text(p, namespaces):
    """パラグラフに青色テキストがあるか判定"""
    for r in p.findall('.//w:r', namespaces):
        color_element = r.find('.//w:color', namespaces)
        if color_element is not None:
            color_val = color_element.get('{' + namespaces['w'] + '}val')
            if color_val and is_blue_color(color_val):
                return True
    return False

def find_blue_text_segments(p, namespaces):
    """パラグラフ内の青色テキストセグメントを位置情報付きで取得"""
    blue_segments = []
    
    # テキスト処理のための一時バッファ
    text_buffer = ""
    
    # すべてのテキスト実行を処理
    for r in p.findall('.//w:r', namespaces):
        is_blue = False
        color_element = r.find('.//w:color', namespaces)
        
        if color_element is not None:
            color_val = color_element.get('{' + namespaces['w'] + '}val')
            if color_val and is_blue_color(color_val):
                is_blue = True
        
        # テキスト内容を取得
        text = ""
        for t in r.findall('.//w:t', namespaces):
            if t.text:
                text += t.text
        
        # 青色テキストなら記録
        if is_blue and text:
            start_pos = len(text_buffer)
            end_pos = start_pos + len(text)
            blue_segments.append({
                'text': text,
                'start': start_pos,
                'end': end_pos
            })
        
        # バッファにテキストを追加
        text_buffer += text
    
    return blue_segments

def has_blue_text_and_url(p, comment_info, namespaces):
    """パラグラフに青色テキストがあり、関連するコメントにURLがあるか判定"""
    # 青色テキストの有無を確認
    has_blue = has_blue_text(p, namespaces)
    if not has_blue:
        return False
    
    # コメント参照とURLの確認
    comment_refs = p.findall('.//w:commentReference', namespaces)
    for ref in comment_refs:
        comment_id = ref.get('{' + namespaces['w'] + '}id')
        if comment_id in comment_info:
            # コメント内容にURLが含まれているか確認
            if comment_info[comment_id].get('urls'):
                return True
    
    return False

def get_urls_from_comments(p, comment_info, namespaces):
    """パラグラフに関連するコメントからすべてのURLを取得"""
    urls = []
    comment_refs = p.findall('.//w:commentReference', namespaces)
    
    for ref in comment_refs:
        comment_id = ref.get('{' + namespaces['w'] + '}id')
        if comment_id in comment_info and comment_info[comment_id].get('urls'):
            urls.extend(comment_info[comment_id]['urls'])
    
    return urls

def process_blue_text_links(full_text, blue_segments, urls):
    """
    テキスト内の青色部分にURLをリンクとして適用
    - ドメインを含む場合は内部リンクテンプレート
    - ドメインを含まない場合は外部リンクテンプレート
    - hrefのURLはclient_domain_omitフラグに従いドメインを省略
    """
    if not blue_segments or not urls:
        return full_text

    site_config = get_site_config()
    client_domain = site_config.get('client_domain', '')
    client_domain_omit = site_config.get('client_domain_omit', False)
    internal_link_template = HTML_TAGS.get('link_template', '<a href="{url}"{target}>{text}</a>')
    external_link_template = HTML_TAGS.get('external_link_template', '<a href="{url}" target="_blank" rel="noopener">{text}</a>')

    result = ""
    last_end = 0
    current_url = None
    current_text = ""

    def is_internal(url):
        # client_domainが空なら常に外部扱い
        if not client_domain:
            return False
        # 完全一致またはスラッシュで区切られている場合のみ内部扱い
        return url.startswith(client_domain)

    def omit_domain(url):
        if client_domain_omit and client_domain and url.startswith(client_domain):
            path = url[len(client_domain):] or "/"
            # 先頭が/でなければ付与
            if not path.startswith("/"):
                path = "/" + path
            return path
        return url

    def render_link(template, href, text, target_attr):
        # テンプレートをformat
        html = template.format(url=href, target=target_attr, text=text, content=text)
        html = re.sub(r'href=""', f'href="{href}"', html)
        # aタグ部分のみ抽出
        a_tag_match = re.search(r'<a [^>]*>.*?</a>', html, re.DOTALL)
        if a_tag_match:
            a_tag = a_tag_match.group(0)
            # aタグの前後に何かタグ（例:span）があれば再ラップ
            before = html[:a_tag_match.start()].strip()
            after = html[a_tag_match.end():].strip()
            if before or after:
                # 前後にタグがあればそれでaタグを囲む（例: <span>...</span>）
                # ただし、before/afterがタグであることを確認
                # beforeが<span ...>なら、afterが</span>なら、その中にa_tagを入れる
                before_tag_match = re.match(r'<([a-zA-Z0-9]+)( [^>]*)?>$', before)
                after_tag_match = re.match(r'^</([a-zA-Z0-9]+)>$', after)
                if before_tag_match and after_tag_match and before_tag_match.group(1) == after_tag_match.group(1):
                    tagname = before_tag_match.group(1)
                    attrs = before_tag_match.group(2) or ''
                    return f'<{tagname}{attrs}>{a_tag}</{tagname}>'
                # それ以外はaタグのみ返す
            return a_tag
        return html

    for i, segment in enumerate(blue_segments):
        url_index = min(i, len(urls) - 1)
        url = urls[url_index]
        result += full_text[last_end:segment['start']]
        blue_text = full_text[segment['start']:segment['end']]
        if url.startswith('@'):
            url = url[1:].strip()
        # 内部/外部判定
        if is_internal(url):
            template = internal_link_template
            href = omit_domain(url)
            target_attr = ''
        else:
            template = external_link_template
            href = url
            target_attr = ' target="_blank" rel="noopener"'
        # 連続URLまとめ
        if url == current_url:
            current_text += blue_text
        else:
            if current_url is not None:
                # 直前のリンク出力
                if is_internal(current_url):
                    t = internal_link_template
                    h = omit_domain(current_url)
                    ta = ''
                else:
                    t = external_link_template
                    h = current_url
                    ta = ' target="_blank" rel="noopener"'
                result += render_link(t, h, current_text, ta)
            current_url = url
            current_text = blue_text
        last_end = segment['end']
    # 最後のリンク
    if current_url is not None:
        if is_internal(current_url):
            t = internal_link_template
            h = omit_domain(current_url)
            ta = ''
        else:
            t = external_link_template
            h = current_url
            ta = ' target="_blank" rel="noopener"'
        result += render_link(t, h, current_text, ta)
    result += full_text[last_end:]
    return result

def collect_comments(xml_file_path, namespaces):
    """XMLからコメント情報を収集する"""
    comment_info = {}
    
    # comments.xmlファイルのパスを生成
    xml_dir = os.path.dirname(xml_file_path)
    comments_file = os.path.join(xml_dir, 'comments.xml')
    
    if not os.path.exists(comments_file):
        print(f"コメントファイルが見つかりません: {comments_file}")
        return comment_info
    
    try:
        comments_tree = ET.parse(comments_file)
        comments_root = comments_tree.getroot()
        
        # コメント情報を収集
        for comment in comments_root.findall('.//w:comment', namespaces):
            comment_id = comment.get('{' + namespaces['w'] + '}id')
            if comment_id:
                # コメント情報を初期化
                comment_info[comment_id] = {
                    'text': '',
                    'has_transition': False,
                    'urls': []
                }
                
                # コメント内の全パラグラフを収集
                paragraphs = []
                for p in comment.findall('.//w:p', namespaces):
                    p_text = get_text_content(p, namespaces)
                    paragraphs.append(p_text)
                    
                    # 「遷移先」という文字列があるか確認
                    if "遷移先" in p_text:
                        comment_info[comment_id]['has_transition'] = True
                    
                    # URLを収集（パターン1: ハイパーリンク）
                    hyperlinks = p.findall('.//w:hyperlink', namespaces)
                    for hyperlink in hyperlinks:
                        hyperlink_text = get_text_content(hyperlink, namespaces)
                        if hyperlink_text and (hyperlink_text.startswith('http') or hyperlink_text.startswith('www')):
                            comment_info[comment_id]['urls'].append(hyperlink_text)
                    
                    # URLを収集（パターン2: @で始まるURL）
                    url_pattern = re.compile(r'@(https?://\S+)')
                    for match in url_pattern.finditer(p_text):
                        url = '@' + match.group(1)  # @付きで保存
                        comment_info[comment_id]['urls'].append(url)
                
                # コメント内容を結合
                comment_info[comment_id]['text'] = '\n'.join(paragraphs)
    
    except ET.ParseError as e:
        print(f"コメントXMLの解析エラー: {e}")
    
    return comment_info

def has_blue_text_with_transition_link(p, comment_info, namespaces, processed_comment_refs):
    """パラグラフに青色テキストがあり、関連するコメントに「遷移」という文字列があるか判定 (廃止予定)"""
    # 青色テキストの有無を確認
    has_blue_text = False
    for r in p.findall('.//w:r', namespaces):
        color_element = r.find('.//w:color', namespaces)
        if color_element is not None:
            color_val = color_element.get('{' + namespaces['w'] + '}val')
            if color_val and is_blue_color(color_val):
                has_blue_text = True
                break
    
    if not has_blue_text:
        return False
    
    # コメント参照の確認
    comment_refs = p.findall('.//w:commentReference', namespaces)
    for ref in comment_refs:
        comment_id = ref.get('{' + namespaces['w'] + '}id')
        if comment_id in processed_comment_refs:
            # 既に処理済みのコメント参照はスキップ
            continue
            
        if comment_id in comment_info:
            # コメント内容に「遷移先」という文字列があり、かつURLが1つだけある場合
            if (comment_info[comment_id].get('has_transition', False) and
                comment_info[comment_id].get('urls')):
                processed_comment_refs.add(comment_id)  # 処理済みとしてマーク
                return True
    
    return False

def get_blue_text(p, namespaces):
    """パラグラフ内の青色テキストを取得 (廃止予定)"""
    blue_text = ""
    
    for r in p.findall('.//w:r', namespaces):
        color_element = r.find('.//w:color', namespaces)
        if color_element is not None:
            color_val = color_element.get('{' + namespaces['w'] + '}val')
            if color_val and is_blue_color(color_val):
                for t in r.findall('.//w:t', namespaces):
                    if t.text:
                        blue_text += t.text
    
    return blue_text

def get_link_from_comments(p, comment_info, namespaces):
    """パラグラフに関連するコメントからリンクを取得 (廃止予定)"""
    comment_refs = p.findall('.//w:commentReference', namespaces)
    for ref in comment_refs:
        comment_id = ref.get('{' + namespaces['w'] + '}id')
        if comment_id in comment_info and comment_info[comment_id].get('urls'):
            return comment_info[comment_id]['urls'][0]  # 最初のURLを返す
    
    return ""

def combine_consecutive_divs(html_elements):
    """連続するdivを一つにまとめ、内容を条件に応じて整形する（動的テンプレート対応）"""
    print("【DEBUG】combine_consecutive_divs関数が呼び出されました")
    print("【DEBUG】関数内のhtml_elements:", repr(html_elements))
    
    result = ""
    div_pattern = re.compile(r'<div[^>]*>(.*?)</div>', re.DOTALL)
    
    i = 0
    while i < len(html_elements):
        current = html_elements[i]
        
        # divかどうかチェック
        div_match = div_pattern.search(current)
        if div_match:
            # 連続するdivを探す
            div_contents = []
            div_contents.append(div_match.group(1))
            
            j = i + 1
            while j < len(html_elements):
                next_match = div_pattern.search(html_elements[j])
                if next_match:
                    div_contents.append(next_match.group(1))
                    j += 1
                else:
                    break
            
            # 連続するdivがある場合は一つにまとめる
            if j > i + 1:
                # 既にリストが生成されている内容か確認
                has_existing_list = any('<ul>' in content and '<li>' in content for content in div_contents)
                
                if has_existing_list:
                    # 既存のリストがある場合は、最初のリスト要素をそのまま使用
                    for content in div_contents:
                        if '<ul>' in content and '<li>' in content:
                            result += current  # 元のHTML要素をそのまま使用
                            break
                else:
                    # リスト形式の内容かどうかを判定
                    bullet_items = []
                    numbered_items = []
                    non_list_items = []
                    
                    for content in div_contents:
                        content_stripped = content.strip()
                        if content_stripped.startswith('・'):
                            bullet_items.append(content_stripped)
                        elif re.match(r'^\d+\.', content_stripped):  # 数字.で始まる項目
                            numbered_items.append(content_stripped)
                        else:
                            non_list_items.append(content)
                    
                    if bullet_items:
                        # 箱内テキスト（中点）のテンプレートを取得
                        list_template = HTML_TAGS.get('div_list_template', '<div style="background:#ffffff;border:1px solid #cccccc;padding:5px 10px;"><ul><li>テキスト</li></ul></div>')
                        combined_content = process_bullet_list_items(bullet_items, list_template)
                        result += combined_content + '\n'
                    elif numbered_items:
                        # 箱内テキスト（番号）のテンプレートを取得
                        ordered_template = HTML_TAGS.get('div_ordered_list_template', '<div style="background:#ffffff;border:1px solid #cccccc;padding:5px 10px;"><ol><li>テキスト</li></ol></div>')
                        combined_content = process_numbered_list_items(numbered_items, ordered_template)
                        result += combined_content + '\n'
                    else:
                        # 通常のテキストの場合は従来の処理
                        div_style = 'background:#ffffff;border:1px solid #cccccc;padding:5px 10px;'
                        combined_div = f'<div style="{div_style}">\n'
                        for idx, content in enumerate(div_contents):
                            combined_div += content
                            if idx < len(div_contents) - 1:
                                combined_div += '<br />\n'
                        combined_div += '</div>\n'
                        result += combined_div
                i = j
            else:
                # 連続していない場合は、単一のdivを条件に応じて整形
                content = div_match.group(1)
                
                # 既にリストが含まれているか確認
                if '<ul>' in content and '<li>' in content:
                    # 既存のリストがある場合はそのまま出力
                    result += current
                elif content.strip().startswith('・'):
                    # 「・」で始まる場合は動的テンプレートを使用
                    list_template = HTML_TAGS.get('div_list_template', '<div style="background:#ffffff;border:1px solid #cccccc;padding:5px 10px;"><ul><li>テキスト</li></ul></div>')
                    formatted_content = process_bullet_list_items([content.strip()], list_template)
                    result += formatted_content + '\n'
                elif re.match(r'^\d+\.', content.strip()):
                    # 「数字.」で始まる場合は番号付きリストのテンプレートを使用
                    ordered_template = HTML_TAGS.get('div_ordered_list_template', '<div style="background:#ffffff;border:1px solid #cccccc;padding:5px 10px;"><ol><li>テキスト</li></ol></div>')
                    formatted_content = process_numbered_list_items([content.strip()], ordered_template)
                    result += formatted_content + '\n'
                else:
                    # そのままdivを出力
                    result += current
                
                i += 1
        else:
            # divでない場合はそのまま追加
            result += current
            i += 1
    
    return result

def convert_table_to_html(tbl_element, namespaces):
    """XMLのテーブル要素をHTMLテーブルに変換する"""
    # テーブルテンプレートからスタイルを取得
    table_template = HTML_TAGS.get('table_template', '<table style="width: 100%;">\n\t<tbody>\n{content}\t</tbody>\n</table>')
    
    # テーブルスタイルを抽出
    table_style = ""
    if table_template and '<table' in table_template:
        # <table>タグからstyle属性を抽出
        import re
        style_match = re.search(r'<table[^>]*style="([^"]*)"', table_template)
        if style_match:
            table_style = style_match.group(1)
    
    # デフォルトスタイル（設定されていない場合）
    if not table_style:
        table_style = "width: 100%;"
    
    # テーブル内容を構築
    table_content = ""
    for tr in tbl_element.findall('.//w:tr', namespaces):
        table_content += '\t\t<tr>\n'
        
        # セルを処理
        for tc in tr.findall('.//w:tc', namespaces):
            # セルの背景色を確認
            bg_color_style = get_cell_background_style(tc, namespaces)
            
            # セル内のパラグラフを処理してテキスト内容を取得
            paragraphs = tc.findall('.//w:p', namespaces)
            cell_content = ''
            is_bold = False
            
            for i, p in enumerate(paragraphs):
                # 太字の判定
                bold_elements = p.findall('.//w:b', namespaces)
                if bold_elements:
                    is_bold = True
                
                # パラグラフのテキスト内容を取得
                formatted_content = process_paragraph_runs(p, namespaces)
                if formatted_content:
                    cell_content += formatted_content
                    # 最後のパラグラフ以外は改行を追加
                    if i < len(paragraphs) - 1:
                        cell_content += '<br />'
            
            # セルタイプ（thかtd）と内容を出力
            if is_bold:
                style_attr = ' style="text-align: center;'
                if bg_color_style:
                    style_attr += bg_color_style
                style_attr += '"'
                table_content += f'\t\t\t<th{style_attr}>{cell_content}</th>\n'
            else:
                style_attr = ''
                if bg_color_style:
                    style_attr = f' style="{bg_color_style}"'
                table_content += f'\t\t\t<td{style_attr}>{cell_content}</td>\n'
        
        table_content += '\t\t</tr>\n'
    
    # 設定されたスタイルでテーブル構造を生成
    result = f'<table style="{table_style}">\n\t<tbody>\n{table_content}\t</tbody>\n</table>\n'
    
    return result

def get_cell_background_style(tc, namespaces):
    """セルの背景色を取得し、スタイル文字列を返す"""
    style = ''
    
    # 背景色を取得
    shd = tc.find('.//w:shd', namespaces)
    if shd is not None:
        fill = shd.get('{' + namespaces['w'] + '}fill')
        if fill and fill != 'auto':
            # 16進数の色コードをRGBに変換
            try:
                r = int(fill[0:2], 16)
                g = int(fill[2:4], 16)
                b = int(fill[4:6], 16)
                
                # オレンジの範囲に含まれるか確認
                if (orange_rgb_range['r'][0] <= r <= orange_rgb_range['r'][1] and
                    orange_rgb_range['g'][0] <= g <= orange_rgb_range['g'][1] and
                    orange_rgb_range['b'][0] <= b <= orange_rgb_range['b'][1]):
                    style = 'background-color: #ffe8d1;'
                
                # 青の範囲に含まれるか確認
                elif (fill_blue_rgb_range['r'][0] <= r <= fill_blue_rgb_range['r'][1] and
                      fill_blue_rgb_range['g'][0] <= g <= fill_blue_rgb_range['g'][1] and
                      fill_blue_rgb_range['b'][0] <= b <= fill_blue_rgb_range['b'][1]):
                    style = 'background-color: #F0F8FF;'
            except ValueError:
                # 色コードの解析に失敗した場合は無視
                pass
    
    return style

def is_paragraph_bordered(p, namespaces):
    """パラグラフが罫線を持つかを判定"""
    print("【DEBUG】is_paragraph_bordered関数が呼び出されました")
    
    # 直接パラグラフに罫線属性がある場合
    pBdr = p.find('.//w:pBdr', namespaces)
    if pBdr is not None:
        print("【DEBUG】pBdr要素を検出: True")
        return True
    
    # 段落内のボックス属性を確認
    shd_elements = p.findall('.//w:shd[@w:fill]', namespaces)
    print(f"【DEBUG】shd_elements数: {len(shd_elements)}")
    if shd_elements:
        for shd in shd_elements:
            fill_value = shd.get('{' + namespaces['w'] + '}fill')
            print(f"【DEBUG】fill_value: {fill_value}")
            if fill_value and fill_value != 'auto':
                print("【DEBUG】有効なfill_valueを検出: True")
                return True
    
    # その他の罫線判定方法を追加
    # 背景色による判定
    bg_elements = p.findall('.//w:shd', namespaces)
    print(f"【DEBUG】bg_elements数: {len(bg_elements)}")
    for bg in bg_elements:
        fill = bg.get('{' + namespaces['w'] + '}fill')
        color = bg.get('{' + namespaces['w'] + '}color')
        print(f"【DEBUG】bg_fill: {fill}, bg_color: {color}")
        if fill and fill != 'auto':
            print("【DEBUG】背景色による罫線判定: True")
            return True
    
    # 段落のスタイル属性を確認
    pPr = p.find('.//w:pPr', namespaces)
    if pPr is not None:
        print("【DEBUG】pPr要素を検出")
        # スタイル名を確認
        pStyle = pPr.find('.//w:pStyle', namespaces)
        if pStyle is not None:
            style_val = pStyle.get('{' + namespaces['w'] + '}val')
            print(f"【DEBUG】段落スタイル: {style_val}")
            # 罫線に関連するスタイル名をチェック
            if style_val and any(keyword in style_val.lower() for keyword in ['border', 'box', 'frame', 'outline']):
                print("【DEBUG】罫線関連スタイルを検出: True")
                return True
    
    print("【DEBUG】罫線判定結果: False")
    return False

def process_paragraph_runs(p, namespaces):
    """パラグラフ内のテキスト実行を処理し、マーカーや太字を適切に適用"""
    result = ""
    text_runs = p.findall('.//w:r', namespaces)
    
    # マーカーと太字の状態を追跡
    current_marker_text = ""
    current_bold_text = ""
    in_marker = False
    in_bold = False
    
    for r in text_runs:
        # 改行タグを確認
        br = r.find('.//w:br', namespaces)
        if br is not None:
            # 現在のマーカーと太字のテキストを出力
            if current_marker_text:
                result += HTML_TAGS['marker_template'].format(content=current_marker_text)
                current_marker_text = ""
            elif current_bold_text:
                result += HTML_TAGS['bold_template'].format(content=current_bold_text)
                current_bold_text = ""
            result += HTML_TAGS['br_tag']
            continue
        
        # テキストを取得
        text = ""
        for t in r.findall('.//w:t', namespaces):
            if t.text:
                text += t.text
        
        if not text:
            continue
        
        # マーカーと太字の判定
        has_highlight = r.find('.//w:highlight', namespaces) is not None
        has_bold = r.find('.//w:b', namespaces) is not None
        
        # デバッグ情報（マーカーの検出状況を確認）
        if text.strip():  # 空でないテキストの場合のみデバッグ出力
            # ハイライト要素の検出
            highlight_elem = r.find('.//w:highlight', namespaces)
            if highlight_elem is not None:
                highlight_val = highlight_elem.get('{' + namespaces['w'] + '}val')
            else:
                pass
            
            # 背景色の属性もチェック
            shd_elements = r.findall('.//w:shd', namespaces)
            if shd_elements:
                for shd in shd_elements:
                    fill_value = shd.get('{' + namespaces['w'] + '}fill')
                    if fill_value:
                        pass
            
            # 太字要素の検出
            bold_elem = r.find('.//w:b', namespaces)
            if bold_elem is not None:
                pass
            
            # 最終的な判定結果
            if has_highlight:
                pass
            else:
                pass
        
        # マーカーの検出を改善（ハイライト属性の詳細チェック）
        if not has_highlight:
            highlight_elem = r.find('.//w:highlight', namespaces)
            if highlight_elem is not None:
                highlight_val = highlight_elem.get('{' + namespaces['w'] + '}val')
                # ハイライトの値が存在し、'none'以外の場合はマーカーとして扱う
                if highlight_val and highlight_val != 'none':
                    has_highlight = True
        
        # 背景色によるマーカーの検出も追加
        if not has_highlight:
            # 背景色の属性をチェック
            shd_elements = r.findall('.//w:shd', namespaces)
            for shd in shd_elements:
                fill_value = shd.get('{' + namespaces['w'] + '}fill')
                if fill_value and fill_value != 'auto':
                    # 黄色系の背景色をマーカーとして扱う
                    if fill_value.lower() in ['ffff00', 'ffff99', 'ffffcc', 'ffff33']:
                        has_highlight = True
                        break
        
        # マーカー判定完了
        
        # マーカーと太字の状態に応じてテキストを処理
        if has_highlight:
            if not in_marker:
                # 前の太字テキストを出力
                if current_bold_text:
                    result += HTML_TAGS['bold_template'].format(content=current_bold_text)
                    current_bold_text = ""
                    in_bold = False
                in_marker = True
            current_marker_text += text
        elif has_bold:
            if not in_bold:
                # 前のマーカーテキストを出力
                if current_marker_text:
                    result += HTML_TAGS['marker_template'].format(content=current_marker_text)
                    current_marker_text = ""
                    in_marker = False
                in_bold = True
            current_bold_text += text
        else:
            # 通常のテキストの場合、現在のマーカーと太字のテキストを出力
            if current_marker_text:
                result += HTML_TAGS['marker_template'].format(content=current_marker_text)
                current_marker_text = ""
                in_marker = False
            if current_bold_text:
                result += HTML_TAGS['bold_template'].format(content=current_bold_text)
                current_bold_text = ""
                in_bold = False
            result += text
    
    # 残りのマーカーと太字のテキストを出力
    if current_marker_text:
        result += HTML_TAGS['marker_template'].format(content=current_marker_text)
    elif current_bold_text:
        result += HTML_TAGS['bold_template'].format(content=current_bold_text)
    
    return result

def get_text_content(element, namespaces):
    """要素内のテキスト内容を取得（マーカーや太字の処理なし、単純にテキストを連結）"""
    text_content = ''
    for r in element.findall('.//w:r', namespaces):
        for t in r.findall('.//w:t', namespaces):
            if t.text:
                text_content += t.text
    return text_content

def fix_consecutive_divs(html_content):
    """連続するdivタグを適切に結合する"""
    # 連続するdivタグのパターン
    div_style_escaped = STYLES['bordered_div_style'].replace(':', r'\:').replace('#', r'\#').replace(';', r'\;')
    div_pattern = re.compile(rf'<div style="{STYLES["bordered_div_style"]}">(.*?)</div>\s*<div style="{STYLES["bordered_div_style"]}">(.*?)</div>', re.DOTALL)
    
    # 連続するdivタグを探して結合
    while True:
        match = div_pattern.search(html_content)
        if not match:
            break
        # 正規表現パターンを修正して、より具体的なマッチングを行う
        div_pattern = re.compile(rf'<div style="{STYLES["bordered_div_style"]}">(.*?)</div>\s*<div style="{STYLES["bordered_div_style"]}">(.*?)</div>', re.DOTALL)
        
        # 各divの内容から余分な空白を削除
        content1 = re.sub(r'\s+', ' ', match.group(1).strip())
        content2 = re.sub(r'\s+', ' ', match.group(2).strip())
        
        # 結合後のdivタグを作成
        combined_div = HTML_TAGS['div_bordered_template'].format(content=f'{content1}{HTML_TAGS["br_tag"]}\n{content2}')
        
        # 元の連続するdivタグを結合後のdivタグで置換
        html_content = html_content[:match.start()] + combined_div + html_content[match.end():]
    
    # 単一のdivタグ内の余分な空白も削除
    single_div_pattern = re.compile(rf'<div style="{STYLES["bordered_div_style"]}">(.*?)</div>', re.DOTALL)
    
    def clean_single_div(match):
        content = match.group(1)
        # 余分な空白と改行を削除
        content = re.sub(r'\n\s+', '\n', content)  # 行の先頭の余分な空白を削除
        content = re.sub(r'\s+', ' ', content)     # 複数の空白を1つにまとめる
        content = re.sub(rf'{HTML_TAGS["br_tag"]}\s+', f'{HTML_TAGS["br_tag"]}\n', content)  # <br />の後の余分な空白を削除
        content = content.strip()                  # 前後の空白を削除
        return HTML_TAGS['div_bordered_template'].format(content=content)
    
    html_content = single_div_pattern.sub(clean_single_div, html_content)
    
    # 全体的な<br />タグの後の余分な空白を削除
    html_content = re.sub(rf'{HTML_TAGS["br_tag"]}\s+', f'{HTML_TAGS["br_tag"]}\n', html_content)
    
    return html_content

def process_toc_entry(p, namespaces):
    """TOCエントリを処理してリンク情報を抽出"""
    # ハイパーリンクのアンカーを取得
    hyperlink = p.find('.//w:hyperlink', namespaces)
    if hyperlink is not None:
        anchor = hyperlink.get('{' + namespaces['w'] + '}anchor')
        if anchor:
            # ハイパーリンク内のテキストを取得
            text_content = ""
            for r in hyperlink.findall('.//w:r', namespaces):
                for t in r.findall('.//w:t', namespaces):
                    if t.text:
                        text_content += t.text
            
            if text_content:
                # TOCアンカーをHTMLのidに変換
                # _Toc198631343 -> heading_4-1 のような形式に変換
                html_id = convert_toc_anchor_to_heading_id(anchor, text_content)
                return {
                    'anchor': anchor,
                    'text': text_content,
                    'html_id': html_id
                }
    return None

def convert_toc_anchor_to_heading_id(toc_anchor, text_content):
    """TOCアンカーを適切なHTMLのIDに変換"""
    # 簡易的な変換（実際の見出し番号と対応付け）
    if "福利厚生について" in text_content:
        return "heading_4-1"
    elif "手当・待遇について" in text_content:
        return "heading_4-2"
    elif "シフト・1日の流れ" in text_content:
        return "heading_4-3"
    elif "研修・教育制度" in text_content:
        return "heading_4-4"
    elif "評価制度・キャリアアップ" in text_content:
        return "heading_4-5"
    elif "どんな登録販売者" in text_content:
        return "heading_5-1"
    elif "活躍している登録販売者" in text_content:
        return "heading_5-2"
    elif "向いている登録販売者" in text_content:
        return "heading_5-3"
    else:
        # デフォルトの処理
        return toc_anchor.lower()

def generate_toc_links(toc_entries):
    """TOCエントリからリンクリストを生成"""
    list_content = ""
    for entry in toc_entries:
        # リンクを直接作成（テンプレートを使用せず）
        link_html = f'<a href="#{entry["html_id"]}">{entry["text"]}</a>'
        list_content += HTML_TAGS['list_item_template'].format(content=link_html) + '\n'
    
    return HTML_TAGS['div_list_template'].format(content=list_content)

def generate_link_list_from_items(items):
    """リンクリスト項目からリンクリストを生成"""
    if not items:
        return ""
    
    # 箱内リンクテキスト（中点）のテンプレートを取得
    template = HTML_TAGS.get('div_link_list_template', '<div class="solution" style="padding:10px 15px;border:1px solid #000000;"><li><span style="text-decoration: underline; color: #56a0d6;"><a href="#text1">{content}</a></span></li></div>')
    
    # アイテムから「・」を除去してクリーンにする
    clean_items = []
    for item in items:
        # 既に<a>タグが含まれている場合は、<span>タグで囲む
        if '<a href=' in item:
            # テンプレートから<span>タグの情報を抽出
            span_match = re.search(r'<span[^>]*style="[^"]*"[^>]*>', template)
            if span_match:
                span_tag = span_match.group(0)
                # <a>タグを<span>タグで囲む
                wrapped_item = f'<li>{span_tag}{item}</span></li>'
                clean_items.append(wrapped_item)
            else:
                # <span>タグが見つからない場合は通常の処理
                clean_items.append(f'<li>{item}</li>')
        else:
            # 「・」で始まる場合は除去
            clean_item = item.strip()
            if clean_item.startswith('・'):
                clean_item = clean_item[1:].strip()
            clean_items.append(f'<li>{clean_item}</li>')
    
    # テンプレートから外側のdiv構造を抽出
    div_match = re.search(r'<div[^>]*style="[^"]*"[^>]*>', template)
    if div_match:
        div_start = div_match.group(0)
        # 外側のdiv構造を構築
        li_content = '\n'.join(clean_items)
        result = f"{div_start}\n{li_content}\n</div>"
        return result
    else:
        # divタグが見つからない場合は通常の処理
        li_content = '\n'.join(clean_items)
        return f"<div>\n{li_content}\n</div>"

def test_tag_parsing():
    """タグ解析のテスト関数"""
    test_cases = [
        '<h2 id="rtoc-1" class="wp-block-heading has-text-color" style="color:#0ca5b0">',
        '<h3 id="heading_5">',
        '<h2 class="title" id="section-3">',
        '<h1 id="main-title-10" class="large">content</h1>',
        '<h2 class="simple">',  # IDなし
        '<div id="item_123" class="box">',
        '<span id="label42">text</span>',
        '<h2 id="section01" class="numbered">',  # ゼロパディング（2桁）
        '<h3 id="chapter001">',  # ゼロパディング（3桁）
        '<h1 id="part05" class="main">content</h1>',  # ゼロパディング（2桁）完全タグ
        '<div id="block007" class="content">',  # ゼロパディング（3桁）
    ]
    
    print("=== タグ解析テスト ===")
    for tag in test_cases:
        template, id_format = parse_html_tag_and_extract_id_pattern(tag)
        print(f"入力: {tag}")
        print(f"  → テンプレート: {template}")
        print(f"  → IDフォーマット: {id_format}")
        
        # IDフォーマットのテスト（実際の数値1を代入してみる）
        if id_format and '{number' in id_format:
            try:
                sample_id = id_format.format(number=1)
                print(f"  → サンプルID(1): {sample_id}")
            except:
                print(f"  → サンプルID: フォーマットエラー")
        print()

def analyze_id_pattern_advanced(tag_string):
    """
    HTMLタグを解析してID内の数字パターンを詳細に分析する
    単一数字パターンと複数数字パターンを判別する
    
    Args:
        tag_string (str): HTMLタグ文字列
    
    Returns:
        tuple: (template_tag, id_format, pattern_type)
               pattern_type: 'single' (単一数字) または 'double' (複数数字) または 'none' (数字なし)
    """
    # 複数の数字を含むidパターン（例：heading-1-1）
    double_pattern = re.compile(r'id\s*=\s*["\']([^"\']*?)(\d+)([^"\']*?)(\d+)([^"\']*?)["\']')
    # 単一の数字を含むidパターン（例：text7）
    single_pattern = re.compile(r'id\s*=\s*["\']([^"\']*?)(\d+)([^"\']*?)["\']')
    
    template_tag = tag_string
    id_format = ""
    pattern_type = "none"
    
    # まず複数数字パターンをチェック
    double_match = double_pattern.search(tag_string)
    if double_match:
        # 複数数字パターンの場合
        full_id = double_match.group(0)
        prefix = double_match.group(1)
        first_number = double_match.group(2)
        middle = double_match.group(3)
        second_number = double_match.group(4)
        suffix = double_match.group(5)
        
        # ゼロパディングの検出
        first_padding = len(first_number) if first_number.startswith('0') and len(first_number) > 1 else 0
        second_padding = len(second_number) if second_number.startswith('0') and len(second_number) > 1 else 0
        
        if first_padding > 0:
            first_format = f"{{main_number:0{first_padding}d}}"
        else:
            first_format = "{main_number}"
            
        if second_padding > 0:
            second_format = f"{{sub_number:0{second_padding}d}}"
        else:
            second_format = "{sub_number}"
        
        id_format = f"{prefix}{first_format}{middle}{second_format}{suffix}"
        pattern_type = "double"
        
        # テンプレート内のidを{id}に置換
        new_id_attr = full_id.replace(prefix + first_number + middle + second_number + suffix, '{id}')
        template_tag = tag_string.replace(full_id, new_id_attr)
        
    else:
        # 単一数字パターンをチェック
        single_match = single_pattern.search(tag_string)
        if single_match:
            full_id = single_match.group(0)
            prefix = single_match.group(1)
            number_str = single_match.group(2)
            suffix = single_match.group(3)
            
            # ゼロパディングの検出
            if len(number_str) > 1 and number_str.startswith('0'):
                padding_length = len(number_str)
                id_format = f"{prefix}{{number:0{padding_length}d}}{suffix}"
            else:
                id_format = f"{prefix}{{number}}{suffix}"
                
            pattern_type = "single"
            
            # テンプレート内のidを{id}に置換
            new_id_attr = full_id.replace(prefix + number_str + suffix, '{id}')
            template_tag = tag_string.replace(full_id, new_id_attr)
    
    # {content}を挿入する位置を決定
    if '</h' in template_tag or '</div' in template_tag:
        # 完全なタグ（開始〜終了）の場合
        if '>' in template_tag and '</' in template_tag:
            parts = template_tag.split('>', 1)
            if len(parts) == 2:
                start_part = parts[0] + '>'
                end_part = parts[1]
                if '</' in end_part:
                    content_and_end = end_part.split('</', 1)
                    template_tag = start_part + '{content}</' + content_and_end[1]
    else:
        # 開始タグのみの場合、{content}と終了タグを追加
        if template_tag.startswith('<'):
            tag_name_match = re.match(r'<(\w+)', template_tag)
            if tag_name_match:
                tag_name = tag_name_match.group(1)
                template_tag = template_tag.rstrip('>') + '>{content}</' + tag_name + '>'
    
    return template_tag, id_format, pattern_type

def configure_from_json_data(json_data):
    """
    JSONデータから動的に変数設定を構築する
    
    Args:
        json_data (dict): Webアプリからのサイト設定JSON
    """
    global CURRENT_SITE, HTML_TAGS, STYLES, ID_PATTERNS
    
    # サイト基本情報の取得
    site_name = json_data.get('name', 'Unknown Site')
    site_url = json_data.get('url', 'unknown')
    client_domain = json_data.get('client_domain', '')
    client_domain_omit = json_data.get('client_domain_omit', False)
    
    print(f"[INFO] サイト設定を構築中: {site_name} ({site_url})")
    print(f"[INFO] クライアントドメイン: {client_domain}")
    print(f"[INFO] クライアントドメイン省略フラグ: {client_domain_omit}")
    
    # client_domain, client_domain_omitを反映
    SITE_CONFIGS['webapp_custom']['client_domain'] = client_domain
    SITE_CONFIGS['webapp_custom']['client_domain_omit'] = client_domain_omit
    
    # ルールの取得（フロントエンドとバックエンドの両方の形式に対応）
    rules = []
    
    # フロントエンドからの直接的なrulesプロパティをチェック
    if 'rules' in json_data:
        rules = json_data.get('rules', [])
        print(f"[INFO] フロントエンド形式のルールを取得: {len(rules)}件")
    else:
        # バックエンド形式のconversion_settingsから取得
        conversion_settings = json_data.get('conversion_settings', [])
        if not conversion_settings:
            print("[WARNING] rulesもconversion_settingsも見つかりません")
            return
        
        # 最初のアクティブな設定を使用
        active_setting = None
        for setting in conversion_settings:
            if setting.get('active', False):
                active_setting = setting
                break
        
        if not active_setting:
            print("[WARNING] アクティブな変換設定が見つかりません")
            return
        
        rules = active_setting.get('rules', [])
        print(f"[INFO] バックエンド形式のルールを取得: {len(rules)}件")
    
    # ルールから見出し設定を抽出
    heading_1_rule = None
    heading_2_rule = None
    table_rule = None
    
    for rule in rules:
        if not rule.get('active', False):
            continue
            
        section = rule.get('section', '')
        if section == '大見出し':
            heading_1_rule = rule
        elif section == '中見出し':
            heading_2_rule = rule
        elif section == '表':
            table_rule = rule
    
    # 見出し1の設定
    if heading_1_rule:
        tag_string = heading_1_rule.get('tag', '')
        before_string = heading_1_rule.get('prefix_text', '').replace('\\n', '\n')
        after_string = heading_1_rule.get('suffix_text', '').replace('\\n', '\n')
        
        template_tag, id_format, pattern_type = analyze_id_pattern_advanced(tag_string)
        
        print(f"[DEBUG] 見出し1設定:")
        print(f"  元のタグ: {tag_string}")
        print(f"  テンプレート: {template_tag}")
        print(f"  IDフォーマット: {id_format}")
        print(f"  パターンタイプ: {pattern_type}")
        print(f"  前文字列: '{before_string}'")
        print(f"  後文字列: '{after_string}'")
        
        # サイト設定を更新
        SITE_CONFIGS['webapp_custom']['heading_1'] = {
            'before': before_string,
            'tag': template_tag,
            'after': after_string,
            'id_format': id_format,
        }
        
        # HTML_TAGSを更新
        HTML_TAGS['h3_template'] = template_tag
        ID_PATTERNS['heading_1_format'] = id_format
    
    # 見出し2の設定
    if heading_2_rule:
        tag_string = heading_2_rule.get('tag', '')
        before_string = heading_2_rule.get('prefix_text', '').replace('\\n', '\n')
        after_string = heading_2_rule.get('suffix_text', '').replace('\\n', '\n')
        
        template_tag, id_format, pattern_type = analyze_id_pattern_advanced(tag_string)
        
        print(f"[DEBUG] 見出し2設定:")
        print(f"  元のタグ: {tag_string}")
        print(f"  テンプレート: {template_tag}")
        print(f"  IDフォーマット: {id_format}")
        print(f"  パターンタイプ: {pattern_type}")
        print(f"  前文字列: '{before_string}'")
        print(f"  後文字列: '{after_string}'")
        
        # サイト設定を更新
        SITE_CONFIGS['webapp_custom']['h4_template'] = template_tag
        SITE_CONFIGS['webapp_custom']['heading_2_before'] = before_string
        SITE_CONFIGS['webapp_custom']['heading_2_after'] = after_string
        
        # パターンタイプに応じてフォーマットを設定
        if pattern_type == "double":
            SITE_CONFIGS['webapp_custom']['heading_2_format'] = id_format
            SITE_CONFIGS['webapp_custom']['heading_2_single_counter'] = False
        elif pattern_type == "single":
            # 単一数字の場合は、見出し1に関係なく連続番号
            SITE_CONFIGS['webapp_custom']['heading_2_format'] = id_format
            SITE_CONFIGS['webapp_custom']['heading_2_single_counter'] = True
        else:
            # IDなしの場合
            SITE_CONFIGS['webapp_custom']['heading_2_format'] = ''
            SITE_CONFIGS['webapp_custom']['heading_2_single_counter'] = False
        
        HTML_TAGS['h4_template'] = template_tag
        ID_PATTERNS['heading_2_format'] = id_format
        
        # リンク項目のIDフォーマットも中見出しの設定に基づいて設定
        if id_format:
            # 中見出しのIDフォーマットをベースにリンク項目フォーマットを作成
            # 実際のIDからテンプレート形式に変換
            if pattern_type == "double":
                # 複数数字パターンの場合（例: heading_1-1 → heading_{main_number}-{sub_number}）
                # 数字部分を変数に置換
                link_format = re.sub(r'(\d+)-(\d+)', r'{main_number}-{sub_number}', id_format)
                ID_PATTERNS['link_item_format'] = link_format
            elif pattern_type == "single":
                # 単一数字パターンの場合
                # パターン1: 単純な連番（例: text1, text2, text3...）
                if re.match(r'^[a-zA-Z]+\d+$', id_format):
                    # text1 → text{number} のような形式に変換
                    link_format = re.sub(r'(\d+)$', r'{number}', id_format)
                    ID_PATTERNS['link_item_format'] = link_format
                else:
                    # その他の単一数字パターン（例: heading_1 → heading_{number}）
                    link_format = re.sub(r'(\d+)', r'{number}', id_format)
                    ID_PATTERNS['link_item_format'] = link_format
            else:
                # IDなしの場合はデフォルト
                ID_PATTERNS['link_item_format'] = 'heading-{main_number}-{sub_number}'
            
            print(f"[DEBUG] リンク項目IDフォーマット設定: {ID_PATTERNS['link_item_format']}")
        else:
            # 中見出しにIDがない場合はデフォルト
            ID_PATTERNS['link_item_format'] = 'heading-{main_number}-{sub_number}'
            print(f"[DEBUG] リンク項目IDフォーマット設定: デフォルト")
    
    # テーブルの設定
    if table_rule:
        tag_string = table_rule.get('tag', '')
        print(f"[DEBUG] テーブル設定:")
        print(f"  元のタグ: {tag_string}")
        
        # テーブルテンプレートを設定
        if tag_string:
            HTML_TAGS['table_template'] = tag_string
            print(f"[DEBUG] テーブルテンプレート設定: {tag_string}")
    
    # その他のルールからHTML_TAGSを更新
    section_mapping = {
        'テキスト': 'paragraph_template',
        '太字': 'bold_template',
        'ハイライト': 'marker_template',
        '箱の枠': 'div_bordered_template',
        '内部リンク': 'link_template',
        '外部リンク': 'external_link_template',
        '表': 'table_template',
        '箱内テキスト（中点）': 'div_list_template',
        '箱内テキスト（番号）': 'div_ordered_list_template',
        '箱内リンクテキスト（中点）': 'div_link_list_template',
    }
    
    # 句点分割フラグとulフラグをリセット
    global SPLIT_ON_PERIOD_FLAGS, UL_FLAGS, OL_FLAGS
    SPLIT_ON_PERIOD_FLAGS = {}
    UL_FLAGS = {}
    OL_FLAGS = {}
    
    for rule in rules:
        if not rule.get('active', False):
            continue
            
        section = rule.get('section', '')
        tag = rule.get('tag', '')
        split_on_period = rule.get('split_on_period', False)
        ul_flag = rule.get('ul_flag', False)  # ulフラグを取得
        ol_flag = rule.get('ol_flag', False)  # olフラグを取得
        
        # 句点分割フラグを設定
        if split_on_period:
            SPLIT_ON_PERIOD_FLAGS[section] = True
            print(f"[DEBUG] 句点分割フラグ設定: サイト={CURRENT_SITE}, セクション={section} = True")
        
        # ulフラグを設定（テンプレートにulタグが含まれている場合は自動的にON）
        if ul_flag or (tag and '<ul>' in tag):
            UL_FLAGS[section] = True
            print(f"[DEBUG] ulフラグ設定: サイト={CURRENT_SITE}, セクション={section} = True")
        
        # olフラグを設定（テンプレートにolタグが含まれている場合は自動的にON）
        if ol_flag or (tag and '<ol>' in tag):
            OL_FLAGS[section] = True
            print(f"[DEBUG] olフラグ設定: サイト={CURRENT_SITE}, セクション={section} = True")
        
        if section in section_mapping:
            # tagの中の「テキスト」を{content}に置換
            processed_tag = tag.replace('テキスト', '{content}')
            
            # 箱内テキスト（中点）のデバッグ出力
            if section == '箱内テキスト（中点）':
                print(f"[DEBUG] 箱内テキスト（中点）の元のテンプレート: {tag}")
                print(f"[DEBUG] 箱内テキスト（中点）の処理後テンプレート: {processed_tag}")
            
            # 太字の場合は、パラグラフ内で使用されるためpタグを除去
            if section == '太字':
                # <p><strong>{content}</strong></p> → <strong>{content}</strong>
                processed_tag = re.sub(r'^<p[^>]*>([\s\S]*)</p>$', r'\1', processed_tag.strip())
            
            # ハイライトの場合も同様にpタグを除去（どんな改行・空白・属性にも対応）
            elif section == 'ハイライト':
                # <p>...</p> で囲まれている場合は除去
                processed_tag = re.sub(r'^<p[^>]*>([\s\S]*)</p>$', r'\1', processed_tag.strip())
                # 複数行やインデントにも対応
                processed_tag = processed_tag.strip()
            
            # 箱内テキスト（中点）の場合は改行文字を実際の改行に変換
            elif section == '箱内テキスト（中点）':
                processed_tag = processed_tag.replace('\\n', '\n')
            
            # 箱内テキスト（番号）の場合も改行文字を実際の改行に変換
            elif section == '箱内テキスト（番号）':
                processed_tag = processed_tag.replace('\\n', '\n')
            
            # 内部リンクと外部リンクの場合もpタグを除去（パラグラフ内で使用されるため）
            elif section in ['内部リンク', '外部リンク']:
                # <p>...</p> で囲まれている場合は除去
                processed_tag = re.sub(r'^<p[^>]*>([\s\S]*)</p>$', r'\1', processed_tag.strip())
                # 複数行やインデントにも対応
                processed_tag = processed_tag.strip()
            
            HTML_TAGS[section_mapping[section]] = processed_tag
            print(f"[DEBUG] {section} → {section_mapping[section]}: {processed_tag}")
    
    # 現在のサイトをwebapp_customに設定
    CURRENT_SITE = 'webapp_custom'

def generate_heading_id_advanced(level, main_number, sub_number=None, single_counter=None):
    """
    高度な見出しID生成（単一数字パターンに対応）
    
    Args:
        level (int): 見出しレベル（1または2）
        main_number (int): 大見出し番号
        sub_number (int): 小見出し番号（level2の場合のみ）
        single_counter (int): 単一カウンター（単一数字パターンの場合）
    
    Returns:
        str: 生成されたID
    """
    site_config = get_site_config()
    
    if level == 1:
        format_str = site_config['heading_1']['id_format']
        if not format_str:
            return ""
        return format_str.format(number=main_number)
        
    elif level == 2:
        format_str = site_config['heading_2_format']
        if not format_str:
            return ""
            
        # 単一数字パターンの場合
        if site_config.get('heading_2_single_counter', False):
            return format_str.format(number=single_counter if single_counter is not None else sub_number)
        else:
            # 複数数字パターンの場合
            return format_str.format(main_number=main_number, sub_number=sub_number)
    
    return ""

def test_json_config_parsing(json_data):
    """
    JSONデータから設定を解析してテスト結果を表示する
    
    Args:
        json_data (dict): テスト用のJSONデータ
    """
    print("=== JSONコンフィグ解析テスト ===")
    
    # サイト基本情報
    site_name = json_data.get('name', 'Unknown Site')
    site_url = json_data.get('url', 'unknown')
    print(f"サイト名: {site_name}")
    print(f"サイトURL: {site_url}")
    
    # 変換設定の確認
    conversion_settings = json_data.get('conversion_settings', [])
    print(f"変換設定数: {len(conversion_settings)}")
    
    if not conversion_settings:
        print("ERROR: conversion_settingsが見つかりません")
        return
    
    # アクティブな設定を探す
    active_setting = None
    for setting in conversion_settings:
        if setting.get('active', False):
            active_setting = setting
            print(f"アクティブな設定: {setting.get('name', 'Unnamed')}")
            break
    
    if not active_setting:
        print("ERROR: アクティブな変換設定が見つかりません")
        return
    
    rules = active_setting.get('rules', [])
    print(f"ルール数: {len(rules)}")
    
    # 見出しルールの解析テスト
    heading_rules = {}
    for rule in rules:
        if not rule.get('active', False):
            continue
            
        section = rule.get('section', '')
        if section in ['大見出し', '中見出し']:
            heading_rules[section] = rule
    
    print("\n=== 見出し設定解析結果 ===")
    
    for section_name, rule in heading_rules.items():
        print(f"\n[{section_name}]")
        tag_string = rule.get('tag', '')
        prefix_text = rule.get('prefix_text', '').replace('\\n', '\n')
        suffix_text = rule.get('suffix_text', '').replace('\\n', '\n')
        
        print(f"  元のタグ: {tag_string}")
        print(f"  前文字列: '{prefix_text}'")
        print(f"  後文字列: '{suffix_text}'")
        
        # 高度な解析を実行
        template_tag, id_format, pattern_type = analyze_id_pattern_advanced(tag_string)
        
        print(f"  解析後テンプレート: {template_tag}")
        print(f"  IDフォーマット: {id_format}")
        print(f"  パターンタイプ: {pattern_type}")
        
        # サンプルID生成テスト
        if id_format:
            try:
                if pattern_type == "double":
                    sample_id = id_format.format(main_number=1, sub_number=2)
                    print(f"  サンプルID(1-2): {sample_id}")
                elif pattern_type == "single":
                    sample_id = id_format.format(number=5)
                    print(f"  サンプルID(5): {sample_id}")
                else:
                    print(f"  サンプルID: (IDなし)")
            except Exception as e:
                print(f"  サンプルID生成エラー: {e}")
        else:
            print(f"  サンプルID: (IDなし)")
    
    print("\n=== その他のルール確認 ===")
    other_sections = ['テキスト', '太字', 'ハイライト', '箱の枠', '内部リンク', '外部リンク', '表']
    
    for section in other_sections:
        for rule in rules:
            if rule.get('active', False) and rule.get('section') == section:
                tag = rule.get('tag', '')
                processed_tag = tag.replace('テキスト', '{content}')
                print(f"{section}: {processed_tag}")
                break
    
    print("\n=== テスト完了 ===")

def process_bullet_list_items(items, list_template):
    """
    各行の先頭に「・」がある場合のみliタグで囲み、それ以外はliタグで囲まない。
    divやulタグはlist_templateの内容に従う。
    Args:
        items (list): テキスト項目のリスト
        list_template (str): JSONから取得したリストのHTMLテンプレート
    Returns:
        str: 適切なHTMLリスト構造
    """
    print("【DEBUG】process_bullet_list_items関数が呼び出されました")
    
    if not items or not list_template:
        return ""

    # デバッグ出力
    print(f"[DEBUG] process_bullet_list_items 呼び出し:")
    print(f"[DEBUG] items: {items}")
    print(f"[DEBUG] list_template: {list_template}")

    import re
    
    # 罫線内のテキストを処理
    li_items = []
    for item in items:
        item = item.strip()
        if not item:
            continue
            
        # 既にliタグが付いている場合はそのまま使用
        if item.startswith('<li>') and item.endswith('</li>'):
            li_items.append(item)
        # 「・」で始まる場合は中点を除去してliタグで囲む
        elif item.startswith('・'):
            # 中点を除去してテキストを取得
            clean_text = item.lstrip("・　 ").strip()
            li_items.append(f'<li>{clean_text}</li>')
        else:
            # 「・」で始まらない場合はそのまま追加
            li_items.append(item)

    print(f"[DEBUG] li_items: {li_items}")

    # list_templateから罫線のdivタグを抽出
    div_start_match = re.search(r'<div[^>]*style="[^"]*background:#ffffff;border:1px solid #cccccc;padding:5px 10px;"[^>]*>', list_template)
    if div_start_match:
        div_start = div_start_match.group(0)
        # 罫線のdivタグの開始部分を取得
        outer_start = list_template.split(div_start)[0]
        # 罫線のdivタグの終了部分を取得
        outer_end = '</div>'
        
        # ulフラグをチェックしてulタグを追加するかどうかを判定
        ul_flag_enabled = UL_FLAGS.get('箱内テキスト（中点）', False)
        ol_flag_enabled = OL_FLAGS.get('箱内テキスト（中点）', False)
        
        if li_items:
            if ul_flag_enabled:
                # ulフラグがONの場合はulタグを追加
                ul_content = '\n'.join(li_items)
                result = f"{outer_start}{div_start}\n<ul>\n{ul_content}\n</ul>\n{outer_end}"
            elif ol_flag_enabled:
                # olフラグがONの場合はolタグを追加
                ol_content = '\n'.join(li_items)
                result = f"{outer_start}{div_start}\n<ol>\n{ol_content}\n</ol>\n{outer_end}"
            else:
                # フラグがOFFの場合はliタグをそのまま配置
                li_content = '\n'.join(li_items)
                result = f"{outer_start}{div_start}\n{li_content}\n{outer_end}"
        else:
            result = f"{outer_start}{div_start}\n{outer_end}"
    else:
        # 罫線のdivタグが見つからない場合は従来の処理
        if '{content}' in list_template:
            list_content = '\n'.join(li_items)
            result = list_template.replace('{content}', list_content)
        else:
            result = '\n'.join(li_items)

    print(f"[DEBUG] 結果: {result}")
    return result

def process_numbered_list_items(items, list_template):
    """
    「数字.」から始まるテキスト項目を動的なHTMLリスト構造に変換する
    
    Args:
        items (list): 「数字.」から始まるテキスト項目のリスト
        list_template (str): JSONから取得した番号付きリストのHTMLテンプレート
    
    Returns:
        str: 適切なHTMLリスト構造
    """
    if not items or not list_template:
        return ""
    
    # アイテムから「数字.」を除去してクリーンにする
    clean_items = []
    for item in items:
        clean_item = item.strip()
        # 既にliタグが付いている場合はそのまま使用
        if clean_item.startswith('<li>') and clean_item.endswith('</li>'):
            clean_items.append(clean_item)
        else:
            # 数字.パターンを除去（例：「1.テキスト」→「テキスト」）
            match = re.match(r'^\d+\.\s*(.*)', clean_item)
            if match:
                clean_item = match.group(1)
            clean_items.append(clean_item)
    
    # テンプレートの解析
    # 「{content}」（JSONから変換済み）または「テキスト」を含む場合はリスト項目として扱う
    has_content_placeholders = '{content}' in list_template or 'テキスト' in list_template
    
    if has_content_placeholders:
        # ol/li形式の場合
        if '<ol>' in list_template and '<li>' in list_template:
            # 複数のテンプレート行がある場合は実際のアイテム数に調整
            li_matches = re.findall(r'<li[^>]*>.*?</li>', list_template, re.DOTALL)
            
            if li_matches and len(li_matches) > 1:
                # 複数のliタグがある場合、最初のliをテンプレートとして使用
                first_li = li_matches[0]
                li_content_match = re.search(r'<li[^>]*>(.*?)</li>', first_li, re.DOTALL)
                if li_content_match:
                    li_content = li_content_match.group(1).strip()
                    
                    # 外側の構造を抽出
                    outer_start = list_template.split('<ol')[0] if '<ol' in list_template else ''
                    ol_start_match = re.search(r'<ol[^>]*>', list_template)
                    ol_start = ol_start_match.group(0) if ol_start_match else '<ol>'
                    outer_end_match = re.search(r'</ol>(.*?)$', list_template, re.DOTALL)
                    outer_end = outer_end_match.group(1) if outer_end_match else ''
                    
                    # リスト項目を生成
                    list_content = ""
                    for clean_item in clean_items:
                        # 既にliタグが付いている場合はそのまま使用
                        if clean_item.startswith('<li>') and clean_item.endswith('</li>'):
                            formatted_li = clean_item
                        # 既に<a>タグが含まれている場合は、直接<li>で囲む
                        elif '<a href=' in clean_item:
                            formatted_li = f'<li>{clean_item}</li>'
                        elif '{content}' in li_content:
                            formatted_li = f'<li>{li_content.replace("{content}", clean_item)}</li>'
                        elif 'テキスト' in li_content:
                            formatted_li = f'<li>{li_content.replace("テキスト", clean_item)}</li>'
                        else:
                            formatted_li = f'<li>{clean_item}</li>'
                        list_content += "\t" + formatted_li + "\n"
                    
                    result = f"{outer_start}{ol_start}\n{list_content}</ol>{outer_end}"
                    return result
            
            # 単一のliタグまたは通常の処理
            # ol開始タグと終了タグを抽出
            ol_start_match = re.search(r'<ol[^>]*>', list_template)
            ol_start = ol_start_match.group(0) if ol_start_match else '<ol>'
            
            # 外側のdiv/dl構造を抽出
            outer_start = list_template.split('<ol')[0] if '<ol' in list_template else ''
            outer_end_match = re.search(r'</ol>(.*?)$', list_template, re.DOTALL)
            outer_end = outer_end_match.group(1) if outer_end_match else ''
            
            # li要素のテンプレートを抽出
            li_pattern = re.search(r'<li[^>]*>(.*?)</li>', list_template, re.DOTALL)
            if li_pattern:
                li_content = li_pattern.group(1).strip()
                # 既に{content}になっている場合はそのまま、テキストの場合は置換
                if '{content}' in li_content:
                    li_template = f'<li>{li_content}</li>'
                elif 'テキスト' in li_content:
                    li_template = f'<li>{li_content.replace("テキスト", "{content}")}</li>'
                else:
                    li_template = '<li>{content}</li>'
            else:
                li_template = '<li>{content}</li>'
            
            # リスト項目を生成
            list_content = ""
            for clean_item in clean_items:
                # 既にliタグが付いている場合はそのまま使用
                if clean_item.startswith('<li>') and clean_item.endswith('</li>'):
                    list_content += "\t" + clean_item + "\n"
                # 既に<a>タグが含まれている場合は、直接<li>で囲む
                elif '<a href=' in clean_item:
                    list_content += "\t" + f'<li>{clean_item}</li>' + "\n"
                else:
                    list_content += "\t" + li_template.format(content=clean_item) + "\n"
            
            # ulフラグをチェックしてulタグを追加するかどうかを判定
            ul_flag_enabled = UL_FLAGS.get('箱内テキスト（番号）', False)
            ol_flag_enabled = OL_FLAGS.get('箱内テキスト（番号）', False)
            
            if ol_flag_enabled:
                # olフラグがONの場合はolタグを使用
                result = f"{outer_start}{ol_start}\n{list_content}</ol>{outer_end}"
            elif ul_flag_enabled:
                # ulフラグがONの場合はulタグを使用
                result = f"{outer_start}<ul>\n{list_content}</ul>{outer_end}"
            else:
                # フラグがOFFの場合はliタグをそのまま配置
                result = f"{outer_start}{list_content}{outer_end}"
            
            return result
        
        # span形式の場合（サイト１のような形式）
        elif '<span' in list_template and not ('<ol>' in list_template or '<p>' in list_template or '<dl>' in list_template):
            # span要素のテンプレートを解析
            span_pattern = re.search(r'<span[^>]*>(.*?)</span>', list_template, re.DOTALL)
            if span_pattern:
                span_content = span_pattern.group(1)
                
                # 外側のdiv構造を抽出
                outer_start_match = re.search(r'^(.*?)<span', list_template, re.DOTALL)
                outer_start = outer_start_match.group(1) if outer_start_match else ''
                outer_end_match = re.search(r'</span>(.*?)$', list_template, re.DOTALL)
                outer_end = outer_end_match.group(1) if outer_end_match else ''
                
                # span要素のテンプレート
                span_template_match = re.search(r'<span[^>]*>', list_template)
                span_start = span_template_match.group(0) if span_template_match else '<span>'
                
                # リスト項目を生成（数字.付きで）
                formatted_items = []
                for i, clean_item in enumerate(clean_items, 1):
                    if 'テキスト' in span_content:
                        item_content = span_content.replace('テキスト', clean_item)
                        # 数字.を付加
                        item_content = f"{i}.{item_content}"
                    else:
                        item_content = f"{i}.{clean_item}"
                    formatted_items.append(f"{span_start}{item_content}</span>")
                
                content = '\n    '.join(formatted_items)
                return f"{outer_start}{content}{outer_end}"
        
        # p形式の場合（サイト２のような形式）
        elif '<p>' in list_template and not ('<ol>' in list_template or '<dl>' in list_template):
            # p要素のテンプレートを解析
            p_pattern = re.search(r'<p[^>]*>(.*?)</p>', list_template, re.DOTALL)
            if p_pattern:
                p_content = p_pattern.group(1)
                
                # 外側のdiv構造を抽出
                outer_start_match = re.search(r'^(.*?)<p', list_template, re.DOTALL)
                outer_start = outer_start_match.group(1) if outer_start_match else ''
                outer_end_match = re.search(r'</p>(.*?)$', list_template, re.DOTALL)
                outer_end = outer_end_match.group(1) if outer_end_match else ''
                
                # p要素のテンプレート
                p_template_match = re.search(r'<p[^>]*>', list_template)
                p_start = p_template_match.group(0) if p_template_match else '<p>'
                
                # リスト項目を生成（数字.付きで）
                formatted_items = []
                for i, clean_item in enumerate(clean_items, 1):
                    if 'テキスト' in p_content:
                        item_content = p_content.replace('テキスト', clean_item)
                        # 数字.を付加
                        item_content = f"{i}.{item_content}"
                    else:
                        item_content = f"{i}.{clean_item}"
                    formatted_items.append(f"{p_start}{item_content}</p>")
                
                content = '\n'.join(formatted_items)
                return f"{outer_start}{content}{outer_end}"
        
        # dl/dd形式の場合（サイト３のような形式）
        elif '<dl>' in list_template and '<dd>' in list_template:
            # dl構造のテンプレートを解析
            dd_pattern = re.search(r'<dd[^>]*[^>]*>(.*?)</dd>', list_template, re.DOTALL)
            if dd_pattern:
                dd_content = dd_pattern.group(1)
                
                # 「数字.テキスト<br>」の繰り返し形式の場合
                if '<br>' in dd_content or '<br />' in dd_content:
                    # dl開始部分を抽出
                    dl_start = list_template.split('<dd')[0] + '<dd' + list_template.split('<dd')[1].split('>')[0] + '>'
                    dl_end = '</dd>' + list_template.split('</dd>')[-1] if '</dd>' in list_template else '</dd>'
                    
                    # リスト項目を生成（数字.付きで<br>区切り）
                    formatted_items = []
                    for i, clean_item in enumerate(clean_items, 1):
                        formatted_items.append(f'{i}.{clean_item}')
                    
                    content = '<br>\n\t\t'.join(formatted_items)
                    return f"{dl_start}\n\t\t{content}\n\t{dl_end}"
            
        # その他のカスタム形式
        else:
            # 一般的な処理（divのみなど）
            # {content}またはテキストを適切に置換
            result = list_template
            
            # 全ての項目を番号付きで改行で結合
            numbered_items = []
            for i, clean_item in enumerate(clean_items, 1):
                numbered_items.append(f'{i}.{clean_item}')
            combined_content = '\n'.join(numbered_items)
            
            if '{content}' in result:
                result = result.replace('{content}', combined_content)
            elif 'テキスト' in result:
                result = result.replace('テキスト', combined_content)
            
            return result
    else:
        # プレースホルダーがない場合は、項目をそのまま結合
        all_items = '\n'.join(items)
        return f'<div>{all_items}</div>'

def generate_numbered_link_list_from_items(items):
    """番号付きリンクリスト項目からリンクリストを生成"""
    if not items:
        return ""
    
    # 箱内リンクテキスト（番号）のテンプレートを取得
    template = HTML_TAGS.get('div_link_list_template', '<div class="solution" style="padding:10px 15px;border:1px solid #000000;"><li><span style="text-decoration: underline; color: #56a0d6;"><a href="#text1">{content}</a></span></li></div>')
    
    # アイテムから「数字.」を除去してクリーンにする（既にクリーンな状態だが念のため）
    clean_items = []
    for item in items:
        # 既に<a>タグが含まれている場合は、<span>タグで囲む
        if '<a href=' in item:
            # テンプレートから<span>タグの情報を抽出
            span_match = re.search(r'<span[^>]*style="[^"]*"[^>]*>', template)
            if span_match:
                span_tag = span_match.group(0)
                # <a>タグを<span>タグで囲む
                wrapped_item = f'<li>{span_tag}{item}</span></li>'
                clean_items.append(wrapped_item)
            else:
                # <span>タグが見つからない場合は通常の処理
                clean_items.append(f'<li>{item}</li>')
        else:
            # 「数字.」で始まる場合は除去
            clean_item = item.strip()
            match = re.match(r'^\d+\.\s*(.*)', clean_item)
            if match:
                clean_item = match.group(1)
            clean_items.append(f'<li>{clean_item}</li>')
    
    # テンプレートから外側のdiv構造を抽出
    div_match = re.search(r'<div[^>]*style="[^"]*"[^>]*>', template)
    if div_match:
        div_start = div_match.group(0)
        # 外側のdiv構造を構築
        li_content = '\n'.join(clean_items)
        result = f"{div_start}\n{li_content}\n</div>"
        return result
    else:
        # divタグが見つからない場合は通常の処理
        li_content = '\n'.join(clean_items)
        return f"<div>\n{li_content}\n</div>"

def load_json_config_from_files(config_files=None):
    """
    JSONコンフィグファイルを読み込む
    
    Args:
        config_files (list): チェックするJSONファイルのリスト
        
    Returns:
        dict: 読み込まれたJSONコンフィグ（見つからない場合はNone）
    """
    import json
    
    if config_files is None:
        config_files = ["site_config.json", "test.json"]
    
    json_config = None
    
    for config_file in config_files:
        if os.path.exists(config_file):
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    json_config = json.load(f)
                print(f"[INFO] 設定ファイルを読み込みました: {config_file}")
                break
            except json.JSONDecodeError as e:
                print(f"[ERROR] JSON設定ファイルの解析エラー ({config_file}): {e}")
            except Exception as e:
                print(f"[ERROR] 設定ファイル読み込みエラー ({config_file}): {e}")
    
    if json_config is None:
        print("[INFO] JSONコンフィグファイルが見つかりません。デフォルト設定を使用します。")
    else:
        # JSONコンフィグが読み込まれた場合、解析テストを実行
        test_json_config_parsing(json_config)
    
    return json_config

def split_p_tags_on_period(html_content):
    """
    pタグ内で句点がある場合に</p><p>を挿入する処理
    
    Args:
        html_content (str): HTMLコンテンツ
        
    Returns:
        str: 句点で分割されたHTMLコンテンツ
    """

    import re
    # 分割フラグがFalseなら何もせずそのまま返す
    if not SPLIT_ON_PERIOD_FLAGS.get('テキスト', False):
        return html_content
    
    print("=== split_p_tags_on_period 関数が呼び出されました ===")
    print("入力HTML:", html_content[:200] + "..." if len(html_content) > 200 else html_content)
    
    # pタグのパターンを検出
    p_pattern = re.compile(r'<p[^>]*>(.*?)</p>', re.DOTALL)
    
    def split_p_content(match):
        p_start = match.group(0)[:match.group(0).find('>') + 1]  # <p...>部分
        p_end = '</p>'
        content = match.group(1)
        print("=== split_p_content が呼び出されました ===")
        print("元のcontent:", content)
        print("contentの長さ:", len(content))
        flag=0
        
        # HTMLタグが含まれている場合は処理をスキップ（安全のため）
        if '<' in content and '>' in content:
            print("HTMLタグが含まれています。特殊処理を実行します。")
            original_content = content
            
            if '。<strong>' in content or '。<span' in content or '。</strong>' in content or '。</span>' in content:
                print("句点とHTMLタグの組み合わせを検出しました")
                content = content.replace('。<strong>', '。</p><p><strong>').replace('</strong><strong>', '').replace('。</strong></span>', '。</strong></span></p><p>').replace('。<span', '。</p><p><span').replace('。</span>', '。</span></p><p>').replace('<p></p>','')
                print("HTMLタグ処理後のcontent:", content)
                flag=1
            if ('。<strong>' in content or '。<span' in content or '。</strong>' in content or '。</span>' in content) and ('。</strong></span>' not in content):
                print("句点とstrongタグの組み合わせを検出しました")
                content = content.replace('。</strong>', '。</strong></p><p>')
                print("strongタグ処理後のcontent:", content)
                flag=1
            if flag==0:
                print("通常の句点分割を実行します")
                content = content.replace('。','。</p><p>').replace('<p></p>','')
                print("通常処理後のcontent:", content)
            # 修正されたコンテンツをpタグで囲んで返す
            if content == '':
                print("contentが空になりました")
                return ''
            print("最終的なcontent:", content)
            result = f"{p_start}{content}{p_end}"
            result = result.replace('<p></p>','')
            print("返却するHTML:", result)
            return result
        
        # 句点で分割
        print("HTMLタグが含まれていません。通常の句点分割を実行します。")
        sentences = content.split('。')
        print("分割された文の数:", len(sentences))
        print("分割された文:", sentences)
        
        # 空文字列やスペースのみの文を除去し、句点を復元
        clean_sentences = []
        for i, sentence in enumerate(sentences):
            sentence = sentence.strip()
            if sentence:  # 空でない場合のみ追加
                # 最後の文以外、または元の文字列が句点で終わっている場合は句点を追加
                if i < len(sentences) - 1 or content.rstrip().endswith('。'):
                    clean_sentences.append(sentence + '。')
                else:
                    clean_sentences.append(sentence)
        
        print("クリーンアップ後の文:", clean_sentences)
        
        # 分割された文が1つ以下の場合は元のpタグをそのまま返す
        if len(clean_sentences) <= 1:
            print("分割された文が1つ以下です。元のpタグをそのまま返します。")
            return match.group(0)
        
        # 複数の文がある場合、各文をpタグで囲む
        print("複数の文があります。各文をpタグで囲みます。")
        result = ""
        for i, sentence in enumerate(clean_sentences):
            if i == 0:
                # 最初の文は元のpタグを使用
                result += f"{p_start}{sentence}{p_end}"
            else:
                # 2番目以降の文は新しいpタグを作成
                result += f"{p_end}\n{p_start}{sentence}{p_end}"
        
        print("最終的な結果:", result)
        return result
    
    # pタグ内の句点で分割を実行
    print("=== pタグの検索と置換を開始します ===")
    processed_html = p_pattern.sub(split_p_content, html_content)
    print("=== 処理完了 ===")
    print("処理後のHTML（最初の500文字）:", processed_html[:500])
    
    return processed_html

if __name__ == "__main__":
    input_file = "document.xml"
    output_file = "output.html"
    
    # JSONコンフィグファイルを読み込み
    json_config = load_json_config_from_files()
    
    if os.path.exists(input_file):
        parse_xml_to_html(input_file, output_file, json_config)
    else:
        print(f"ファイルが見つかりません: {input_file}")
    print("テスト")

"""
=== Webアプリ連携システムの使用方法 ===

このシステムは、Webアプリから送られるHTMLタグの文字列を自動解析し、
適切な見出しフォーマットでXMLからHTMLへの変換を行います。

1. 自動実行される機能：
   XML変換時に set_heading1_from_webapp() が自動的に呼び出され、
   指定されたHTMLタグ形式が適用されます。

2. HTMLタグの自動解析機能：
   # 基本的な使用例（id内の数字を自動解析）
   set_heading1_from_webapp(
       tag_string='<h2 id="rtoc-1" class="wp-block-heading has-text-color" style="color:#0ca5b0">',
       before_string='',
       after_string=''
   )
   # 結果: テンプレート='<h2 id="{id}" class="wp-block-heading has-text-color" style="color:#0ca5b0">{content}</h2>'
   #       IDフォーマット='rtoc-{number}'
   
   # IDフォーマットを手動指定する場合
   set_heading1_from_webapp(
       tag_string='<h2 id="custom-5" class="title">',
       before_string='<section>\n',
       after_string='\n</section>',
       id_format='custom-section-{number}'  # 手動指定が優先される
   )
   
   # IDがないタグの場合
   set_heading1_from_webapp(
       tag_string='<h2 class="simple-heading">',
       before_string='',
       after_string='',
   )
   # 結果: デフォルトのIDフォーマット='heading_{number}'が使用される

3. 自動解析される例：
   入力タグ                                  → テンプレート                               → IDフォーマット
   '<h2 id="rtoc-1" class="wp">'            → '<h2 id="{id}" class="wp">{content}</h2>' → 'rtoc-{number}'
   '<h3 id="heading_5">'                    → '<h3 id="{id}">{content}</h3>'            → 'heading_{number}'
   '<h2 class="title" id="section-3">'      → '<h2 class="title" id="{id}">{content}</h2>' → 'section-{number}'
   '<h1 id="main-title-10">content</h1>'    → '<h1 id="{id}">{content}</h1>'            → 'main-title-{number}'
   '<h2 id="section01" class="numbered">'   → '<h2 id="{id}" class="numbered">{content}</h2>' → 'section{number:02d}'
   '<h3 id="chapter001">'                   → '<h3 id="{id}">{content}</h3>'            → 'chapter{number:03d}'
   '<h2 class="simple">'                    → '<h2 class="simple">{content}</h2>'       → 'heading_{number}' (デフォルト)

4. パラメータ説明：
   - tag_string: 見出しのHTMLタグ（id内の数字は自動で変数化される）
   - before_string: タグの前に置く文字列（オプション）
   - after_string: タグの後に置く文字列（オプション）
   - id_format: IDのフォーマット（Noneの場合は自動解析、空文字列でIDなし）

5. 処理の優先順位：
   - IDフォーマット: 手動指定 > 自動解析 > デフォルト('heading_{number}')
   - テンプレート: HTMLタグから自動生成（{id}と{content}を含む）

6. 自動処理される内容：
   - id属性内の数字を自動検出し、{number}に変換
   - ゼロパディング（01, 02, 001など）を自動検出し、適切なフォーマット文字列を生成
   - 完全なHTMLタグ（開始～終了）が与えられた場合、{content}が適切な位置に挿入される
   - 開始タグのみの場合、{content}と終了タグを追加
   - 設定は自動的に'webapp_custom'モードに切り替わる

7. 出力例：
   # before_string + formatted_tag + after_string の形式で出力される
   set_heading1_from_webapp('<h2 id="rtoc-5" class="title">', '<section>\n', '\n</section>')
   → <section>
     <h2 id="rtoc-1" class="title">見出しテキスト</h2>
     </section>

8. テスト機能：
   test_tag_parsing()関数でタグ解析の動作をテストできます：
   ```python
   test_tag_parsing()  # 様々なHTMLタグのテスト結果を表示
   ```

9. 使用例（XML変換開始時の設定）：
   現在は以下の設定で自動実行されます：
   ```python
   set_heading1_from_webapp(
       tag_string='<h3 id="heading_1"></h3>',
       before_string='',
       after_string=''
   )
   ```
""" 