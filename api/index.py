from flask import Flask, jsonify, request, render_template
import os
import sys

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
        
        return jsonify({
            'success': True,
            'message': 'Translation endpoint is working',
            'filename': file.filename,
            'api_key_configured': bool(deepl_api_key)
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Vercel用のエクスポート
def app_handler(environ, start_response):
    return app(environ, start_response)

# Vercel用のapp変数をエクスポート
if __name__ == '__main__':
    app.run(debug=False)