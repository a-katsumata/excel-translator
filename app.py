from flask import Flask, render_template, request, jsonify, send_file, flash, redirect, url_for
import os
import io
from werkzeug.utils import secure_filename
from excel_translator import ExcelTranslator
from dotenv import load_dotenv

# 環境変数を読み込み
load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'your-secret-key-here')

# 設定
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'xlsx', 'xls'}
MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB

# DeepL APIキー（環境変数から取得）
DEEPL_API_KEY = os.environ.get('DEEPL_API_KEY', 'a8ee58ad-8642-4c06-85b4-bc7d0e6e35a8:fx')

# アップロードフォルダを作成
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    """
    アップロードされたファイルが許可された拡張子かチェック
    """
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    """
    メインページ - ファイルアップロード画面
    """
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    """
    ファイルアップロード処理
    """
    if 'file' not in request.files:
        flash('ファイルが選択されていません。')
        return redirect(request.url)
    
    file = request.files['file']
    context = request.form.get('context', '')
    source_lang = request.form.get('source_lang', 'JA')
    target_lang = request.form.get('target_lang', 'EN-US')
    
    if file.filename == '':
        flash('ファイルが選択されていません。')
        return redirect(request.url)
    
    if file and allowed_file(file.filename):
        try:
            # ファイルデータを読み込み
            file_data = file.read()
            
            # 翻訳処理
            translator = ExcelTranslator(DEEPL_API_KEY)
            
            # APIキーの有効性を確認
            if not translator.validate_api_key():
                flash('DeepL APIキーが無効です。設定を確認してください。')
                return redirect(url_for('index'))
            
            # 翻訳実行
            translated_data = translator.translate_excel_file(
                file_data=file_data,
                context=context,
                source_lang=source_lang,
                target_lang=target_lang
            )
            
            # 翻訳後のファイル名を生成
            original_filename = secure_filename(file.filename)
            name, ext = os.path.splitext(original_filename)
            translated_filename = f"{name}_translated{ext}"
            
            # Base64エンコードしてテンプレートに渡す
            import base64
            encoded_data = base64.b64encode(translated_data).decode('utf-8')
        
            return render_template('result.html', 
                                     original_filename=original_filename,
                                     translated_filename=translated_filename,
                                     context=context,
                                     source_lang=source_lang,
                                     target_lang=target_lang,
                                     file_data=encoded_data)
            
        except Exception as e:
            flash(f'翻訳処理中にエラーが発生しました: {str(e)}')
            return redirect(url_for('index'))
    
    else:
        flash('許可されていないファイル形式です。Excel形式(.xlsx, .xls)のファイルを選択してください。')
        return redirect(url_for('index'))

@app.route('/download')
def download_file():
    """
    翻訳済みファイルのダウンロード
    """
    file_data = request.args.get('file_data')
    filename = request.args.get('filename', 'translated_file.xlsx')
    
    if not file_data:
        flash('ダウンロードするファイルが見つかりません。')
        return redirect(url_for('index'))
    
    try:
        # Base64デコード（実際の実装では適切なデータ受け渡し方法を使用）
        import base64
        decoded_data = base64.b64decode(file_data)
        
        return send_file(
            io.BytesIO(decoded_data),
            as_attachment=True,
            download_name=filename,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
    
    except Exception as e:
        flash(f'ファイルのダウンロードに失敗しました: {str(e)}')
        return redirect(url_for('index'))

@app.route('/health')
def health_check():
    """
    ヘルスチェック用エンドポイント
    """
    return jsonify({'status': 'healthy', 'service': 'excel-translator'})

@app.route('/api/translate', methods=['POST'])
def api_translate():
    """
    API形式での翻訳処理
    """
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'ファイルが選択されていません。'}), 400
        
        file = request.files['file']
        context = request.form.get('context', '')
        source_lang = request.form.get('source_lang', 'JA')
        target_lang = request.form.get('target_lang', 'EN-US')
        
        if not allowed_file(file.filename):
            return jsonify({'error': '許可されていないファイル形式です。'}), 400
        
        # ファイルデータを読み込み
        file_data = file.read()
        
        # 翻訳処理
        translator = ExcelTranslator(DEEPL_API_KEY)
        
        if not translator.validate_api_key():
            return jsonify({'error': 'DeepL APIキーが無効です。'}), 500
        
        translated_data = translator.translate_excel_file(
            file_data=file_data,
            context=context,
            source_lang=source_lang,
            target_lang=target_lang
        )
        
        # Base64エンコードして返す
        import base64
        encoded_data = base64.b64encode(translated_data).decode('utf-8')
        
        return jsonify({
            'success': True,
            'translated_file': encoded_data,
            'original_filename': file.filename,
            'context': context
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    # 本番環境では環境変数を使用、開発環境ではデフォルト値を使用
    host = os.environ.get('HOST', '0.0.0.0')
    port = int(os.environ.get('PORT', 5003))
    debug = os.environ.get('FLASK_ENV', 'development') == 'development'
    
    app.run(debug=debug, host=host, port=port)