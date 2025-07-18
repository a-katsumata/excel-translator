"""
レスポンス作成用のヘルパー関数
"""
from typing import Dict, Any, Optional, Union
from flask import jsonify, render_template, Response
import base64
import logging


logger = logging.getLogger(__name__)


def create_error_response(message: str, status_code: int = 400, details: Optional[str] = None) -> Response:
    """
    エラーレスポンスを作成
    
    Args:
        message: エラーメッセージ
        status_code: HTTPステータスコード
        details: 詳細情報
    
    Returns:
        JSONレスポンス
    """
    response_data = {
        'success': False,
        'error': message,
        'status_code': status_code
    }
    
    if details:
        response_data['details'] = details
    
    logger.error(f"Error response: {message} (Status: {status_code})")
    return jsonify(response_data), status_code


def create_success_response(data: Dict[str, Any], message: str = "Success") -> Response:
    """
    成功レスポンスを作成
    
    Args:
        data: レスポンスデータ
        message: 成功メッセージ
    
    Returns:
        JSONレスポンス
    """
    response_data = {
        'success': True,
        'message': message,
        'data': data
    }
    
    logger.info(f"Success response: {message}")
    return jsonify(response_data)


def create_translation_result_response(
    original_filename: str,
    translated_filename: str,
    translated_data: bytes,
    context: str,
    source_lang: str,
    target_lang: str,
    format_type: str = "html"
) -> Union[Response, str]:
    """
    翻訳結果のレスポンスを作成
    
    Args:
        original_filename: 元のファイル名
        translated_filename: 翻訳後のファイル名
        translated_data: 翻訳後のファイルデータ
        context: 翻訳文脈
        source_lang: 翻訳元言語
        target_lang: 翻訳先言語
        format_type: レスポンス形式（html または json）
    
    Returns:
        レスポンス
    """
    encoded_data = base64.b64encode(translated_data).decode('utf-8')
    
    if format_type == "json":
        return create_success_response({
            'original_filename': original_filename,
            'translated_filename': translated_filename,
            'translated_file': encoded_data,
            'context': context,
            'source_lang': source_lang,
            'target_lang': target_lang
        }, "翻訳が完了しました")
    
    # HTML形式の場合
    return render_template(
        'result.html',
        original_filename=original_filename,
        translated_filename=translated_filename,
        context=context,
        source_lang=source_lang,
        target_lang=target_lang,
        file_data=encoded_data
    )


def create_health_response() -> Response:
    """
    ヘルスチェックレスポンスを作成
    
    Returns:
        JSONレスポンス
    """
    import os
    import sys
    
    health_data = {
        'status': 'healthy',
        'service': 'excel-translator',
        'version': '1.0.0',
        'environment': {
            'python_version': sys.version,
            'platform': sys.platform,
            'working_directory': os.getcwd(),
            'has_deepl_key': bool(os.environ.get('DEEPL_API_KEY')),
            'has_secret_key': bool(os.environ.get('SECRET_KEY'))
        }
    }
    
    # Test imports
    try:
        import excel_translator
        health_data['imports'] = {'excel_translator': 'OK'}
    except ImportError as e:
        health_data['imports'] = {'excel_translator': f'ERROR: {str(e)}'}
    
    try:
        import utils.validators
        health_data['imports']['utils.validators'] = 'OK'
    except ImportError as e:
        health_data['imports']['utils.validators'] = f'ERROR: {str(e)}'
    
    return jsonify(health_data)


def log_request_info(request, endpoint: str) -> None:
    """
    リクエスト情報をログに記録
    
    Args:
        request: Flaskリクエストオブジェクト
        endpoint: エンドポイント名
    """
    logger.info(f"Request to {endpoint}: {request.method} {request.path}")
    if request.files:
        for key, file in request.files.items():
            logger.info(f"File uploaded: {key} = {file.filename}")
    if request.form:
        form_data = dict(request.form)
        # APIキーなどの機密情報はログに記録しない
        if 'api_key' in form_data:
            form_data['api_key'] = '*' * 8
        logger.info(f"Form data: {form_data}")


def handle_exception(e: Exception, endpoint: str) -> Response:
    """
    例外処理の統一ハンドラー
    
    Args:
        e: 例外オブジェクト
        endpoint: エンドポイント名
    
    Returns:
        エラーレスポンス
    """
    logger.exception(f"Exception in {endpoint}: {str(e)}")
    
    # 既知の例外タイプに応じた処理
    if "APIキー" in str(e):
        return create_error_response("APIキーが無効です。設定を確認してください。", 401)
    elif "制限" in str(e) or "quota" in str(e).lower():
        return create_error_response("API使用制限に達しました。しばらく待ってから再試行してください。", 429)
    elif "ファイル" in str(e):
        return create_error_response(str(e), 400)
    else:
        return create_error_response("予期しないエラーが発生しました。", 500, str(e))