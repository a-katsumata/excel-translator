from flask import Flask, jsonify, request, render_template
import os
import sys
import logging

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# パスを追加
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

app = Flask(__name__, template_folder='../templates')
app.secret_key = os.environ.get('SECRET_KEY', 'excel-translator-secret-key')

# 基本的なヘルスチェック
@app.route('/')
def index():
    try:
        return render_template('index.html')
    except Exception as e:
        logger.error(f"Index error: {e}")
        return jsonify({
            'error': 'Template error',
            'message': str(e),
            'working_directory': os.getcwd(),
            'template_folder': app.template_folder
        }), 500

@app.route('/health')
def health():
    return jsonify({
        'status': 'healthy',
        'service': 'excel-translator',
        'python_version': sys.version,
        'working_directory': os.getcwd(),
        'environment_variables': list(os.environ.keys()),
        'deepl_api_key_exists': bool(os.environ.get('DEEPL_API_KEY'))
    })

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
        
        # 基本的な翻訳処理（後で実装）
        return jsonify({
            'success': True,
            'message': 'Translation endpoint is working',
            'filename': file.filename,
            'api_key_configured': bool(deepl_api_key)
        })
        
    except Exception as e:
        logger.error(f"API translate error: {e}")
        return jsonify({'error': str(e)}), 500

# Vercel用のハンドラー
def handler(environ, start_response):
    return app(environ, start_response)

# デバッグ情報
logger.info(f"Python version: {sys.version}")
logger.info(f"Current working directory: {os.getcwd()}")
logger.info(f"Template folder: {app.template_folder}")
logger.info(f"Environment variables: {list(os.environ.keys())}")

if __name__ == '__main__':
    app.run(debug=False)