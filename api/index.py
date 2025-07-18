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

def translate_batch(texts, target_lang, source_lang, context, api_key, formality=None, quality_mode='balanced'):
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
    
    # 品質モードの設定
    if quality_mode == 'quality':
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
        quality_mode = request.form.get('quality_mode', 'balanced')
        
        # Excelファイルを読み込み
        wb = openpyxl.load_workbook(io.BytesIO(file.read()))
        
        # 全シートの全セルを翻訳（バッチ処理）
        for sheet_name in wb.sheetnames:
            sheet = wb[sheet_name]
            
            # 翻訳対象のセルを収集（インテリジェント分析）
            cells_to_translate = []
            texts_to_translate = []
            cell_contexts = []
            
            for row in sheet.iter_rows():
                for cell in row:
                    if should_translate_cell(cell.value):
                        cells_to_translate.append(cell)
                        texts_to_translate.append(cell.value)
                        
                        # 個別の文脈を生成（既存の文脈と組み合わせ）
                        cell_context = generate_context_from_headers(sheet, cell.row, cell.column)
                        if context and cell_context:
                            combined_context = f"{context}. {cell_context}"
                        else:
                            combined_context = context or cell_context
                        cell_contexts.append(combined_context)
            
            # バッチで翻訳（最大50個ずつ）
            batch_size = 50
            for i in range(0, len(texts_to_translate), batch_size):
                batch_texts = texts_to_translate[i:i+batch_size]
                batch_cells = cells_to_translate[i:i+batch_size]
                batch_contexts = cell_contexts[i:i+batch_size]
                
                try:
                    # バッチの代表的な文脈を使用（最初の非空の文脈）
                    batch_context = next((ctx for ctx in batch_contexts if ctx), context)
                    
                    translated_batch = translate_batch(
                        batch_texts,
                        target_lang,
                        source_lang,
                        batch_context,
                        deepl_api_key,
                        formality,
                        quality_mode
                    )
                    
                    # 翻訳結果をセルに適用
                    for j, translated_text in enumerate(translated_batch):
                        batch_cells[j].value = translated_text
                        
                except Exception as e:
                    print(f"Translation error for batch: {str(e)}")
                    # バッチエラーの場合は元のテキストを保持
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