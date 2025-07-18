from flask import Flask, render_template, request, jsonify
import os
import sys
import logging
from werkzeug.utils import secure_filename

# パスを追加してモジュールをインポート
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

try:
    from excel_translator import ExcelTranslator
    from utils.validators import ValidationError, validate_file_upload, validate_translation_params, validate_environment
    from utils.response_helpers import (
        create_error_response, create_success_response, create_translation_result_response,
        create_health_response, log_request_info, handle_exception
    )
except ImportError as e:
    logger.error(f"Import error: {e}")
    # Fallback imports with absolute paths
    import importlib.util
    
    # Import excel_translator
    spec = importlib.util.spec_from_file_location("excel_translator", os.path.join(parent_dir, "excel_translator.py"))
    excel_translator_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(excel_translator_module)
    ExcelTranslator = excel_translator_module.ExcelTranslator
    
    # Import utils
    validators_path = os.path.join(parent_dir, "utils", "validators.py")
    spec = importlib.util.spec_from_file_location("validators", validators_path)
    validators_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(validators_module)
    ValidationError = validators_module.ValidationError
    validate_file_upload = validators_module.validate_file_upload
    validate_translation_params = validators_module.validate_translation_params
    validate_environment = validators_module.validate_environment
    
    response_helpers_path = os.path.join(parent_dir, "utils", "response_helpers.py")
    spec = importlib.util.spec_from_file_location("response_helpers", response_helpers_path)
    response_helpers_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(response_helpers_module)
    create_error_response = response_helpers_module.create_error_response
    create_success_response = response_helpers_module.create_success_response
    create_translation_result_response = response_helpers_module.create_translation_result_response
    create_health_response = response_helpers_module.create_health_response
    log_request_info = response_helpers_module.log_request_info
    handle_exception = response_helpers_module.handle_exception

# ログ設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Debug: Environment and path information
logger.info(f"Python version: {sys.version}")
logger.info(f"Current working directory: {os.getcwd()}")
logger.info(f"Script directory: {current_dir}")
logger.info(f"Parent directory: {parent_dir}")
logger.info(f"Python path: {sys.path}")
logger.info(f"Environment variables: {list(os.environ.keys())}")

app = Flask(__name__, template_folder='../templates')
app.secret_key = os.environ.get('SECRET_KEY', 'excel-translator-secret-key')

# 設定
ALLOWED_EXTENSIONS = {'xlsx', 'xls'}
MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB

# 環境変数の検証
try:
    env_vars = validate_environment()
    DEEPL_API_KEY = env_vars['DEEPL_API_KEY']
    logger.info("Environment validation passed")
except ValidationError as e:
    logger.error(f"Environment validation failed: {e}")
    raise

def create_translator() -> ExcelTranslator:
    """
    翻訳インスタンスを作成
    
    Returns:
        ExcelTranslator: 翻訳インスタンス
    """
    return ExcelTranslator(DEEPL_API_KEY)

@app.route('/')
def index():
    """
    メインページ - ファイルアップロード画面
    """
    try:
        log_request_info(request, 'index')
        return render_template('index.html')
    except Exception as e:
        return handle_exception(e, 'index')

@app.route('/upload', methods=['POST'])
def upload_file():
    """
    ファイルアップロード処理
    """
    try:
        log_request_info(request, 'upload')
        
        # ファイルの取得
        file = request.files.get('file')
        context = request.form.get('context', '')
        source_lang = request.form.get('source_lang', 'JA')
        target_lang = request.form.get('target_lang', 'EN-US')
        
        # バリデーション
        validate_file_upload(file, ALLOWED_EXTENSIONS, MAX_CONTENT_LENGTH)
        source_lang, target_lang, context = validate_translation_params(source_lang, target_lang, context)
        
        # ファイルデータを読み込み
        file_data = file.read()
        
        # 翻訳処理
        translator = create_translator()
        
        # APIキーの有効性を確認
        if not translator.validate_api_key():
            return create_error_response('DeepL APIキーが無効です。', 401)
        
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
        
        return create_translation_result_response(
            original_filename=original_filename,
            translated_filename=translated_filename,
            translated_data=translated_data,
            context=context,
            source_lang=source_lang,
            target_lang=target_lang,
            format_type="html"
        )
        
    except ValidationError as e:
        return create_error_response(str(e), 400)
    except Exception as e:
        return handle_exception(e, 'upload')

@app.route('/health')
def health_check():
    """
    ヘルスチェック用エンドポイント
    """
    try:
        return create_health_response()
    except Exception as e:
        return handle_exception(e, 'health')

@app.route('/api/translate', methods=['POST'])
def api_translate():
    """
    API形式での翻訳処理
    """
    try:
        log_request_info(request, 'api_translate')
        
        # ファイルの取得
        file = request.files.get('file')
        context = request.form.get('context', '')
        source_lang = request.form.get('source_lang', 'JA')
        target_lang = request.form.get('target_lang', 'EN-US')
        
        # バリデーション
        validate_file_upload(file, ALLOWED_EXTENSIONS, MAX_CONTENT_LENGTH)
        source_lang, target_lang, context = validate_translation_params(source_lang, target_lang, context)
        
        # ファイルデータを読み込み
        file_data = file.read()
        
        # 翻訳処理
        translator = create_translator()
        
        if not translator.validate_api_key():
            return create_error_response('DeepL APIキーが無効です。', 401)
        
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
        
        return create_translation_result_response(
            original_filename=original_filename,
            translated_filename=translated_filename,
            translated_data=translated_data,
            context=context,
            source_lang=source_lang,
            target_lang=target_lang,
            format_type="json"
        )
        
    except ValidationError as e:
        return create_error_response(str(e), 400)
    except Exception as e:
        return handle_exception(e, 'api_translate')

# Vercel用のハンドラー
def handler(environ, start_response):
    return app(environ, start_response)

if __name__ == '__main__':
    app.run(debug=False)