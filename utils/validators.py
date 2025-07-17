"""
バリデーション関連のユーティリティ関数
"""
import os
from typing import Optional, Tuple
from werkzeug.datastructures import FileStorage


class ValidationError(Exception):
    """バリデーションエラー"""
    pass


def validate_file_upload(file: FileStorage, allowed_extensions: set, max_size: int) -> None:
    """
    アップロードされたファイルのバリデーション
    
    Args:
        file: アップロードされたファイル
        allowed_extensions: 許可される拡張子のセット
        max_size: 最大ファイルサイズ（バイト）
    
    Raises:
        ValidationError: バリデーションエラー
    """
    if not file:
        raise ValidationError("ファイルが選択されていません。")
    
    if file.filename == '':
        raise ValidationError("ファイルが選択されていません。")
    
    # 拡張子チェック
    if not _is_allowed_file(file.filename, allowed_extensions):
        extensions_str = ', '.join(f'.{ext}' for ext in allowed_extensions)
        raise ValidationError(f"許可されていないファイル形式です。対応形式: {extensions_str}")
    
    # ファイルサイズチェック
    if hasattr(file, 'content_length') and file.content_length:
        if file.content_length > max_size:
            raise ValidationError(f"ファイルサイズが大きすぎます。最大サイズ: {max_size // (1024*1024)}MB")


def _is_allowed_file(filename: str, allowed_extensions: set) -> bool:
    """
    ファイル名が許可された拡張子かチェック
    
    Args:
        filename: ファイル名
        allowed_extensions: 許可される拡張子のセット
    
    Returns:
        許可されている場合True
    """
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions


def validate_translation_params(source_lang: str, target_lang: str, context: str) -> Tuple[str, str, str]:
    """
    翻訳パラメータのバリデーション
    
    Args:
        source_lang: 翻訳元言語
        target_lang: 翻訳先言語
        context: 翻訳文脈
    
    Returns:
        バリデーション済みのパラメータ
    
    Raises:
        ValidationError: バリデーションエラー
    """
    # サポートされている言語コード
    supported_languages = {
        'JA', 'EN', 'EN-US', 'EN-GB', 'ZH', 'KO', 'DE', 'FR', 'ES', 'IT', 'PT', 'RU'
    }
    
    if source_lang not in supported_languages:
        raise ValidationError(f"サポートされていない翻訳元言語です: {source_lang}")
    
    if target_lang not in supported_languages:
        raise ValidationError(f"サポートされていない翻訳先言語です: {target_lang}")
    
    if source_lang == target_lang:
        raise ValidationError("翻訳元言語と翻訳先言語が同じです。")
    
    # 文脈の長さチェック
    if context and len(context) > 200:
        raise ValidationError("文脈が長すぎます。200文字以内で入力してください。")
    
    return source_lang, target_lang, context.strip() if context else ""


def validate_api_key(api_key: Optional[str]) -> str:
    """
    APIキーのバリデーション
    
    Args:
        api_key: APIキー
    
    Returns:
        バリデーション済みのAPIキー
    
    Raises:
        ValidationError: バリデーションエラー
    """
    if not api_key:
        raise ValidationError("DeepL APIキーが設定されていません。")
    
    if len(api_key) < 10:
        raise ValidationError("DeepL APIキーの形式が正しくありません。")
    
    if not api_key.endswith(':fx'):
        raise ValidationError("DeepL APIキーの形式が正しくありません。無料版のキーは':fx'で終わる必要があります。")
    
    return api_key


def validate_environment() -> dict:
    """
    実行環境のバリデーション
    
    Returns:
        環境変数の辞書
    
    Raises:
        ValidationError: バリデーションエラー
    """
    required_env_vars = ['DEEPL_API_KEY']
    env_vars = {}
    
    for var in required_env_vars:
        value = os.environ.get(var)
        if not value:
            raise ValidationError(f"必要な環境変数が設定されていません: {var}")
        env_vars[var] = value
    
    # APIキーのバリデーション
    validate_api_key(env_vars['DEEPL_API_KEY'])
    
    return env_vars