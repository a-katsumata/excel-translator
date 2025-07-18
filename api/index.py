from flask import Flask, jsonify, request, render_template, send_file
import os
import sys
import openpyxl
import requests
import io
import tempfile
from urllib.parse import quote

# パスを追加
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

app = Flask(__name__, template_folder='../templates')
app.secret_key = os.environ.get('SECRET_KEY', 'excel-translator-secret-key')

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

def translate_batch(texts, target_lang, source_lang, context, api_key):
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
        
        # Excelファイルを読み込み
        wb = openpyxl.load_workbook(io.BytesIO(file.read()))
        
        # 全シートの全セルを翻訳（バッチ処理）
        for sheet_name in wb.sheetnames:
            sheet = wb[sheet_name]
            
            # 翻訳対象のセルを収集
            cells_to_translate = []
            texts_to_translate = []
            
            for row in sheet.iter_rows():
                for cell in row:
                    if cell.value and isinstance(cell.value, str):
                        cells_to_translate.append(cell)
                        texts_to_translate.append(cell.value)
            
            # バッチで翻訳（最大50個ずつ）
            batch_size = 50
            for i in range(0, len(texts_to_translate), batch_size):
                batch_texts = texts_to_translate[i:i+batch_size]
                batch_cells = cells_to_translate[i:i+batch_size]
                
                try:
                    translated_batch = translate_batch(
                        batch_texts,
                        target_lang,
                        source_lang,
                        context,
                        deepl_api_key
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