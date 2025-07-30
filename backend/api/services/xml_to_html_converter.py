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
        'heading_2_format': 'text{number}',  # 単一数字形式をデフォルトに
        'client_domain': '',  # 追加: 内部リンク判定用
        'client_domain_omit': False,  # 追加: ドメイン省略フラグ
    },
}

# 使用するサイト設定を選択
CURRENT_SITE = 'webapp_custom'  # Webアプリ連携用設定のみ使用

# 選択されたサイト設定を取得
def get_site_config():
    return SITE_CONFIGS[CURRENT_SITE]

def get_closing_tags_for_section(section_name):
    """
    指定されたセクションの閉じタグを取得する
    
    Args:
        section_name (str): セクション名（'大見出し' または '中見出し'）
        
    Returns:
        str: 閉じタグ文字列、設定されていない場合は空文字列
    """
    # グローバル変数からルール情報を取得
    global RULES_DATA
    
    if not hasattr(get_closing_tags_for_section, 'rules_cache'):
        get_closing_tags_for_section.rules_cache = {}
    
    # キャッシュから取得
    if section_name in get_closing_tags_for_section.rules_cache:
        return get_closing_tags_for_section.rules_cache[section_name]
    
    # ルールデータから該当するセクションの閉じタグを取得
    closing_tags = ""
    if RULES_DATA:
        for rule in RULES_DATA:
            if rule.get('section') == section_name:
                closing_tags = rule.get('closing_tags', '')
                break
    
    # キャッシュに保存
    get_closing_tags_for_section.rules_cache[section_name] = closing_tags
    
    return closing_tags

def get_header_footer_tags():
    """
    文頭・文末のタグを取得する
    
    Returns:
        tuple: (header_tag, footer_tag)
               header_tag: 文頭のHTMLタグ
               footer_tag: 文末のHTMLタグ
    """
    global rules
    
    header_tag = ""
    footer_tag = ""
    
    if 'rules' in globals() and rules:
        for rule in rules:
            if rule.get('active', False):
                if rule.get('section') == '文頭':
                    header_tag = rule.get('tag', '')
                elif rule.get('section') == '文末':
                    footer_tag = rule.get('tag', '')
    
    return header_tag, footer_tag

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
    'div_bordered_template': '<div>{content}</div>',  # 罫線
    'div_list_template': '<div>\n<ul>\n{content}\n</ul>\n</div>',  # リスト
    'paragraph_template': '<p>{content}</p>',#パラグラフ
    'link_template': '<a href="{url}"{target}>{text}</a>',#リンク
    'list_item_template': '\t<li>{content}</li>',#リスト項目
    'table_template': '<table style="width: 100%;">\n\t<tbody>\n{content}\t</tbody>\n</table>',#テーブル
    'table_row_template': '\t\t<tr>\n{content}\t\t</tr>\n',#テーブル行
    'table_cell_th_template': '\t\t\t<th{style}>{content}</th>\n',#テーブルセル（見出し）
    'table_cell_td_template': '\t\t\t<td{style}>{content}</td>\n',#テーブルセル（データ）
    'br_tag': '<br />',#改行
    'nbsp_paragraph': '<p>&nbsp;</p>',#空白パラグラフ
    # 単体テーブル要素（テーブルルール用）
    'tr_tag': '<tr>{content}</tr>',
    'th_tag': '<th>{content}</th>',
    'td_tag': '<td>{content}</td>',
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

# グローバルリンクカウンター
global_link_counter = 1

# 見出し番号をグローバルで管理（シンプルに）
major_heading_counter = 0  # 大見出し番号
minor_heading_counter = 0  # 中見出し番号（heading-x-yの形式用）
cumulative_heading_counter = 0  # 累積中見出し番号（textNの形式用）
box_links_processed = False  # 罫線内リンクテキストが処理されたかのフラグ

def reset_heading_counters():
    """見出しカウンターをリセット（累積カウンターは除く）"""
    global major_heading_counter, minor_heading_counter, box_links_processed
    major_heading_counter = 0
    minor_heading_counter = 0
    box_links_processed = False
    print(f"【初期化】見出しカウンターをリセット: 大見出し={major_heading_counter}, 中見出し={minor_heading_counter}")

def increment_major_heading():
    """大見出し番号をインクリメントし、中見出し番号をリセット（累積カウンターは維持）"""
    global major_heading_counter, minor_heading_counter
    major_heading_counter += 1
    minor_heading_counter = 0  # heading-x-y形式用の番号のみリセット
    print(f"【COUNTER】大見出し番号を{major_heading_counter}にインクリメント（中見出し番号をリセット）")
    return major_heading_counter

def increment_minor_heading():
    """中見出し番号をインクリメント"""
    global minor_heading_counter
    minor_heading_counter += 1
    print(f"【COUNTER】中見出し番号を{minor_heading_counter}にインクリメント（大見出し={major_heading_counter}）")
    return minor_heading_counter

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
    return generate_heading_html_simple(level, heading_id, text_content, heading_number)

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

def parse_xml_to_html(xml_file_path, output_file_path, json_config=None, variable_values=None):
    """
    XMLをHTMLに変換する（JSONコンフィグ対応版）
    """
    print("=== parse_xml_to_html 関数が開始されました ===")
    global rules, global_link_counter, box_links_processed, cumulative_heading_counter
    
    # グローバルカウンターの初期化（未初期化の場合のみ）
    if 'global_link_counter' not in globals() or global_link_counter is None:
        global_link_counter = 0
    # 見出しカウンターはリセット（これは文書単位でリセットが必要）
    reset_heading_counters()
    
    # 累積見出しカウンターも0にリセット（変換処理の開始時は必ず0から始める）
    cumulative_heading_counter = 0
    print(f"【初期化】累積見出しカウンターを1にリセット: cumulative_heading_counter={cumulative_heading_counter}")
    
    # use_bullet_pointsフラグを取得（デフォルトはTrue）
    use_bullet_points = True
    if json_config:
        print(f"[DEBUG] JSON CONFIG STRUCTURE: {list(json_config.keys())}")
        # 直接プロパティとして設定がある場合（フロントエンドからの送信形式）
        if 'use_bullet_points' in json_config:
            use_bullet_points = json_config.get('use_bullet_points', True)
            print(f"[DEBUG] Pattern 1 - direct use_bullet_points: {use_bullet_points}")
        # パターン2: sites配列内に設定がある場合（別のケース用）
        elif 'sites' in json_config and json_config['sites']:
            site_config = json_config['sites'][0]
            use_bullet_points = site_config.get('use_bullet_points', True)
            print(f"[DEBUG] Pattern 1 - sites[0].use_bullet_points: {use_bullet_points}")
        # パターン2: 直接プロパティとして設定がある場合
        elif 'use_bullet_points' in json_config:
            use_bullet_points = json_config.get('use_bullet_points', True)
            print(f"[DEBUG] Pattern 2 - direct use_bullet_points: {use_bullet_points}")
        else:
            print(f"[DEBUG] use_bullet_points not found in JSON, using default: {use_bullet_points}")
    print(f"[DEBUG] FINAL use_bullet_points: {use_bullet_points}")
    
    # JSONコンフィグが提供された場合は動的設定を構築
    if json_config:
        configure_from_json_data(json_config)
        # ルールをグローバル変数に格納
        if 'conversion_settings' in json_config and json_config['conversion_settings']:
            rules = json_config['conversion_settings'][0].get('rules', [])
        elif 'rules' in json_config:
            rules = json_config.get('rules', [])
        else:
            rules = []
    else:
        # デフォルト設定を使用
        set_heading1_from_webapp(
            tag_string='<h3 id="heading_1"></h3>',
            before_string='',
            after_string=''
        )
    
    # 単一数字カウンター（グローバル変数を使用）
    global single_heading_counter
    
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
    
    # 見出し番号はグローバル変数で管理（簡潔な管理）
    
    # 文頭・文末のタグを取得
    header_tag, footer_tag = get_header_footer_tags()
    
    # HTML出力用の文字列（文頭のHTMLタグを追加）
    html_output = header_tag
    
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
                link_list_html = generate_link_list_from_items(process_blue_text_links.link_list_items, use_bullet_points)
                if link_list_html.strip().startswith('<div') or link_list_html.strip().startswith('<p'):
                    html_elements.append(link_list_html)
                else:
                    div_content = HTML_TAGS['div_bordered_template'].format(content=link_list_html)
                    html_elements.append(div_content)
                del process_blue_text_links.link_list_items
            # ルールから表の設定を取得
            table_rule = None
            if 'rules' in globals():
                for rule in rules:
                    if rule.get('active', False) and rule.get('section') == '表':
                        table_rule = rule
                        break
            html_elements.append(convert_table_to_html(element, namespaces, table_rule))
            continue
        
        # パラグラフの処理
        if tag == 'p':
            p = element
            # スタイルを確認
            pStyle = p.find('.//w:pStyle', namespaces)
            
            # デバッグ: スタイル名とテキスト内容を出力
            style_val = pStyle.get('{' + namespaces['w'] + '}val') if pStyle is not None else None
            text_content_dbg = get_text_content(p, namespaces)
            print("================ パラグラフデバッグ ================")
            print(f"[DEBUG] パラグラフ: style={style_val}, text={repr(text_content_dbg)}")
            print("==================================================")
            
            # 見出し処理の前にリンクリストを出力
            if pStyle is not None and pStyle.get('{' + namespaces['w'] + '}val') in ['1', '2']:
                if hasattr(process_blue_text_links, 'link_list_items') and process_blue_text_links.link_list_items:
                    link_list_html = generate_link_list_from_items(process_blue_text_links.link_list_items, use_bullet_points)
                    if link_list_html.strip().startswith('<div') or link_list_html.strip().startswith('<p'):
                        html_elements.append(link_list_html)
                    else:
                        div_content = HTML_TAGS['div_bordered_template'].format(content=link_list_html)
                        html_elements.append(div_content)
                    del process_blue_text_links.link_list_items
            
            # 見出し1の処理
            if pStyle is not None and pStyle.get('{' + namespaces['w'] + '}val') == '1':
                print("【DEBUG】見出し1の処理に入りました")
                
                # 前の見出し1のセクションを閉じる（2回目以降の場合）
                if major_heading_counter > 0:
                    closing_tags = get_closing_tags_for_section('大見出し')
                    if closing_tags:
                        html_elements.append(closing_tags)
                        print(f"【DEBUG】大見出しセクションを閉じました: {closing_tags}")
                
                # 大見出し処理前に蓄積された箱内リンクテキストを出力
                if hasattr(process_blue_text_links, 'box_link_items') and process_blue_text_links.box_link_items:
                    print(f"【蓄積処理】大見出し前に箱内リンクテキスト {len(process_blue_text_links.box_link_items)}項目を出力")
                    # 箱内リンクテキスト（中点）の場合は現在の大見出し番号を使用
                    if (process_blue_text_links.box_link_major_heading == -1 or
                        (process_blue_text_links.box_link_rule and 
                         process_blue_text_links.box_link_rule.get('section') == '箱内リンクテキスト（中点）')):
                        current_major_for_output = major_heading_counter + 1  # 次の大見出し番号を使用
                        print(f"【修正】箱内リンクテキスト（中点）で次の大見出し番号を使用: {current_major_for_output}")
                    else:
                        current_major_for_output = process_blue_text_links.box_link_major_heading
                    box_link_html = generate_box_link_list_from_items(
                        process_blue_text_links.box_link_items,
                        process_blue_text_links.box_link_rule,
                        current_major_for_output,
                        use_bullet_points,
                        headings
                    )
                    if box_link_html:
                        html_elements.append(box_link_html)
                    # 蓄積をクリア
                    del process_blue_text_links.box_link_items
                    del process_blue_text_links.box_link_rule
                    del process_blue_text_links.box_link_major_heading
                
                # 大見出し番号をインクリメント（中見出し番号も自動リセット）
                current_major_number = increment_major_heading()
                print(f"【HEADING】大見出し{current_major_number}を処理")
                
                text_content = get_text_content(p, namespaces)
                if text_content:
                    heading_id = generate_heading_id_advanced(1, current_major_number)
                    heading_html_content = generate_heading_html(1, heading_id, text_content, current_major_number)
                    heading_html = f'{heading_html_content}\n'
                    html_elements.append(heading_html)
                    # headingsリストにはIDがある場合のみ追加
                    if heading_id:
                        headings.append((heading_id, text_content, 1))
                    else:
                        headings.append(('', text_content, 1))
                continue  # 見出し1の処理後は他の処理をスキップ
            
            # 見出し3（小見出し）の処理
            if pStyle is not None and pStyle.get('{' + namespaces['w'] + '}val') == '3':
                print("【DEBUG】見出し3（小見出し）の処理に入りました")
                # 大見出し・中見出しのカウンターが0なら初期化
                if major_heading_counter == 0:
                    # 小見出し処理前に蓄積された箱内リンクテキストを出力
                    if hasattr(process_blue_text_links, 'box_link_items') and process_blue_text_links.box_link_items:
                        print(f"【蓄積処理】小見出し前に箱内リンクテキスト {len(process_blue_text_links.box_link_items)}項目を出力")
                        # 箱内リンクテキスト（中点）の場合は現在の大見出し番号を使用
                        if (process_blue_text_links.box_link_major_heading == -1 or
                            (process_blue_text_links.box_link_rule and 
                             process_blue_text_links.box_link_rule.get('section') == '箱内リンクテキスト（中点）')):
                            current_major_for_output = major_heading_counter if major_heading_counter > 0 else 1
                            print(f"【修正】箱内リンクテキスト（中点）で現在の大見出し番号を使用: {current_major_for_output}")
                        else:
                            current_major_for_output = process_blue_text_links.box_link_major_heading
                        box_link_html = generate_box_link_list_from_items(
                            process_blue_text_links.box_link_items,
                            process_blue_text_links.box_link_rule,
                            current_major_for_output,
                            use_bullet_points
                        )
                        if box_link_html:
                            html_elements.append(box_link_html)
                        # 蓄積をクリア
                        del process_blue_text_links.box_link_items
                        del process_blue_text_links.box_link_rule
                        del process_blue_text_links.box_link_major_heading
                    
                    increment_major_heading()
                if minor_heading_counter == 0:
                    increment_minor_heading()
                    
                # 中見出しには設定値を使用
                text_content = get_text_content(p, namespaces)
                if text_content:
                    heading_id = generate_heading_id_advanced(2, major_heading_counter, minor_heading_counter, None, 1)
                    heading_html_content = generate_heading_html_simple(2, heading_id, text_content, major_heading_counter, minor_heading_counter, 1)
                    heading_html = f'{heading_html_content}\n'
                    html_elements.append(heading_html)
                    # headingsリストに追加
                    if heading_id:
                        headings.append((heading_id, text_content, 4))
                    else:
                        headings.append(('', text_content, 4))
                continue
            
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
                    
                if major_heading_counter > 0:  # 見出し1が存在する場合のみ
                    # 前の中見出しのセクションを閉じる（2回目以降の場合）
                    if minor_heading_counter > 0:
                        closing_tags = get_closing_tags_for_section('中見出し')
                        if closing_tags:
                            html_elements.append(closing_tags)
                            print(f"【DEBUG】中見出しセクションを閉じました: {closing_tags}")
                    
                    site_config = get_site_config()
                    
                    # 中見出し番号をインクリメント（両方のカウンターを更新）
                    current_minor_number = increment_minor_heading()  # heading-x-y形式用
                    
                    # 常にcumulative_heading_counterをインクリメント（一意性を保証）
                    cumulative_heading_counter += 1
                    heading_id = f"text{cumulative_heading_counter}"
                    
                    if box_links_processed:
                        print(f"【HEADING】罫線内リンク後の中見出し: カウンター{cumulative_heading_counter}を使用")
                        box_links_processed = False  # フラグをリセット
                    else:
                        print(f"【HEADING】通常の中見出し: カウンター{cumulative_heading_counter}を使用")
                    
                    print(f"【HEADING】中見出し{minor_heading_counter}を処理")
                    
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
                continue  # 見出し2の処理後は他の処理をスキップ
            
            # 罫線内の青色テキストの場合は箱内リンクテキスト処理を優先
            elif is_paragraph_bordered(p, namespaces) and has_blue_text(p, namespaces):
                print("【DEBUG】罫線内の青色テキストを検出")
                text_content = get_text_content(p, namespaces)
                print(f"【DEBUG】罫線内テキスト内容: {repr(text_content)}")
                if text_content and text_content.strip().startswith('・'):
                    # 罫線内青色テキストを即座に処理
                    # ルールを決定
                    link_rule = None
                    for section_name in ['箱内リンクテキスト（中点）', '箱内リンクテキスト', '箱の枠']:
                        rule = next((r for r in rules if r.get('active', False) and r.get('section') == section_name), None)
                        if rule:
                            print(f"【即時処理】{section_name}ルールを使用します")
                            link_rule = rule
                            break

                    if link_rule:
                        # テキストを処理
                        if use_bullet_points and '・' in text_content:
                            # 中点除去ONかつ中点がある場合：中点を除去
                            lines = [line.lstrip('・　').strip() for line in text_content.split('\n') if line.strip().startswith('・')]
                            print(f"【即時処理】中点除去: {lines}")
                        else:
                            # 中点除去OFFまたは中点がない場合：中点保持
                            lines = [line.strip() for line in text_content.split('\n') if line.strip()]
                            print(f"【即時処理】中点保持: {lines}")

                        # HTMLを生成
                        box_link_html = generate_box_link_list_from_items(
                            lines,
                            link_rule,
                            major_heading_counter,
                            use_bullet_points,
                            headings
                        )
                        if box_link_html:
                            html_elements.append(box_link_html)
                            box_links_processed = True  # フラグを立てる
                            print(f"【即時処理】罫線内青色テキストを出力: {len(lines)}項目")
                    continue  # 他の処理をスキップ
                    
                    if link_rule:
                        print(f"【DEBUG】選択されたルールを適用: {link_rule.get('section', 'Unknown')}")
                        prefix = link_rule.get('prefix_text', '').replace('\\n', '\n')
                        suffix = link_rule.get('suffix_text', '').replace('\\n', '\n')
                        tag = link_rule.get('tag', '')
                        
                        # use_bullet_pointsフラグで中点除去を制御
                        should_remove_bullets = use_bullet_points
                        print(f"【DEBUG】use_bullet_points設定: {should_remove_bullets}")
                        
                        if should_remove_bullets and '・' in text_content:
                            # 中点除去ONかつ中点がある場合：中点を除去
                            link_lines = [line.lstrip('・　').strip() for line in text_content.split('\n') if line.strip().startswith('・')]
                            print(f"【DEBUG】中点除去処理を実行")
                        else:
                            # 中点除去OFFまたは中点がない場合：改行で分割（中点保持）
                            link_lines = [line.strip() for line in text_content.split('\n') if line.strip()]
                            print(f"【DEBUG】中点保持処理を実行")
                        
                        print(f"【NEWDEBUG】text_content: {repr(text_content)}")
                        print(f"【NEWDEBUG】link_lines: {link_lines}")
                        print(f"【NEWDEBUG】link_lines数: {len(link_lines)}")
                        
                        # 1行分のテンプレート（li+span+a）を抽出
                        item_template = tag
                        li_match = re.search(r'(<li[\s\S]*?</li>)', tag)
                        if li_match:
                            item_template = li_match.group(1)
                        
                        # hrefの数字部分を昇順にする
                        formatted_items = []
                        print(f"【NEWDEBUG】item_template: {item_template}")
                        print(f"【NEWDEBUG】開始 - link_linesのループ処理, グローバルカウンター: {global_link_counter}")
                        
                        # 現在の大見出し番号を取得（リンク発見時点での番号を記録）
                        current_major_at_link_time = major_heading_counter
                        print(f"【リンク処理】リンク発見時の大見出し番号: {current_major_at_link_time}")
                        
                        for local_idx, line in enumerate(link_lines, 1):
                            print(f"【NEWDEBUG】処理中 - local_idx: {local_idx}, line: {line}")
                            # テキストを置換
                            link_html = item_template.replace('テキスト', line)
                            if '{content}' in link_html:
                                link_html = link_html.replace('{content}', line)
                            print(f"【NEWDEBUG】テキスト置換後のlink_html: {link_html}")
                            
                            # hrefの数字を昇順にする（href属性内のみ）
                            if 'href=' in link_html:
                                print(f"【NEWDEBUG】href属性が見つかりました")
                                # href属性内の数字のみを置換（他の数字は触らない）
                                def replace_href_number(match):
                                    quote_char = match.group(1)  # 引用符（" または '）
                                    href_content = match.group(2)  # href属性の中身
                                    print(f"【NEWDEBUG】replace_href_number - quote_char: {quote_char}, href_content: {href_content}, local_idx: {local_idx}")
                                    # リンク発見時点での大見出し番号を使用
                                    current_major = current_major_at_link_time
                                    print(f"【HREF置換】使用する大見出し番号: {current_major}, local_idx: {local_idx}, href: {href_content}")
                                    if current_major == 0:
                                        print("【警告】大見出し番号が0です！まだ大見出しが処理されていない可能性があります")
                                    
                                    # hrefのパターンを判定して適切な番号を使用
                                    # href内の数字の塊の数で処理を分岐
                                    numbers = re.findall(r'\d+', href_content)
                                    print(f"【HREF判定】href_content='{href_content}', numbers={numbers}")
                                    
                                    # 次の中見出し番号を計算（現在のminor_heading_counter + ローカルインデックス）
                                    global minor_heading_counter
                                    next_heading_number = minor_heading_counter + local_idx
                                    print(f"【DEBUG】現在の中見出し番号: {minor_heading_counter}, ローカルインデックス: {local_idx}, 次の番号: {next_heading_number}")

                                    if '-' in href_content and href_content.count('-') >= 2:
                                        # heading-1-1のようなパターンの場合（数字が2つ）
                                        parts = href_content.split('-')
                                        if len(parts) >= 3:
                                            # 最後から2番目を大見出し番号、最後を中見出し番号に
                                            parts[-2] = str(current_major)  # 大見出し番号
                                            parts[-1] = str(next_heading_number)  # 次の中見出し番号
                                            new_href_content = '-'.join(parts)
                                            print(f"【2つの数字】大見出し番号{current_major}と中見出し番号{next_heading_number}を使用")
                                        else:
                                            # フォールバック
                                            new_href_content = href_content
                                    else:
                                        # text1のようなパターンの場合（数字が1つ）
                                        # 次の中見出し番号を使用
                                        new_href_content = re.sub(r'\d+', str(next_heading_number), href_content, count=1)
                                        print(f"【1つの数字】次の中見出し番号{next_heading_number}を使用")
                                    
                                    print(f"【NEWDEBUG】置換後のhref_content: {new_href_content}")
                                    # 元の形式でhref属性を再構築
                                    result = f'href={quote_char}{new_href_content}{quote_char}'
                                    print(f"【NEWDEBUG】最終的なhref属性: {result}")
                                    return result
                                
                                # href属性のみをターゲットにした置換
                                old_link_html = link_html
                                link_html = re.sub(r'href=(["\'])([^"\']*)\1', replace_href_number, link_html)
                                print(f"【NEWDEBUG】href置換前: {old_link_html}")
                                print(f"【NEWDEBUG】href置換後: {link_html}")
                            else:
                                print(f"【NEWDEBUG】href属性が見つかりませんでした")
                            formatted_items.append(link_html)
                            print(f"【NEWDEBUG】local_idx={local_idx}のアイテム完了: {link_html}")
                        
                        print(f"【NEWDEBUG】ループ完了 - formatted_items: {formatted_items}")
                        # 最終的なHTMLを構築
                        content = '\n'.join(formatted_items)
                        final_html = f"{prefix}{content}{suffix}"
                        print(f"【NEWDEBUG】最終的なHTML: {final_html}")
                        html_elements.append(final_html)
                    else:
                        print("【DEBUG】適用可能なルールが見つかりません（箱内リンクテキスト（中点）、箱内リンクテキスト、箱の枠すべて無効）")
                        # フォールバック: 通常の箱内テキスト処理
                        if use_bullet_points and '・' in text_content:
                            # 中点除去ONかつ中点がある場合：中点を除去
                            link_lines = [line.lstrip('・　').strip() for line in text_content.split('\n') if line.strip().startswith('・')]
                        else:
                            # 中点除去OFFまたは中点がない場合：改行で分割
                            link_lines = [line.strip() for line in text_content.split('\n') if line.strip()]
                        formatted_html = process_bullet_list_items(link_lines, '', use_bullet_points)
                        html_elements.append(formatted_html)
                else:
                    # それ以外は従来通り
                    pass
            
            # パラグラフ内の青色テキストとコメントのURLをリンクとして処理（罫線内でない場合）
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
            
            # マーカー、太字、罫線の処理
            else:
                # 罫線の判定
                is_bordered = is_paragraph_bordered(p, namespaces)
                if is_bordered:
                    text_content = get_text_content(p, namespaces)
                    print("【DEBUG】罫線内テキスト:", repr(text_content))
                
                # パラグラフ内のテキスト実行を処理し、マーカーや太字を適切に適用
                formatted_content = process_paragraph_runs(p, namespaces)
                print(f"【DEBUG】formatted_content: {repr(formatted_content)}")
                print(f"【DEBUG】is_bordered: {is_bordered}")
                
                if formatted_content or is_bordered:  # 罫線がある場合は内容が空でも処理
                    if is_bordered:
                        # 「箱の枠」ルールから設定を取得
                        box_rule = next((r for r in rules if r.get('active', False) and r.get('section') == '箱の枠'), None)
                        if box_rule and box_rule.get('tag'):
                            # 設定からテンプレートを使用
                            div_template = box_rule.get('tag', '')
                            div_content = div_template.format(content=formatted_content or "")
                            print(f"【DEBUG】箱の枠テンプレート適用: {repr(div_content)}")
                        else:
                            # フォールバック: デフォルトのdiv_bordered_template
                            div_content = HTML_TAGS['div_bordered_template'].format(content=formatted_content or "")
                            print(f"【DEBUG】デフォルト箱の枠テンプレート適用: {repr(div_content)}")
                        html_elements.append(div_content)
                    elif formatted_content:  # 罫線がない場合のみformatted_contentをチェック
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
        # 優先順位付きでルールを取得
        rule = None
        for section_name in ['箱内リンクテキスト（中点）', '箱内リンクテキスト', '箱内テキスト（中点）', '箱の枠']:
            rule = next((r for r in rules if r.get('active', False) and r.get('section') == section_name), None)
            if rule:
                print(f"【最終出力】{section_name}ルールを使用（残りリンクリスト）")
                break
        before = rule['prefix_text'] if rule and 'prefix_text' in rule else ''
        after = rule['suffix_text'] if rule and 'suffix_text' in rule else ''
        link_list_html = generate_link_list_from_items(process_blue_text_links.link_list_items, use_bullet_points, before, after)
        html_elements.append(link_list_html)
        del process_blue_text_links.link_list_items
    
    # 番号付きリンクリスト項目を出力
    if hasattr(process_blue_text_links, 'numbered_link_list_items') and process_blue_text_links.numbered_link_list_items:
        rule = next((r for r in rules if r.get('active', False) and r.get('section') == '箱内テキスト（番号）'), None)
        before = rule['prefix_text'] if rule and 'prefix_text' in rule else ''
        after = rule['suffix_text'] if rule and 'suffix_text' in rule else ''
        numbered_list_html = generate_link_list_from_items(process_blue_text_links.numbered_link_list_items, use_bullet_points, before, after)
        html_elements.append(numbered_list_html)
        del process_blue_text_links.numbered_link_list_items
    
    # ドキュメントの最後に残ったセクションを閉じる
    if minor_heading_counter > 0:
        # 最後の中見出しセクションを閉じる
        closing_tags = get_closing_tags_for_section('中見出し')
        if closing_tags:
            html_elements.append(closing_tags)
            print(f"【DEBUG】最後の中見出しセクションを閉じました: {closing_tags}")
    
    # 処理の最後に残っている蓄積された箱内リンクテキストを出力
    if hasattr(process_blue_text_links, 'box_link_items') and process_blue_text_links.box_link_items:
        print(f"【蓄積処理】処理最後に箱内リンクテキスト {len(process_blue_text_links.box_link_items)}項目を出力")
        # 箱内リンクテキスト（中点）の場合は現在の大見出し番号を使用
        if (process_blue_text_links.box_link_major_heading == -1 or
            (process_blue_text_links.box_link_rule and 
             process_blue_text_links.box_link_rule.get('section') == '箱内リンクテキスト（中点）')):
            current_major_for_output = major_heading_counter
            print(f"【修正】箱内リンクテキスト（中点）で現在の大見出し番号を使用: {current_major_for_output}")
        else:
            current_major_for_output = process_blue_text_links.box_link_major_heading
        box_link_html = generate_box_link_list_from_items(
            process_blue_text_links.box_link_items,
            process_blue_text_links.box_link_rule,
            current_major_for_output,
            use_bullet_points
        )
        if box_link_html:
            html_elements.append(box_link_html)
        # 蓄積をクリア
        del process_blue_text_links.box_link_items
        del process_blue_text_links.box_link_rule
        del process_blue_text_links.box_link_major_heading

    if major_heading_counter > 0:
        # 最後の大見出しセクションを閉じる
        closing_tags = get_closing_tags_for_section('大見出し')
        if closing_tags:
            html_elements.append(closing_tags)
            print(f"【DEBUG】最後の大見出しセクションを閉じました: {closing_tags}")
    
    # 連続するdivの処理
    processed_html = combine_consecutive_divs(html_elements, use_bullet_points)
    
    # 最終的なHTMLの修正
    processed_html = fix_consecutive_divs(processed_html)
    
    # pタグ内で句点がある場合に</p><p>を挿入する処理
    print("=== split_p_tags_on_period を呼び出します ===")
    processed_html = split_p_tags_on_period(processed_html)
    print("=== split_p_tags_on_period が完了しました ===")
    
    # 空白テキストを削除する処理
    print("=== remove_empty_text_tags を呼び出します ===")
    processed_html = remove_empty_text_tags(processed_html)
    print("=== remove_empty_text_tags が完了しました ===")
    
    # HTML出力に結合（文末のHTMLタグを追加）
    html_output += processed_html + footer_tag
    
    # 変数置換を適用
    if variable_values:
        html_output = replace_variables_in_html(html_output, variable_values)
    
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

def combine_consecutive_divs(html_elements, use_bullet_points=True):
    """連続するdivを一つにまとめ、内容を条件に応じて整形する（動的テンプレート対応）"""
    result = ""
    div_pattern = re.compile(r'<div[^>]*>(.*?)</div>', re.DOTALL)
    i = 0
    while i < len(html_elements):
        current = html_elements[i]
        div_match = div_pattern.search(current)
        if div_match:
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
            if j > i + 1:
                has_existing_list = any('<ul>' in content and '<li>' in content for content in div_contents)
                # 個別の<li>要素も統合対象にする
                has_individual_li = any('<li>' in content and '<ul>' not in content for content in div_contents)
                print(f"【ULDEBUG】combine_consecutive_divs - has_existing_list: {has_existing_list}")
                print(f"【ULDEBUG】div_contents: {div_contents}")
                # 既存のul/li形式を検出して統合処理
                print("【ULDEBUG】div統合処理を実行")
                
                # 既存の<ul><li>...</li></ul>形式を検出
                ul_li_items = []
                bullet_items = []
                numbered_items = []
                non_list_items = []
                
                for content in div_contents:
                    content_stripped = content.strip()
                    # <ul><li>...</li></ul>形式の検出
                    if content_stripped.startswith('<ul>') and content_stripped.endswith('</ul>') and '<li>' in content_stripped:
                        # <li>...</li>部分を抽出
                        li_match = re.search(r'<li[^>]*>(.*?)</li>', content_stripped, re.DOTALL)
                        if li_match:
                            li_content = li_match.group(1)
                            ul_li_items.append(li_content)
                            print(f"【ULDEBUG】抽出されたli内容: {repr(li_content)}")
                    # 個別の<li>要素の検出
                    elif content_stripped.startswith('<li>') and content_stripped.endswith('</li>') and '<ul>' not in content_stripped:
                        # <li>...</li>部分を抽出
                        li_match = re.search(r'<li[^>]*>(.*?)</li>', content_stripped, re.DOTALL)
                        if li_match:
                            li_content = li_match.group(1)
                            ul_li_items.append(li_content)
                            print(f"【ULDEBUG】個別li要素から抽出: {repr(li_content)}")
                    elif content_stripped.startswith('・'):
                        bullet_items.append(content_stripped)
                    elif re.match(r'^\d+\.', content_stripped):
                        numbered_items.append(content_stripped)
                    else:
                        non_list_items.append(content)
                if ul_li_items:
                    # 既存の<ul><li>...</li></ul>形式を統合
                    print(f"【ULDEBUG】ul_li_items統合処理: {ul_li_items}")
                    
                    # 箱内リンクテキスト（中点）ルールを優先順位付きで取得
                    link_rule = None
                    global rules
                    if 'rules' in globals() and rules:
                        # 優先順位: 箱内リンクテキスト（中点） → 箱内リンクテキスト → 箱の枠
                        for section_name in ['箱内リンクテキスト（中点）', '箱内リンクテキスト', '箱の枠']:
                            link_rule = next((r for r in rules if r.get('active', False) and r.get('section') == section_name), None)
                            if link_rule:
                                print(f"【統合処理】{section_name}ルールを使用します")
                                break
                    
                    if link_rule:
                        prefix = link_rule.get('prefix_text', '').replace('\\n', '\n')
                        suffix = link_rule.get('suffix_text', '').replace('\\n', '\n')
                        print(f"【ULDEBUG】統合処理 - prefix: {repr(prefix)}, suffix: {repr(suffix)}")
                        
                        # 箱内リンクテキスト（中点）の場合は現在の大見出し番号を使用
                        if link_rule.get('section') == '箱内リンクテキスト（中点）':
                            global major_heading_counter
                            current_major = major_heading_counter
                            print(f"【統合処理修正】箱内リンクテキスト（中点）で現在の大見出し番号を使用: {current_major}")
                        else:
                            # その他のルールでは従来通りli要素から大見出し番号を抽出
                            current_major = 1  # デフォルト値
                            
                            # 最初のli要素のhrefから大見出し番号を抽出
                            if ul_li_items:
                                first_item = ul_li_items[0]
                                href_match = re.search(r'href=["\'](#[^"\']*heading-(\d+)-\d+)', first_item)
                                if href_match:
                                    current_major = int(href_match.group(2))
                                    print(f"【統合処理】li要素から抽出した大見出し番号: {current_major}")
                                else:
                                    # フォールバック：グローバル変数を使用
                                    current_major = major_heading_counter
                                    print(f"【統合処理】フォールバック - グローバル変数から取得: {current_major}")
                            else:
                                print("【統合処理警告】ul_li_itemsが空です！")
                        
                        # 各li要素を再構築（href内の数字を見出し番号で置換）
                        formatted_lis = []
                        
                        # 最初のli要素からベース番号を抽出
                        base_number = None
                        if ul_li_items:
                            first_item = ul_li_items[0]
                            href_match = re.search(r'href=["\'](#[^"\']*?)(\d+)([^"\']*)["\']', first_item)
                            if href_match:
                                base_number = int(href_match.group(2))
                                print(f"【統合処理】ベース番号を抽出: {base_number}")
                        
                        for local_idx, item in enumerate(ul_li_items, 1):
                            # href内の数字を連番で置換
                            updated_item = item
                            if 'href=' in updated_item and base_number is not None:
                                def replace_href_with_sequential_numbers(match):
                                    quote_char = match.group(1)
                                    href_content = match.group(2)
                                    
                                    # ベース番号 + 1 + (local_idx - 1) で連番を計算（基準点を1つ下げる）
                                    target_number = (base_number + 1) + (local_idx - 1)
                                    
                                    # href内の数字を連番で置換
                                    if re.search(r'\d+', href_content):
                                        new_href_content = re.sub(r'\d+', str(target_number), href_content)
                                        print(f"【統合処理】href連番更新(idx={local_idx}): {href_content} → {new_href_content}")
                                    else:
                                        new_href_content = href_content
                                    
                                    return f'href={quote_char}{new_href_content}{quote_char}'
                                
                                updated_item = re.sub(r'href=(["\'])([^"\']*)\1', replace_href_with_sequential_numbers, updated_item)
                                print(f"【ULDEBUG】href更新(idx={local_idx}): {item} → {updated_item}")
                            
                            formatted_lis.append(f'\t\t<li>{updated_item}</li>')
                        
                        # 最終的なHTMLを構築
                        content = '\n'.join(formatted_lis)
                        final_html = f"{prefix}\n{content}\n{suffix}"
                        print(f"【ULDEBUG】統合結果: {repr(final_html)}")
                        result += final_html + '\n'
                    else:
                        # フォールバック: 元の形式で結合
                        for content in div_contents:
                            result += content + '\n'
                elif bullet_items:
                    # 改良した関数で自動的にルールを判別
                    combined_content = process_bullet_list_items(bullet_items, '', use_bullet_points)
                    result += combined_content + '\n'
                elif numbered_items:
                    # 改良した関数で自動的にルールを判別
                    combined_content = process_numbered_list_items(numbered_items, '', use_bullet_points)
                    result += combined_content + '\n'
                else:
                    # 通常のテキストの場合は従来の処理
                    div_style = 'background:#ffffff;border:1px solid #cccccc;padding:5px 10px;'
                    combined_div = f'<div style="{div_style}">\n'
                    for idx, content in enumerate(div_contents):
                        combined_div += content
                        # リンクテキスト（<a href=と<li>を含む）の場合は<br />を挿入しない
                        if idx < len(div_contents) - 1:
                            # リンクテキストまたは箱内リンクテキストの場合は改行のみ
                            if ('<a href=' in content and '<li>' in content) or ('div_link_list_template' in HTML_TAGS and HTML_TAGS['div_link_list_template'] in content):
                                combined_div += '\n'
                            else:
                                combined_div += '<br />\n'
                    combined_div += '</div>\n'
                    result += combined_div
                i = j
            else:
                content = div_match.group(1)
                print(f"【ULDEBUG】単一div処理 - current: {repr(current)}")
                print(f"【ULDEBUG】単一div処理 - content: {repr(content)}")
                # ulありの分岐を無効化
                # if '<ul>' in content and '<li>' in content:
                #     print("【ULDEBUG】ul/li含有のため、そのまま追加")
                #     result += current
                # elif content.strip().startswith('・'):
                if content.strip().startswith('・'):
                    print("【ULDEBUG】中点で始まるため、process_bullet_list_items呼び出し")
                    # 改良した関数で自動的にルールを判別
                    formatted_content = process_bullet_list_items([content.strip()], '', use_bullet_points)
                    result += formatted_content + '\n'
                elif re.match(r'^\d+\.', content.strip()):
                    # 改良した関数で自動的にルールを判別
                    formatted_content = process_numbered_list_items([content.strip()], '', use_bullet_points)
                    result += formatted_content + '\n'
                else:
                    # リンクテキスト（<a href=を含む）の場合は元のdiv構造を保持
                    if '<a href=' in content:
                        print("【ULDEBUG】リンクテキストのため、元のdiv構造を保持")
                        # 単一div処理でも元のdiv構造を保持
                        result += current + '\n'
                    else:
                        print("【ULDEBUG】通常のテキストのため、content + <br />で処理")
                        result += content + '<br />\n'
                i += 1
        else:
            result += current
            i += 1
    return result

def convert_table_to_html(tbl_element, namespaces, table_rule=None):
    """XMLのテーブル要素をHTMLテーブルに変換する（ルール対応版）"""
    print(f"【TABLE_CONVERT】convert_table_to_html関数が呼ばれました")
    
    # HTML_TAGSから個別のタグを取得してテンプレートを再構築
    table_tag = HTML_TAGS.get('table_tag', '<table style="width: 100%;">')
    tbody_tag = HTML_TAGS.get('tbody_tag', '<tbody>{content}</tbody>')
    tr_tag = HTML_TAGS.get('tr_tag', '<tr>{content}</tr>')
    th_tag = HTML_TAGS.get('th_tag', '<th>{content}</th>')
    td_tag = HTML_TAGS.get('td_tag', '<td>{content}</td>')
    
    print(f"【TABLE_CONVERT】取得したタグ - table_tag: '{table_tag}', tbody_tag: '{tbody_tag}'")
    
    # テンプレートを直接構築
    if table_tag and tbody_tag:
        # table_tagから開始タグのみを抽出
        table_start_match = re.match(r'(<table[^>]*>)', table_tag)
        clean_table_start = table_start_match.group(1) if table_start_match else '<table>'
        # 完全なテンプレートを構築
        table_template = clean_table_start + '<tbody>{content}</tbody></table>'
    else:
        # フォールバック
        table_template = '<table style="width: 100%;"><tbody>{content}</tbody></table>'
    
    print(f"【TABLE_CONVERT】構築したテンプレート: '{table_template}'")

    # ルールが渡されていれば上書き
    if table_rule:
        if table_rule.get('tag'):  # table_rule.tagがある場合は全体テンプレートとして使用
            table_template = table_rule['tag']
        if table_rule.get('tr_tag'):
            tr_tag = table_rule['tr_tag']
        if table_rule.get('th_tag'):
            th_tag = table_rule['th_tag']
        if table_rule.get('td_tag'):
            td_tag = table_rule['td_tag']

    trs = tbl_element.findall('.//w:tr', namespaces)
    table_content = ""
    for tr_idx, tr in enumerate(trs):
        row_content = ""
        tcs = tr.findall('.//w:tc', namespaces)
        for tc in tcs:
            paragraphs = tc.findall('.//w:p', namespaces)
            cell_content = ''
            for i, p in enumerate(paragraphs):
                formatted_content = process_paragraph_runs(p, namespaces)
                if formatted_content:
                    cell_content += formatted_content
                    if i < len(paragraphs) - 1:
                        cell_content += '<br />'
            # 1行目はth、それ以降はtd
            if tr_idx == 0:
                tag_html = th_tag.replace('{content}', cell_content)
                row_content += tag_html
            else:
                if '<ul' in td_tag and '<li>{content}</li>' in td_tag:
                    # 「・」で分割しliタグで囲む（「・」は除去しない）、li内の<br>は除去
                    items = [f'・{item}' if not item.startswith('・') else item for item in re.split(r'・', cell_content) if item.strip()]
                    items = [re.sub(r'<br ?/?>', '', item).strip() for item in items]
                    li_html = ''.join(f'<li>{item}</li>' for item in items)
                    cell_html = td_tag.replace('<li>{content}</li>', li_html)
                    row_content += cell_html
                else:
                    tag_html = td_tag.replace('{content}', cell_content)
                    row_content += tag_html
        row_html = tr_tag.replace('{content}', row_content)
        table_content += row_html
    
    # table_templateの{content}部分にtable_contentを埋め込み
    print(f"【TABLE_CONVERT】table_content: '{table_content}'")
    table_html = table_template.replace('{content}', table_content)
    print(f"【TABLE_CONVERT】最終的なtable_html: '{table_html}'")
    return table_html

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
    
    # 直接パラグラフに罫線属性がある場合
    pBdr = p.find('.//w:pBdr', namespaces)
    if pBdr is not None:
        return True
    
    # 段落内のボックス属性を確認
    shd_elements = p.findall('.//w:shd[@w:fill]', namespaces)
    if shd_elements:
        for shd in shd_elements:
            fill_value = shd.get('{' + namespaces['w'] + '}fill')
            if fill_value and fill_value != 'auto':
                return True
    
    # その他の罫線判定方法を追加
    # 背景色による判定
    bg_elements = p.findall('.//w:shd', namespaces)
    for bg in bg_elements:
        fill = bg.get('{' + namespaces['w'] + '}fill')
        color = bg.get('{' + namespaces['w'] + '}color')
        if fill and fill != 'auto':
            return True
    
    # 段落のスタイル属性を確認
    pPr = p.find('.//w:pPr', namespaces)
    if pPr is not None:
        # スタイル名を確認
        pStyle = pPr.find('.//w:pStyle', namespaces)
        if pStyle is not None:
            style_val = pStyle.get('{' + namespaces['w'] + '}val')
            print(f"【DEBUG】段落スタイル: {style_val}")
            # 罫線に関連するスタイル名をチェック
            if style_val and any(keyword in style_val.lower() for keyword in ['border', 'box', 'frame', 'outline']):
                print("【DEBUG】罫線関連スタイルを検出: True")
                return True
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


def remove_empty_text_tags(html_content):
    """
    空白で終わるテキストタグを削除する
    
    Args:
        html_content (str): HTML文字列
        
    Returns:
        str: 空白テキストが削除されたHTML文字列
    """
    # 空白で終わるpタグを削除するパターン
    # 全角空白（　）または半角空白のみを含むpタグを検出
    empty_p_pattern = re.compile(r'<p[^>]*>\s*[　\s]*</p>', re.MULTILINE)
    
    # 空白で終わるpタグを削除
    html_content = empty_p_pattern.sub('', html_content)
    
    # 連続する改行を整理
    html_content = re.sub(r'\n\s*\n\s*\n', '\n\n', html_content)
    
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
    
    # ulフラグをチェックしてulタグを追加するかどうかを判定
    ul_flag_enabled = UL_FLAGS.get('箱内リンクテキスト（中点）', False)
    if ul_flag_enabled:
        li_content = '\n'.join(clean_items)
        li_content = f'<ul>\n{li_content}\n</ul>'
    else:
        li_content = '\n'.join(clean_items)
    
    # テンプレートから外側のdiv構造を抽出
    div_match = re.search(r'<div[^>]*style="[^"]*"[^>]*>', template)
    if div_match:
        div_start = div_match.group(0)
        # 外側のdiv構造を構築
        result = f"{div_start}\n{li_content}\n</div>"
        return result
    else:
        # divタグが見つからない場合は通常の処理
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
    
    # ルールデータをグローバルに保存（閉じタグ取得用）
    global RULES_DATA
    RULES_DATA = []
    
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
        
        # ルールデータを保存（閉じタグ取得用）
        RULES_DATA.append(rule)
    
    # 見出し1の設定
    if heading_1_rule:
        tag_string = heading_1_rule.get('tag', '')
        before_string = heading_1_rule.get('prefix_text', '').replace('\\n', '\n')
        after_string = heading_1_rule.get('suffix_text', '').replace('\\n', '\n')
        
        template_tag, id_format, pattern_type, text_position = analyze_heading_structure(tag_string)
        
        # サイト設定を更新
        SITE_CONFIGS['webapp_custom']['heading_1'] = {
            'before': before_string,
            'tag': template_tag,
            'after': after_string,
            'id_format': id_format,
            'text_position': text_position,
            'original_tag': tag_string,  # 元のタグ文字列を保存
        }
        
        # HTML_TAGSを更新
        HTML_TAGS['h3_template'] = template_tag
        ID_PATTERNS['heading_1_format'] = id_format
    
    # 見出し2の設定
    if heading_2_rule:
        tag_string = heading_2_rule.get('tag', '')
        before_string = heading_2_rule.get('prefix_text', '').replace('\\n', '\n')
        after_string = heading_2_rule.get('suffix_text', '').replace('\\n', '\n')
        
        template_tag, id_format, pattern_type, text_position = analyze_heading_structure(tag_string)

        
        # サイト設定を更新
        SITE_CONFIGS['webapp_custom']['h4_template'] = template_tag
        SITE_CONFIGS['webapp_custom']['heading_2_before'] = before_string
        SITE_CONFIGS['webapp_custom']['heading_2_after'] = after_string
        SITE_CONFIGS['webapp_custom']['heading_2_text_position'] = text_position
        SITE_CONFIGS['webapp_custom']['heading_2_original_tag'] = tag_string  # 元のタグ文字列を保存
        
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
        else:
            # 中見出しにIDがない場合はデフォルト
            ID_PATTERNS['link_item_format'] = 'heading-{main_number}-{sub_number}'
    
    # テーブルの設定
    if table_rule:
        # 個別のテーブルタグを取得
        table_tag = table_rule.get('table_tag', '')
        tbody_tag = table_rule.get('tbody_tag', '')
        tr_tag = table_rule.get('tr_tag', '')
        th_tag = table_rule.get('th_tag', '')
        td_tag = table_rule.get('td_tag', '')
        
        # HTML_TAGSに設定
        if table_tag:
            HTML_TAGS['table_tag'] = table_tag
        if tbody_tag:
            HTML_TAGS['tbody_tag'] = tbody_tag
        if tr_tag:
            HTML_TAGS['tr_tag'] = tr_tag
            HTML_TAGS['table_row_template'] = tr_tag
        if th_tag:
            HTML_TAGS['th_tag'] = th_tag
            HTML_TAGS['table_cell_th_template'] = th_tag
        if td_tag:
            HTML_TAGS['td_tag'] = td_tag
            HTML_TAGS['table_cell_td_template'] = td_tag
            
        # table_templateとtbody_tagからテーブル全体のテンプレートを構築
        if table_tag and tbody_tag:
            print(f"【TABLE_CONFIG】元のtable_tag: '{table_tag}'")
            print(f"【TABLE_CONFIG】元のtbody_tag: '{tbody_tag}'")
            
            # table_tagから開始タグのみを抽出
            table_start_match = re.match(r'(<table[^>]*>)', table_tag)
            clean_table_start = table_start_match.group(1) if table_start_match else '<table>'
            
            print(f"【TABLE_CONFIG】抽出したclean_table_start: '{clean_table_start}'")
            
            # tbody_tagを正規化（正しい<tbody>{content}</tbody>形式にする）
            clean_tbody_tag = '<tbody>{content}</tbody>'
            
            # 正しいテンプレートを構築
            table_template = clean_table_start + clean_tbody_tag + '</table>'
            print(f"【TABLE_CONFIG】最終テンプレート: '{table_template}'")
            HTML_TAGS['table_template'] = table_template
    
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
        '箱内リンクテキスト': 'div_link_list_template',
        '箱内テキスト（番号）': 'div_ordered_list_template',
        '箱内リンクテキスト（中点）': 'div_link_list_template',
        # 追加: tr, td, th
        'tr': 'table_row_template',
        'td': 'table_cell_td_template',
        'th': 'table_cell_th_template',
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
        
        # ulフラグを設定（テンプレートにulタグが含まれている場合は自動的にON）
        if ul_flag or (tag and '<ul>' in tag):
            UL_FLAGS[section] = True
        
        # olフラグを設定（テンプレートにolタグが含まれている場合は自動的にON）
        if ol_flag or (tag and '<ol>' in tag):
            OL_FLAGS[section] = True
        
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
    # ルールループの最後にUL_FLAGSの内容を出力
    
    # 現在のサイトをwebapp_customに設定
    CURRENT_SITE = 'webapp_custom'

def generate_heading_id_advanced(level, main_number, sub_number=None, single_counter=None, sub_sub_number=None):
    """
    高度な見出しID生成（小見出し対応）
    Args:
        level (int): 見出しレベル（1,2,4）
        main_number (int): 大見出し番号
        sub_number (int): 中見出し番号
        single_counter (int): 単一カウンター
        sub_sub_number (int): 小見出し番号
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
        # フォーマット指定子を確認して適切なパラメータを渡す
        if '{number}' in format_str:
            # 単一数字形式（例：text{number}）
            return format_str.format(number=sub_number)
        else:
            # 複数数字形式（例：heading-{main_number}-{sub_number}）
            return format_str.format(main_number=main_number, sub_number=sub_number)
    elif level == 4:
        # 小見出し: section{main_number}-{sub_number}-{sub_sub_number}
        return f"section{main_number}-{sub_number}-{sub_sub_number}"
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
    
    # 変換設定の確認
    conversion_settings = json_data.get('conversion_settings', [])
    
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
        
        # 高度な解析を実行
        template_tag, id_format, pattern_type = analyze_id_pattern_advanced(tag_string)

        
        # サンプルID生成テスト
        if id_format:
            try:
                if pattern_type == "double":
                    sample_id = id_format.format(main_number=1, sub_number=2)
                elif pattern_type == "single":
                    sample_id = id_format.format(number=5)
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
                break
    
    print("\n=== テスト完了 ===")

def process_bullet_list_items(items, list_template, use_bullet_points=True):
    """
    箱内テキスト（中点）や箱内リンクテキスト（中点）用リスト生成。
    JSONデータの設定項目を参照し、中点除去フラグに基づいて処理する。
    Args:
        items (list): テキスト項目のリスト
        list_template (str): JSONから取得したリストのHTMLテンプレート
        use_bullet_points (bool): 中点除去フラグ（True=除去、False=保持）
    Returns:
        str: 適切なHTMLリスト構造
    """
    print("【ULDEBUG】process_bullet_list_items関数が呼び出されました")
    print(f"【ULDEBUG】items: {items}")
    print(f"【ULDEBUG】list_template: {list_template}")

    if not items:
        return ""

    # ルールから設定項目を優先順位付きで取得
    bullet_rule = None
    link_rule = None
    global rules, global_link_counter
    if 'rules' in globals() and rules:
        # 箱内テキスト（中点）の取得（フォールバック: 箱の枠）
        for section_name in ['箱内テキスト（中点）', '箱の枠']:
            bullet_rule = next((r for r in rules if r.get('active', False) and r.get('section') == section_name), None)
            if bullet_rule:
                print(f"【process_bullet_list】{section_name}ルールを使用（箱内テキスト）")
                break
        
        # 箱内リンクテキスト（中点）の取得（フォールバック: 箱内リンクテキスト → 箱の枠）
        for section_name in ['箱内リンクテキスト（中点）', '箱内リンクテキスト', '箱の枠']:
            link_rule = next((r for r in rules if r.get('active', False) and r.get('section') == section_name), None)
            if link_rule:
                print(f"【process_bullet_list】{section_name}ルールを使用（箱内リンクテキスト）")
                break

    # 先頭が中点かどうかを判定し、適切なルールを選択
    has_bullet_points = any(item.strip().startswith('・') for item in items)
    
    # リンク要素があるかどうかを判定（初期判定のため項目内容のみをチェック）
    has_links = any('<a href=' in item for item in items)
    
    # 適切なルールを選択
    print(f"【ULDEBUG】has_links: {has_links}, link_rule: {link_rule is not None}, bullet_rule: {bullet_rule is not None}")
    if has_links and link_rule:
        current_rule = link_rule
        print("【ULDEBUG】箱内リンクテキスト（中点）ルールを使用")
    elif bullet_rule:
        current_rule = bullet_rule
        print("【ULDEBUG】箱内テキスト（中点）ルールを使用")
    else:
        current_rule = None
        print("【ULDEBUG】デフォルト処理を使用")

    # 前後の文字列を取得
    prefix = current_rule.get('prefix_text', '').replace('\\n', '\n') if current_rule else ''
    suffix = current_rule.get('suffix_text', '').replace('\\n', '\n') if current_rule else ''
    tag = current_rule.get('tag', '') if current_rule else ''
    
    print(f"【ULDEBUG】設定値 - prefix: {repr(prefix)}")
    print(f"【ULDEBUG】設定値 - suffix: {repr(suffix)}")
    print(f"【ULDEBUG】設定値 - tag: {repr(tag)}")
    
    # tagが空の場合はデフォルトテンプレートを使用
    if not tag:
        if has_links:
            tag = HTML_TAGS.get('div_link_list_template', '<li><span style="text-decoration: underline; color: #56a0d6;"><a href="#text1">テキスト</a></span></li>')
        else:
            tag = HTML_TAGS.get('div_list_template', '<li>テキスト</li>')
        print(f"【DEBUG】デフォルトテンプレートを使用: {tag}")

    # 項目を処理
    processed_items = []
    for item in items:
        item = item.strip()
        if not item:
            continue
        # use_bullet_pointsフラグに基づいて中点除去を制御
        if use_bullet_points and item.startswith('・'):
            # 中点除去ONかつ中点がある場合：中点を除去
            item = item.lstrip('・　').strip()
            print(f"【DEBUG】中点除去: {item}")
        # 中点除去OFFの場合は中点をそのまま保持
        processed_items.append(item)

    # tagテンプレートから1行分のテンプレートを抽出
    item_template = tag
    li_match = re.search(r'(<li[\s\S]*?</li>)', tag)
    if li_match:
        item_template = li_match.group(1)

    # hrefの数字部分を昇順にソートするための処理
    print(f"【ULDEBUG】数字置換処理 - has_links: {has_links}, href in template: {'href=' in item_template}")
    if has_links and 'href=' in item_template:
        print(f"【ULDEBUG】元のitem_template: {item_template}")
        # href内の数字を{idx}に置換
        item_template = re.sub(r'(href=["\'].*?)(\d+)(["\'])', r'\1{idx}\3', item_template)
        print(f"【ULDEBUG】置換後のitem_template: {item_template}")
        
        # 各項目にグローバルカウンターを使用してHTMLを生成
        formatted_items = []
        global global_link_counter
        
        print(f"【ULDEBUG】グローバルカウンター取得: {global_link_counter}")
        
        # 現在の大見出し番号を取得（実行時点での番号を記録）
        global major_heading_counter
        
        # 箱内リンクテキスト（中点）の場合は現在の大見出し番号を使用
        if (current_rule and current_rule.get('section') == '箱内リンクテキスト（中点）'):
            current_major = major_heading_counter
            print(f"【process_bullet_list修正】箱内リンクテキスト（中点）で現在の大見出し番号を使用: {current_major}")
        else:
            current_major = major_heading_counter
            print(f"【ULDEBUG】関数実行時の大見出し番号: {current_major}")
        
        # この関数が呼ばれた時点での大見出し番号を記録（クロージャで使用）
        recorded_major_counter = current_major
        
        for local_idx, item in enumerate(processed_items, 1):
            print(f"【ULDEBUG】処理中 - local_idx: {local_idx}, 大見出し: {recorded_major_counter}, item: {item}")
            
            # hrefを見出し番号ベースで置換
            formatted_html = item_template.replace('テキスト', item)
            if '{content}' in formatted_html:
                formatted_html = formatted_html.replace('{content}', item)
            
            # {idx}の置換は一旦スキップして、直接href置換を行う
            if 'href=' in formatted_html:
                def replace_href_with_heading_numbers(match):
                    quote_char = match.group(1)
                    href_content = match.group(2)
                    
                    # hrefのパターンを判定して適切な番号を使用
                    # href内の数字の塊の数で大見出し番号の有無を判定
                    numbers = re.findall(r'\d+', href_content)
                    is_no_heading_number_site = len(numbers) <= 1
                    
                    if is_no_heading_number_site:
                        # 大見出し番号がないサイト（text1, text2等）の場合はグローバルカウンターを使用
                        global global_link_counter
                        new_href_content = re.sub(r'\d+', str(global_link_counter), href_content, count=1)
                        global_link_counter += 1
                        print(f"【process_bullet_list】数字の塊1つ（大見出し番号なし）でグローバルカウンター使用: {global_link_counter-1} → 次回{global_link_counter}")
                    elif '-' in href_content and href_content.count('-') >= 2:
                        parts = href_content.split('-')
                        if len(parts) >= 3:
                            parts[-2] = str(recorded_major_counter)  # 記録された大見出し番号
                            parts[-1] = str(local_idx)              # 中見出し番号
                            new_href_content = '-'.join(parts)
                        else:
                            new_href_content = href_content
                    else:
                        # 数字の塊が2つ以上の場合は従来の処理
                        if len(numbers) >= 2:
                            new_href_content = re.sub(r'\d+', str(recorded_major_counter), href_content, count=1)
                            new_href_content = re.sub(r'\d+', str(local_idx), new_href_content, count=1)
                        else:
                            # 数字が1つしかない場合は、ローカルインデックスを使用
                            new_href_content = re.sub(r'\d+', str(local_idx), href_content, count=1)
                    
                    return f'href={quote_char}{new_href_content}{quote_char}'
                
                formatted_html = re.sub(r'href=(["\'])([^"\']*)\1', replace_href_with_heading_numbers, formatted_html)
            
            print(f"【ULDEBUG】formatted_html: {formatted_html}")
            formatted_items.append(formatted_html)
    else:
        # 通常のテキスト処理
        formatted_items = []
        for item in processed_items:
            formatted_html = item_template.replace('テキスト', item)
            if '{content}' in formatted_html:
                formatted_html = formatted_html.replace('{content}', item)
            formatted_items.append(formatted_html)

    # 最終的なHTMLを構築
    print(f"【ULDEBUG】li_match: {li_match is not None}")
    print(f"【ULDEBUG】formatted_items: {formatted_items}")
    
    if li_match:
        # li要素がある場合は、テンプレートの構造を保持して内容を置換
        content = '\n'.join(formatted_items)
        print(f"【ULDEBUG】結合されたcontent: {repr(content)}")
        # tagテンプレート内のli要素部分を置換
        result = re.sub(r'<li[\s\S]*?</li>', content, tag, count=1)
        print(f"【ULDEBUG】置換後のresult: {repr(result)}")
    else:
        # li要素がない場合は単純に結合
        result = '\n'.join(formatted_items)
        print(f"【ULDEBUG】単純結合のresult: {repr(result)}")

    # 前後の文字列を付与
    final_result = f"{prefix}{result}{suffix}"
    print(f"【ULDEBUG】最終結果: {repr(final_result)}")
    return final_result

def generate_box_link_list_from_items(items, rule, major_heading_number, use_bullet_points=True, headings=None):
    """
    蓄積された箱内リンクテキストをまとめて処理してHTMLを生成する
    Args:
        items (list): 蓄積されたテキスト項目のリスト
        rule (dict): 適用するルール設定
        major_heading_number (int): 大見出し番号
        use_bullet_points (bool): 中点除去フラグ
        headings (list): 見出しのリスト（ID参照用）
    Returns:
        str: 生成されたHTML
    """
    """
    蓄積された箱内リンクテキストをまとめて処理してHTMLを生成する
    Args:
        items (list): 蓄積されたテキスト項目のリスト
        rule (dict): 適用するルール設定
        major_heading_number (int): 大見出し番号
        use_bullet_points (bool): 中点除去フラグ
    Returns:
        str: 生成されたHTML
    """
    if not items or not rule:
        return ""
    
    print(f"【まとめて処理】箱内リンクテキスト {len(items)}項目をまとめて処理開始")
    
    prefix = rule.get('prefix_text', '').replace('\\n', '\n')
    suffix = rule.get('suffix_text', '').replace('\\n', '\n')
    tag = rule.get('tag', '')
    
    # 1行分のテンプレート
    item_template = tag
    
    # hrefの数字部分を昇順にする
    formatted_items = []
    print(f"【まとめて処理】item_template: {item_template}")
    print(f"【まとめて処理】使用する大見出し番号: {major_heading_number}")
    
    for local_idx, line in enumerate(items, 1):
        print(f"【まとめて処理】処理中 - local_idx: {local_idx}, line: {line}")
        
        # テキストを置換
        link_html = item_template.replace('テキスト', line)
        if '{content}' in link_html:
            link_html = link_html.replace('{content}', line)
        
        # hrefの数字を昇順にする（href属性内のみ）
        if 'href=' in link_html:
            print(f"【まとめて処理】href属性を処理、local_idx={local_idx}")
            
            def replace_href_number(match):
                quote_char = match.group(1)
                href_content = match.group(2)
                
                # 渡されたmajor_heading_numberをそのまま使用
                current_major_number = major_heading_number
                
                print(f"【まとめて処理】href置換 - href: {href_content}, 使用する大見出し: {current_major_number}, local_idx: {local_idx}")
                
                # 動的プレフィックス処理
                # ルールのtagからhrefパターンを判定
                rule_tag = rule.get('tag', '') if rule else ''
                has_hyphen_pattern = bool(re.search(r'href="[^"]*-\d+-\d+', rule_tag))
                
                if has_hyphen_pattern:
                    # ハイフン有りパターン（#heading-1-1）
                    regex_match = re.match(r'^#[a-zA-Z]+-\d+-\d+', href_content)
                    extract_pattern = r'^(#[a-zA-Z]+)-\d+-\d+'
                    format_template = "{prefix_part}-{major}-{local}"
                else:
                    # ハイフン無しパターン（#rtoc1-1）
                    regex_match = re.match(r'^#[a-zA-Z]+\d+-\d+', href_content)
                    extract_pattern = r'^(#[a-zA-Z]+)\d+-\d+'
                    format_template = "{prefix_part}{major}-{local}"
                
                print(f"【デバッグ】タグパターン解析: has_hyphen_pattern={has_hyphen_pattern}, rule_tag={rule_tag}")
                print(f"【デバッグ】正規表現マッチ結果: {href_content} → {regex_match is not None}")
                
                if regex_match:
                    # マッチした場合は、文字列部分を抽出して番号を置換
                    match_prefix = re.match(extract_pattern, href_content)
                    if match_prefix:
                        prefix_part = match_prefix.group(1)  # #rtoc, #heading等の文字列部分
                        if has_hyphen_pattern:
                            new_href_content = f"{prefix_part}-{current_major_number}-{local_idx}"
                        else:
                            new_href_content = f"{prefix_part}{current_major_number}-{local_idx}"
                        print(f"【まとめて処理】動的プレフィックス: {prefix_part} → {new_href_content}")
                    else:
                        new_href_content = href_content
                else:
                    # 罫線内の各リンクに対して、次の中見出し番号を使用
                    global cumulative_heading_counter
                    # 最初のリンクの場合のみ、次の中見出し番号を計算
                    if local_idx == 1:
                        base_number = cumulative_heading_counter
                    # 各リンクに連番を割り当て
                    current_number = base_number + local_idx - 1
                    # 最後のリンクの場合、累積カウンターを更新
                    if local_idx == len(items):
                        cumulative_heading_counter = current_number
                    # href属性の形式を修正（#を確実に付ける）
                    new_href_content = f"#text{current_number}"
                    print(f"【まとめて処理】通常の番号置換: {href_content} → {new_href_content} (開始番号{base_number} + {local_idx - 1} = {current_number})")
                
                return f'href={quote_char}{new_href_content}{quote_char}'
            
            link_html = re.sub(r'href=(["\'])([^"\']*)\1', replace_href_number, link_html)
        
        # 箱内リンクテキスト系の処理を分岐
        if rule.get('section') == '箱内リンクテキスト（中点）':
            # 箱内リンクテキスト（中点）の場合は、<li>タグを保持
            # link_htmlはそのまま使用（<li><a href="...">...</a></li>の形式を維持）
            pass
        elif rule.get('section') == '箱内リンクテキスト':
            # 箱内リンクテキスト（通常）の場合は、<a>タグのみを抽出
            a_match = re.search(r'(<a[^>]*>.*?</a>)', link_html)
            if a_match:
                link_html = a_match.group(1)
                if local_idx < len(items):  # 最後の要素以外には<br />を追加
                    link_html += '<br />'
        
        formatted_items.append(link_html)
        print(f"【まとめて処理】local_idx={local_idx}のアイテム完了: {link_html}")
    
    # 最終的なHTMLを構築
    if rule.get('section') == '箱内リンクテキスト':
        # 箱内リンクテキスト（通常）の場合は、<br />で区切られているので改行なしで結合
        content = '\n'.join(formatted_items)
    else:
        # 箱内リンクテキスト（中点）やその他の場合は通常の改行で結合
        content = '\n'.join(formatted_items)
    
    final_html = f"{prefix}{content}{suffix}"
    print(f"【まとめて処理】最終的なHTML: {final_html}")
    return final_html

def process_numbered_list_items(items, list_template, use_bullet_points=True):
    """
    「数字.」から始まるテキスト項目を動的なHTMLリスト構造に変換する
    箱内テキスト（番号）と箱内リンクテキスト（番号）に対応
    
    Args:
        items (list): 「数字.」から始まるテキスト項目のリスト
        list_template (str): JSONから取得した番号付きリストのHTMLテンプレート
    
    Returns:
        str: 適切なHTMLリスト構造
    """
    if not items:
        return ""
    
    # ルールから設定項目を優先順位付きで取得
    numbered_rule = None
    numbered_link_rule = None
    global rules
    if 'rules' in globals() and rules:
        # 箱内テキスト（番号）の取得（フォールバック: 箱の枠）
        for section_name in ['箱内テキスト（番号）', '箱の枠']:
            numbered_rule = next((r for r in rules if r.get('active', False) and r.get('section') == section_name), None)
            if numbered_rule:
                print(f"【process_numbered_list】{section_name}ルールを使用（箱内テキスト番号）")
                break
        
        # 箱内リンクテキスト（番号）の取得（フォールバック: 箱内リンクテキスト → 箱の枠）
        for section_name in ['箱内リンクテキスト（番号）', '箱内リンクテキスト', '箱の枠']:
            numbered_link_rule = next((r for r in rules if r.get('active', False) and r.get('section') == section_name), None)
            if numbered_link_rule:
                print(f"【process_numbered_list】{section_name}ルールを使用（箱内リンクテキスト番号）")
                break

    # リンク要素があるかどうかを判定（初期判定のため項目内容のみをチェック）
    has_links = any('<a href=' in item for item in items)
    
    # 適切なルールを選択
    if has_links and numbered_link_rule:
        current_rule = numbered_link_rule
        print("【DEBUG】箱内リンクテキスト（番号）ルールを使用")
    elif numbered_rule:
        current_rule = numbered_rule
        print("【DEBUG】箱内テキスト（番号）ルールを使用")
    else:
        current_rule = None
        print("【DEBUG】デフォルト処理を使用")

    # 前後の文字列を取得
    prefix = current_rule.get('prefix_text', '').replace('\\n', '\n') if current_rule else ''
    suffix = current_rule.get('suffix_text', '').replace('\\n', '\n') if current_rule else ''
    tag = current_rule.get('tag', '') if current_rule else ''
    
    # tagが空の場合はデフォルトテンプレートを使用
    if not tag:
        if has_links:
            tag = HTML_TAGS.get('div_link_list_template', '<li><span style="text-decoration: underline; color: #56a0d6;"><a href="#text1">テキスト</a></span></li>')
        else:
            tag = HTML_TAGS.get('div_ordered_list_template', '<li>テキスト</li>')
        print(f"【DEBUG】デフォルトテンプレートを使用: {tag}")

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
    has_content_placeholders = '{content}' in tag or 'テキスト' in tag
    
    if has_content_placeholders:
        # ol/li形式の場合
        if '<ol>' in tag and '<li>' in tag:
            # 複数のテンプレート行がある場合は実際のアイテム数に調整
            li_matches = re.findall(r'<li[^>]*>.*?</li>', tag, re.DOTALL)
            
            if li_matches and len(li_matches) > 1:
                # 複数のliタグがある場合、最初のliをテンプレートとして使用
                first_li = li_matches[0]
                li_content_match = re.search(r'<li[^>]*>(.*?)</li>', first_li, re.DOTALL)
                if li_content_match:
                    li_content = li_content_match.group(1).strip()
                    
                    # 外側の構造を抽出
                    outer_start = tag.split('<ol')[0] if '<ol' in tag else ''
                    ol_start_match = re.search(r'<ol[^>]*>', tag)
                    ol_start = ol_start_match.group(0) if ol_start_match else '<ol>'
                    outer_end_match = re.search(r'</ol>(.*?)$', tag, re.DOTALL)
                    outer_end = outer_end_match.group(1) if outer_end_match else ''
                    
                    # リスト項目を生成（hrefの数字をソート）
                    list_content = ""
                    for idx, clean_item in enumerate(clean_items, 1):
                        # 既にliタグが付いている場合はそのまま使用
                        if clean_item.startswith('<li>') and clean_item.endswith('</li>'):
                            formatted_li = clean_item
                        # 既に<a>タグが含まれている場合は、直接<li>で囲む
                        elif '<a href=' in clean_item:
                            formatted_li = f'<li>{clean_item}</li>'
                        elif '{content}' in li_content:
                            # hrefの数字を昇順にする
                            item_content = li_content.replace("{content}", clean_item)
                            if has_links and 'href=' in item_content:
                                item_content = re.sub(r'(href=["\'].*?)(\d+)(["\'])', rf'\g<1>{idx}\g<3>', item_content)
                            formatted_li = f'<li>{item_content}</li>'
                        elif 'テキスト' in li_content:
                            # hrefの数字を昇順にする
                            item_content = li_content.replace("テキスト", clean_item)
                            if has_links and 'href=' in item_content:
                                item_content = re.sub(r'(href=["\'].*?)(\d+)(["\'])', rf'\g<1>{idx}\g<3>', item_content)
                            formatted_li = f'<li>{item_content}</li>'
                        else:
                            formatted_li = f'<li>{clean_item}</li>'
                        list_content += "\t" + formatted_li + "\n"
                    
                    result = f"{outer_start}{ol_start}\n{list_content}</ol>{outer_end}"
                    return result
            
            # 単一のliタグまたは通常の処理
            # ol開始タグと終了タグを抽出
            ol_start_match = re.search(r'<ol[^>]*>', tag)
            ol_start = ol_start_match.group(0) if ol_start_match else '<ol>'
            
            # 外側のdiv/dl構造を抽出
            outer_start = tag.split('<ol')[0] if '<ol' in tag else ''
            outer_end_match = re.search(r'</ol>(.*?)$', tag, re.DOTALL)
            outer_end = outer_end_match.group(1) if outer_end_match else ''
            
            # li要素のテンプレートを抽出
            li_pattern = re.search(r'<li[^>]*>(.*?)</li>', tag, re.DOTALL)
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
            
            # リスト項目を生成（hrefの数字をソート）
            list_content = ""
            for idx, clean_item in enumerate(clean_items, 1):
                # 既にliタグが付いている場合はそのまま使用
                if clean_item.startswith('<li>') and clean_item.endswith('</li>'):
                    list_content += "\t" + clean_item + "\n"
                # 既に<a>タグが含まれている場合は、直接<li>で囲む
                elif '<a href=' in clean_item:
                    list_content += "\t" + f'<li>{clean_item}</li>' + "\n"
                else:
                    # hrefの数字を昇順にする
                    item_content = li_template.format(content=clean_item)
                    if has_links and 'href=' in item_content:
                        item_content = re.sub(r'(href=["\'].*?)(\d+)(["\'])', rf'\g<1>{idx}\g<3>', item_content)
                    list_content += "\t" + item_content + "\n"
            
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
            
            # 前後の文字列を付与
            return f"{prefix}{result}{suffix}"
        
        # span形式の場合（サイト１のような形式）
        elif '<span' in tag and not ('<ol>' in tag or '<p>' in tag or '<dl>' in tag):
            # span要素のテンプレートを解析
            span_pattern = re.search(r'<span[^>]*>(.*?)</span>', tag, re.DOTALL)
            if span_pattern:
                span_content = span_pattern.group(1)
                
                # 外側のdiv構造を抽出
                outer_start_match = re.search(r'^(.*?)<span', tag, re.DOTALL)
                outer_start = outer_start_match.group(1) if outer_start_match else ''
                outer_end_match = re.search(r'</span>(.*?)$', tag, re.DOTALL)
                outer_end = outer_end_match.group(1) if outer_end_match else ''
                
                # span要素のテンプレート
                span_template_match = re.search(r'<span[^>]*>', tag)
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
                return f"{prefix}{outer_start}{content}{outer_end}{suffix}"
        
        # p形式の場合（サイト２のような形式）
        elif '<p>' in tag and not ('<ol>' in tag or '<dl>' in tag):
            # p要素のテンプレートを解析
            p_pattern = re.search(r'<p[^>]*>(.*?)</p>', tag, re.DOTALL)
            if p_pattern:
                p_content = p_pattern.group(1)
                
                # 外側のdiv構造を抽出
                outer_start_match = re.search(r'^(.*?)<p', tag, re.DOTALL)
                outer_start = outer_start_match.group(1) if outer_start_match else ''
                outer_end_match = re.search(r'</p>(.*?)$', tag, re.DOTALL)
                outer_end = outer_end_match.group(1) if outer_end_match else ''
                
                # p要素のテンプレート
                p_template_match = re.search(r'<p[^>]*>', tag)
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
                return f"{prefix}{outer_start}{content}{outer_end}{suffix}"
        
        # dl/dd形式の場合（サイト３のような形式）
        elif '<dl>' in tag and '<dd>' in tag:
            # dl構造のテンプレートを解析
            dd_pattern = re.search(r'<dd[^>]*[^>]*>(.*?)</dd>', tag, re.DOTALL)
            if dd_pattern:
                dd_content = dd_pattern.group(1)
                
                # 「数字.テキスト<br>」の繰り返し形式の場合
                if '<br>' in dd_content or '<br />' in dd_content:
                    # dl開始部分を抽出
                    dl_start = tag.split('<dd')[0] + '<dd' + tag.split('<dd')[1].split('>')[0] + '>'
                    dl_end = '</dd>' + tag.split('</dd>')[-1] if '</dd>' in tag else '</dd>'
                    
                    # リスト項目を生成（数字.付きで<br>区切り）
                    formatted_items = []
                    for i, clean_item in enumerate(clean_items, 1):
                        formatted_items.append(f'{i}.{clean_item}')
                    
                    content = '<br>\n\t\t'.join(formatted_items)
                    return f"{prefix}{dl_start}\n\t\t{content}\n\t{dl_end}{suffix}"
            
        # その他のカスタム形式
        else:
            # 一般的な処理（divのみなど）
            # {content}またはテキストを適切に置換
            result = tag
            
            # 全ての項目を番号付きで改行で結合
            numbered_items = []
            for i, clean_item in enumerate(clean_items, 1):
                numbered_items.append(f'{i}.{clean_item}')
            combined_content = '\n'.join(numbered_items)
            
            if '{content}' in result:
                result = result.replace('{content}', combined_content)
            elif 'テキスト' in result:
                result = result.replace('テキスト', combined_content)
            
            return f"{prefix}{result}{suffix}"
    else:
        # プレースホルダーがない場合は、項目をそのまま結合
        all_items = '\n'.join(items)
        return f"{prefix}<div>{all_items}</div>{suffix}"



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
        flag=0
        
        # HTMLタグが含まれている場合は処理をスキップ（安全のため）
        if '<' in content and '>' in content:
            original_content = content
            
            if '。<strong>' in content or '。<span' in content or '。</strong>' in content or '。</span>' in content:
                content = content.replace('。<strong>', '。</p><p><strong>').replace('</strong><strong>', '').replace('。</strong></span>', '。</strong></span></p><p>').replace('。<span', '。</p><p><span').replace('。</span>', '。</span></p><p>').replace('<p></p>','')
                flag=1
            if ('。<strong>' in content or '。<span' in content or '。</strong>' in content or '。</span>' in content) and ('。</strong></span>' not in content):
                content = content.replace('。</strong>', '。</strong></p><p>')
                flag=1
            if flag==0:
                content = content.replace('。','。</p><p>').replace('<p></p>','')
            # 修正されたコンテンツをpタグで囲んで返す
            if content == '':
                return ''
            result = f"{p_start}{content}{p_end}"
            result = result.replace('<p></p>','')
            return result
        
        # 句点で分割
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
        
        # 分割された文が1つ以下の場合は元のpタグをそのまま返す
        if len(clean_sentences) <= 1:
            return match.group(0)
        
        # 複数の文がある場合、各文をpタグで囲む
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
    processed_html = p_pattern.sub(split_p_content, html_content)
    
    return processed_html

def analyze_heading_structure(tag_string):
    """
    HTMLタグを解析して、テキスト部分以外の構造を保持する
    
    Args:
        tag_string (str): HTMLタグ文字列
    
    Returns:
        tuple: (template_tag, id_format, pattern_type, text_position)
               text_position: テキストが挿入される位置の情報
    """
    # 複数の数字を含むidパターン（例：heading-1-1）
    double_pattern = re.compile(r'id\s*=\s*["\']([^"\']*?)(\d+)([^"\']*?)(\d+)([^"\']*?)["\']')
    # 単一の数字を含むidパターン（例：text7）
    single_pattern = re.compile(r'id\s*=\s*["\']([^"\']*?)(\d+)([^"\']*?)["\']')
    
    template_tag = tag_string
    id_format = ""
    pattern_type = "none"
    text_position = "end"  # デフォルトは終了タグの直前
    
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
    
    # テキスト位置の決定と構造の保持
    # 完全なタグ（開始〜終了）の場合
    if '</h' in template_tag or '</div' in template_tag:
        if '>' in template_tag and '</' in template_tag:
            parts = template_tag.split('>', 1)
            if len(parts) == 2:
                start_part = parts[0] + '>'
                end_part = parts[1]
                if '</' in end_part:
                    content_and_end = end_part.split('</', 1)
                    # 既存のコンテンツ部分を{content}に置換
                    template_tag = start_part + '{content}</' + content_and_end[1]
                    text_position = "before_closing"
    else:
        # 開始タグのみの場合、{content}と終了タグを追加
        if template_tag.startswith('<'):
            tag_name_match = re.match(r'<(\w+)', template_tag)
            if tag_name_match:
                tag_name = tag_name_match.group(1)
                template_tag = template_tag.rstrip('>') + '>{content}</' + tag_name + '>'
                text_position = "before_closing"
    
    return template_tag, id_format, pattern_type, text_position

def extract_text_from_heading_tag(tag_string):
    """
    HTMLタグから「テキスト」部分を抽出する
    
    Args:
        tag_string (str): HTMLタグ文字列
    
    Returns:
        str: 抽出されたテキスト部分
    """
    # 開始タグと終了タグの間のコンテンツを抽出
    if '>' in tag_string and '</' in tag_string:
        parts = tag_string.split('>', 1)
        if len(parts) == 2:
            content_part = parts[1]
            if '</' in content_part:
                text_content = content_part.split('</', 1)[0]
                return text_content.strip()
    
    return ""

def replace_text_in_heading_tag(tag_string, new_text):
    """
    HTMLタグ内の「テキスト」部分を新しいテキストに置換する
    
    Args:
        tag_string (str): 元のHTMLタグ文字列
        new_text (str): 新しいテキスト
    
    Returns:
        str: テキストが置換されたHTMLタグ
    """
    # 開始タグと終了タグの間のコンテンツを置換
    if '>' in tag_string and '</' in tag_string:
        parts = tag_string.split('>', 1)
        if len(parts) == 2:
            start_part = parts[0] + '>'
            end_part = parts[1]
            if '</' in end_part:
                content_and_end = end_part.split('</', 1)
                if len(content_and_end) == 2:
                    return start_part + new_text + '</' + content_and_end[1]
    
    return tag_string

def replace_text_in_html_tag(tag_string, new_text):
    """
    HTMLタグ内の「テキスト」部分を新しいテキストに置換する
    より確実な方法: 最後のテキスト部分のみを置換
    
    Args:
        tag_string (str): 元のHTMLタグ文字列
        new_text (str): 新しいテキスト
    
    Returns:
        str: テキストが置換されたHTMLタグ
    """
    # 開始タグと終了タグの間のコンテンツを正規表現で置換
    # 例: <h2 class="..." id="...">テキスト</h2> の「テキスト」部分を置換
    
    # パターン1: 完全なタグ（開始タグ + コンテンツ + 終了タグ）
    # より正確なパターン: 開始タグから終了タグまでを正確にマッチ
    pattern1 = r'(<[^>]+>)(.*?)(</[^>]+>)'
    match1 = re.search(pattern1, tag_string, re.DOTALL)
    if match1:
        start_tag = match1.group(1)
        content = match1.group(2)
        end_tag = match1.group(3)
        # 開始タグのタグ名と終了タグのタグ名が一致するかチェック
        start_tag_name = re.match(r'<(\w+)', start_tag)
        end_tag_name = re.match(r'</(\w+)', end_tag)
        if start_tag_name and end_tag_name and start_tag_name.group(1) == end_tag_name.group(1):
            return start_tag + new_text + end_tag
    
    # パターン2: 自己終了タグでない場合の開始タグのみ
    pattern2 = r'(<[^>]+>)(.*?)$'
    match2 = re.search(pattern2, tag_string, re.DOTALL)
    if match2:
        start_tag = match2.group(1)
        content = match2.group(2)
        # タグ名を抽出して終了タグを作成
        tag_name_match = re.match(r'<(\w+)', start_tag)
        if tag_name_match:
            tag_name = tag_name_match.group(1)
            return start_tag + new_text + f'</{tag_name}>'
    
    return tag_string

def replace_last_text_in_html_tag(tag_string, new_text):
    """
    HTMLタグ内の最後のテキスト部分のみを新しいテキストに置換する
    より確実な方法
    
    Args:
        tag_string (str): 元のHTMLタグ文字列
        new_text (str): 新しいテキスト
    
    Returns:
        str: テキストが置換されたHTMLタグ
    """
    # 開始タグと終了タグの間のコンテンツを正規表現で置換
    # 例: <h2 class="..." id="..."><span>...</span>テキスト</h2> の「テキスト」部分を置換
    
    # パターン: 開始タグから終了タグまでを正確にマッチ
    pattern = r'(<[^>]+>)(.*?)(</[^>]+>)'
    match = re.search(pattern, tag_string, re.DOTALL)
    if match:
        start_tag = match.group(1)
        content = match.group(2)
        end_tag = match.group(3)
        
        # 開始タグのタグ名と終了タグのタグ名が一致するかチェック
        start_tag_name = re.match(r'<(\w+)', start_tag)
        end_tag_name = re.match(r'</(\w+)', end_tag)
        if start_tag_name and end_tag_name and start_tag_name.group(1) == end_tag_name.group(1):
            # コンテンツ部分で最後のテキストを探す
            # 最後のテキスト部分（タグで囲まれていない部分）を置換
            # 正規表現で最後のテキスト部分を特定
            last_text_pattern = r'(.*?)([^<>]+)$'
            last_text_match = re.search(last_text_pattern, content, re.DOTALL)
            if last_text_match:
                before_text = last_text_match.group(1)
                last_text = last_text_match.group(2)
                # 最後のテキスト部分を新しいテキストに置換
                new_content = before_text + new_text
                return start_tag + new_content + end_tag
            else:
                # 最後のテキストが見つからない場合は、コンテンツ全体を置換
                return start_tag + new_text + end_tag
    
    return tag_string

def replace_text_in_heading_structure(tag_string, new_text):
    """
    HTMLタグ内の「テキスト」部分を実際の見出しテキストに置換する
    より確実な方法
    
    Args:
        tag_string (str): 元のHTMLタグ文字列
        new_text (str): 新しいテキスト
    
    Returns:
        str: テキストが置換されたHTMLタグ
    """
    # 開始タグと終了タグの間のコンテンツを正規表現で置換
    # 例: <h2 class="..." id="..."><span>...</span>テキスト</h2> の「テキスト」部分を置換
    
    # より正確なパターン: 最初の開始タグから最後の終了タグまでをマッチ
    # タグ名を抽出して、対応する終了タグを探す
    tag_name_match = re.match(r'<(\w+)', tag_string)
    if not tag_name_match:
        return tag_string
    
    tag_name = tag_name_match.group(1)
    
    # 開始タグの終了位置を探す
    start_tag_end = tag_string.find('>')
    if start_tag_end == -1:
        return tag_string
    
    start_tag = tag_string[:start_tag_end + 1]
    remaining_content = tag_string[start_tag_end + 1:]
    
    # 対応する終了タグを探す
    end_tag_pattern = f'</{tag_name}>'
    end_tag_pos = remaining_content.rfind(end_tag_pattern)
    if end_tag_pos == -1:
        return tag_string
    
    content = remaining_content[:end_tag_pos]
    end_tag = remaining_content[end_tag_pos:]
    
    # コンテンツ部分で「テキスト」を探して置換
    if 'テキスト' in content:
        # 最後の「テキスト」のみを置換
        # より簡単な方法: 最後の「テキスト」を探して置換
        parts = content.split('テキスト')
        if len(parts) > 1:
            # 最後の部分を除いて結合し、新しいテキストを追加
            new_content = 'テキスト'.join(parts[:-1]) + new_text + parts[-1]
            return start_tag + new_content + end_tag
    else:
        # 「テキスト」が見つからない場合は、最後のテキスト部分を置換
        # 最後のテキスト部分（タグで囲まれていない部分）を探す
        last_text_pattern = r'(.*?)([^<>]+)$'
        last_text_match = re.search(last_text_pattern, content, re.DOTALL)
        if last_text_match:
            before_text = last_text_match.group(1)
            last_text = last_text_match.group(2)
            # 最後のテキスト部分を新しいテキストに置換
            new_content = before_text + new_text
            return start_tag + new_content + end_tag
        else:
            # 最後のテキストが見つからない場合は、コンテンツ全体を置換
            return start_tag + new_text + end_tag

def generate_heading_html_simple(level, heading_id, text_content, heading_number=None, sub_number=None, sub_sub_number=None):
    """
    シンプルな見出しHTML生成（元のタグ構造を保持）
    """
    site_config = get_site_config()
    if level == 1:
        heading_config = site_config['heading_1']
        original_tag = heading_config.get('original_tag', '')
        before = heading_config['before']
        after = heading_config['after']
        if original_tag:
            formatted_tag = replace_text_in_heading_structure(original_tag, text_content)
            if heading_id:
                if 'id=' in formatted_tag:
                    formatted_tag = re.sub(r'id\s*=\s*["\'][^"\']*["\']', f'id="{heading_id}"', formatted_tag)
                else:
                    tag_name_match = re.match(r'<(\w+)', formatted_tag)
                    if tag_name_match:
                        tag_name = tag_name_match.group(1)
                        formatted_tag = formatted_tag.replace(f'<{tag_name}', f'<{tag_name} id="{heading_id}"')
        else:
            template = heading_config['tag']
            if '{id}' in template and heading_id:
                formatted_tag = template.format(id=heading_id, content=text_content)
            else:
                formatted_tag = template.format(content=text_content)
        return before + formatted_tag + after
    elif level == 2:
        original_tag = site_config.get('heading_2_original_tag', '')
        before = site_config.get('heading_2_before', '')
        after = site_config.get('heading_2_after', '')
        if original_tag:
            formatted_tag = replace_text_in_heading_structure(original_tag, text_content)
            if heading_id:
                if 'id=' in formatted_tag:
                    formatted_tag = re.sub(r'id\s*=\s*["\'][^"\']*["\']', f'id="{heading_id}"', formatted_tag)
                else:
                    tag_name_match = re.match(r'<(\w+)', formatted_tag)
                    if tag_name_match:
                        tag_name = tag_name_match.group(1)
                        formatted_tag = formatted_tag.replace(f'<{tag_name}', f'<{tag_name} id="{heading_id}"')
        else:
            template = site_config['h4_template']
            if '{id}' in template and heading_id:
                formatted_tag = template.format(id=heading_id, content=text_content)
            else:
                formatted_tag = template.format(content=text_content)
        return before + formatted_tag + after
    elif level == 4:
        # 小見出し用: 固定テンプレート
        if heading_id:
            return f'<h4 class="zm__text-body __basic" style="color: #2299e1;font-weight: 700;font-size: 1.1em;" id="{heading_id}">{text_content}</h4>'
        else:
            return f'<h4 class="zm__text-body __basic" style="color: #2299e1;font-weight: 700;font-size: 1.1em;">{text_content}</h4>'
    return text_content

def replace_variables_in_html(html_content, variable_values):
    """
    HTMLコンテンツ内の{変数名}をvariable_valuesの値で置換する
    
    Args:
        html_content (str): 置換対象のHTMLコンテンツ
        variable_values (dict): 変数名と値の辞書
        
    Returns:
        str: 変数が置換されたHTMLコンテンツ
    """
    if not variable_values:
        return html_content
    
    # {変数名}のパターンを検索して置換
    pattern = r'\{([^}]+)\}'
    
    def replace_match(match):
        variable_name = match.group(1)
        if variable_name in variable_values:
            return str(variable_values[variable_name])
        else:
            # 変数が見つからない場合は元の文字列をそのまま返す
            return match.group(0)
    
    return re.sub(pattern, replace_match, html_content)

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