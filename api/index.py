from flask import Flask, jsonify, request, render_template, send_file
import os
import sys
import openpyxl
import requests
import io
import tempfile
from urllib.parse import quote
import re
from datetime import datetime

# パスを追加
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

app = Flask(__name__, template_folder='../templates')
app.secret_key = os.environ.get('SECRET_KEY', 'excel-translator-secret-key')

def should_translate_cell(cell_value):
    """セルの内容を分析して翻訳が必要かどうかを判定"""
    if not cell_value:
        return False
    
    # 文字列以外は翻訳しない
    if not isinstance(cell_value, str):
        return False
    
    # 空白文字のみは翻訳しない
    if not cell_value.strip():
        return False
    
    # 数値のみの場合は翻訳しない
    if re.match(r'^[\d\s,.\-+%$€¥]+$', cell_value.strip()):
        return False
    
    # 日付形式の場合は翻訳しない
    date_patterns = [
        r'^\d{4}[-/]\d{1,2}[-/]\d{1,2}$',  # 2023-12-31, 2023/12/31
        r'^\d{1,2}[-/]\d{1,2}[-/]\d{4}$',  # 31-12-2023, 31/12/2023
        r'^\d{4}年\d{1,2}月\d{1,2}日$',     # 2023年12月31日
    ]
    
    for pattern in date_patterns:
        if re.match(pattern, cell_value.strip()):
            return False
    
    # 数式の場合は翻訳しない
    if cell_value.startswith('='):
        return False
    
    # URLの場合は翻訳しない
    if re.match(r'^https?://', cell_value.strip()):
        return False
    
    # メールアドレスの場合は翻訳しない
    if re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', cell_value.strip()):
        return False
    
    # 長すぎる場合は翻訳しない（API制限回避）
    if len(cell_value) > 5000:
        return False
    
    # 短すぎる場合（1文字）で日本語/中国語/韓国語でない場合は翻訳しない
    if len(cell_value.strip()) == 1:
        if not re.match(r'[ひらがなカタカナ漢字가-힣]', cell_value):
            return False
    
    return True

def generate_context_from_headers(sheet, cell_row, cell_col):
    """ヘッダー情報から文脈を生成"""
    context_parts = []
    
    # 同じ行の左側のセルから文脈を取得（見出し）
    for col in range(max(1, cell_col - 3), cell_col):
        if col < cell_col:
            header_cell = sheet.cell(row=cell_row, column=col)
            if header_cell.value and isinstance(header_cell.value, str):
                context_parts.append(header_cell.value)
    
    # 同じ列の上側のセルから文脈を取得（カラムヘッダー）
    for row in range(max(1, cell_row - 3), cell_row):
        if row < cell_row:
            header_cell = sheet.cell(row=row, column=cell_col)
            if header_cell.value and isinstance(header_cell.value, str):
                context_parts.append(header_cell.value)
    
    return ' '.join(context_parts[:5])  # 最大5つの要素で文脈を作成

def analyze_sheet_structure(sheet):
    """シート構造を分析して翻訳単位を決定"""
    # シートの全セルを取得
    all_cells = []
    for row in sheet.iter_rows():
        for cell in row:
            if cell.value is not None:
                all_cells.append({
                    'row': cell.row,
                    'column': cell.column,
                    'value': cell.value,
                    'coordinate': cell.coordinate
                })
    
    # ヘッダー行を特定（最初の数行でテキストが多い行）
    header_rows = []
    for row_num in range(1, min(6, sheet.max_row + 1)):
        text_cells = 0
        for col_num in range(1, sheet.max_column + 1):
            cell = sheet.cell(row=row_num, column=col_num)
            if cell.value and isinstance(cell.value, str) and len(cell.value.strip()) > 0:
                text_cells += 1
        if text_cells >= sheet.max_column * 0.5:  # 50%以上がテキスト
            header_rows.append(row_num)
    
    # データ領域を特定
    data_start_row = max(header_rows) + 1 if header_rows else 1
    
    return {
        'header_rows': header_rows,
        'data_start_row': data_start_row,
        'total_cells': len(all_cells),
        'max_row': sheet.max_row,
        'max_column': sheet.max_column
    }

def create_sheet_context(sheet, structure):
    """シート全体の文脈を作成"""
    context_parts = []
    
    # シート名を文脈に追加
    if sheet.title:
        context_parts.append(f"シート名: {sheet.title}")
    
    # ヘッダー行から文脈を作成
    for header_row in structure['header_rows']:
        header_texts = []
        for col_num in range(1, min(sheet.max_column + 1, 10)):  # 最大10列
            cell = sheet.cell(row=header_row, column=col_num)
            if cell.value and isinstance(cell.value, str):
                header_texts.append(cell.value)
        if header_texts:
            context_parts.append(' | '.join(header_texts))
    
    return '. '.join(context_parts)

def convert_sheet_to_structured_text(sheet, structure):
    """シートを構造化されたテキストに変換"""
    lines = []
    
    # ヘッダー行の処理
    for header_row in structure['header_rows']:
        header_cells = []
        for col_num in range(1, sheet.max_column + 1):
            cell = sheet.cell(row=header_row, column=col_num)
            if cell.value is not None:
                header_cells.append(str(cell.value))
            else:
                header_cells.append('')
        lines.append('\t'.join(header_cells))
    
    # データ行の処理
    for row_num in range(structure['data_start_row'], sheet.max_row + 1):
        row_cells = []
        has_content = False
        for col_num in range(1, sheet.max_column + 1):
            cell = sheet.cell(row=row_num, column=col_num)
            if cell.value is not None:
                if should_translate_cell(cell.value):
                    row_cells.append(str(cell.value))
                    has_content = True
                else:
                    row_cells.append(f"[PRESERVE]{cell.value}[/PRESERVE]")
            else:
                row_cells.append('')
        
        if has_content:
            lines.append('\t'.join(row_cells))
    
    return '\n'.join(lines)

def parse_translated_structured_text(translated_text, sheet, structure):
    """翻訳されたテキストを解析してシートに適用"""
    lines = translated_text.strip().split('\n')
    
    # ヘッダー行の処理
    header_line_count = len(structure['header_rows'])
    for i, header_row in enumerate(structure['header_rows']):
        if i < len(lines):
            cells = lines[i].split('\t')
            for col_num, cell_value in enumerate(cells, 1):
                if col_num <= sheet.max_column:
                    cell = sheet.cell(row=header_row, column=col_num)
                    if should_translate_cell(cell.value):
                        cell.value = cell_value
    
    # データ行の処理
    for i, row_num in enumerate(range(structure['data_start_row'], sheet.max_row + 1), header_line_count):
        if i < len(lines):
            cells = lines[i].split('\t')
            for col_num, cell_value in enumerate(cells, 1):
                if col_num <= sheet.max_column:
                    cell = sheet.cell(row=row_num, column=col_num)
                    if should_translate_cell(cell.value):
                        # [PRESERVE]タグがある場合は元の値を保持
                        if cell_value.startswith('[PRESERVE]') and cell_value.endswith('[/PRESERVE]'):
                            continue
                        else:
                            cell.value = cell_value

@app.route('/')
def index():
    try:
        return render_template('index.html')
    except Exception as e:
        return jsonify({
            'error': 'Template error',
            'message': str(e),
            'working_directory': os.getcwd(),
            'template_folder': app.template_folder,
            'files_in_templates': os.listdir(os.path.join(parent_dir, 'templates')) if os.path.exists(os.path.join(parent_dir, 'templates')) else 'templates directory not found'
        }), 500

@app.route('/health')
def health():
    return jsonify({
        'status': 'healthy',
        'service': 'excel-translator',
        'python_version': sys.version,
        'working_directory': os.getcwd(),
        'parent_directory': parent_dir,
        'current_directory': current_dir,
        'template_folder': app.template_folder,
        'environment_variables': list(os.environ.keys()),
        'deepl_api_key_exists': bool(os.environ.get('DEEPL_API_KEY')),
        'files_in_current_dir': os.listdir(os.getcwd()),
        'files_in_parent_dir': os.listdir(parent_dir) if os.path.exists(parent_dir) else 'parent directory not found'
    })

def translate_batch(texts, target_lang, source_lang, context, api_key, formality=None):
    """DeepL APIを使用して複数のテキストを一括翻訳"""
    if not texts:
        return []
    
    # 空のテキストを除外し、インデックスを記録
    non_empty_texts = []
    text_indices = []
    
    for i, text in enumerate(texts):
        if text and text.strip():
            non_empty_texts.append(text)
            text_indices.append(i)
    
    if not non_empty_texts:
        return texts
    
    url = "https://api-free.deepl.com/v2/translate"
    
    data = {
        'auth_key': api_key,
        'text': non_empty_texts,
        'target_lang': target_lang,
        'source_lang': source_lang if source_lang != 'auto' else None
    }
    
    if context:
        data['context'] = context
    
    # フォーマリティの設定
    if formality and formality != 'default':
        data['formality'] = formality
    
    # 常に高品質モードを使用
    data['model_type'] = 'quality_optimized'
    
    response = requests.post(url, data=data)
    
    if response.status_code == 200:
        result = response.json()
        translated_texts = [t['text'] for t in result['translations']]
        
        # 結果を元の配列に戻す
        final_results = list(texts)
        for i, translated_text in enumerate(translated_texts):
            final_results[text_indices[i]] = translated_text
        
        return final_results
    else:
        raise Exception(f"DeepL API error: {response.status_code} - {response.text}")

@app.route('/api/translate', methods=['POST'])
def api_translate():
    try:
        # 環境変数チェック
        deepl_api_key = os.environ.get('DEEPL_API_KEY')
        if not deepl_api_key:
            return jsonify({'error': 'DEEPL_API_KEY not found in environment variables'}), 500
        
        # ファイルチェック
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        # パラメータ取得
        source_lang = request.form.get('source_lang', 'JA')
        target_lang = request.form.get('target_lang', 'EN-US')
        context = request.form.get('context', '')
        formality = request.form.get('formality', 'default')
        
        # Excelファイルを読み込み
        wb = openpyxl.load_workbook(io.BytesIO(file.read()))
        
        # 全シートをシート全体翻訳で処理
        for sheet_name in wb.sheetnames:
            sheet = wb[sheet_name]
            
            # シート構造を分析
            structure = analyze_sheet_structure(sheet)
            
            # シート全体の文脈を作成
            sheet_context = create_sheet_context(sheet, structure)
            combined_context = f"{context}. {sheet_context}" if context else sheet_context
            
            # シートを構造化されたテキストに変換
            structured_text = convert_sheet_to_structured_text(sheet, structure)
            
            # 構造化されたテキストのサイズをチェック
            if len(structured_text) > 100000:  # 100KB以上の場合は分割
                # 大きなシートの場合は行ごとに分割して処理
                lines = structured_text.split('\n')
                header_lines = lines[:len(structure['header_rows'])]
                data_lines = lines[len(structure['header_rows']):]
                
                # ヘッダー行を翻訳
                if header_lines:
                    header_text = '\n'.join(header_lines)
                    try:
                        translated_header = translate_batch(
                            [header_text],
                            target_lang,
                            source_lang,
                            combined_context,
                            deepl_api_key,
                            formality
                        )[0]
                        
                        # ヘッダー行を解析してシートに適用
                        header_structure = {
                            'header_rows': structure['header_rows'],
                            'data_start_row': structure['header_rows'][-1] if structure['header_rows'] else 1,
                            'max_row': structure['header_rows'][-1] if structure['header_rows'] else 1,
                            'max_column': structure['max_column']
                        }
                        parse_translated_structured_text(translated_header, sheet, header_structure)
                        
                    except Exception as e:
                        print(f"Header translation error: {str(e)}")
                
                # データ行を小さなバッチに分けて翻訳
                batch_size = 50
                for i in range(0, len(data_lines), batch_size):
                    batch_lines = data_lines[i:i+batch_size]
                    batch_text = '\n'.join(batch_lines)
                    
                    try:
                        translated_batch = translate_batch(
                            [batch_text],
                            target_lang,
                            source_lang,
                            combined_context,
                            deepl_api_key,
                            formality
                        )[0]
                        
                        # バッチ結果を解析してシートに適用
                        batch_structure = {
                            'header_rows': [],
                            'data_start_row': structure['data_start_row'] + i,
                            'max_row': min(structure['data_start_row'] + i + batch_size - 1, structure['max_row']),
                            'max_column': structure['max_column']
                        }
                        parse_translated_structured_text(translated_batch, sheet, batch_structure)
                        
                    except Exception as e:
                        print(f"Data batch translation error: {str(e)}")
                        
            else:
                # 小さなシートの場合は全体を一度に翻訳
                try:
                    translated_text = translate_batch(
                        [structured_text],
                        target_lang,
                        source_lang,
                        combined_context,
                        deepl_api_key,
                        formality
                    )[0]
                    
                    # 翻訳されたテキストを解析してシートに適用
                    parse_translated_structured_text(translated_text, sheet, structure)
                    
                except Exception as e:
                    print(f"Sheet translation error: {str(e)}")
                    # エラーの場合は従来のセル単位翻訳にフォールバック
                    pass
        
        # 翻訳されたファイルを一時ファイルに保存
        with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp_file:
            wb.save(tmp_file.name)
            tmp_file_path = tmp_file.name
        
        # ファイル名を生成（翻訳済みの接頭辞を追加）
        original_filename = file.filename
        name, ext = os.path.splitext(original_filename)
        translated_filename = f"{name}_translated{ext}"
        
        # ファイルをダウンロード用に送信
        return send_file(
            tmp_file_path,
            as_attachment=True,
            download_name=translated_filename,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Vercel用のエクスポート
def app_handler(environ, start_response):
    return app(environ, start_response)

# Vercel用のapp変数をエクスポート
if __name__ == '__main__':
    app.run(debug=False)