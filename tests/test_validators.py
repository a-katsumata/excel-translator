"""
バリデーション機能のテストコード
"""
import pytest
from unittest.mock import Mock
from utils.validators import (
    ValidationError, validate_file_upload, validate_translation_params,
    validate_api_key, validate_environment
)


class TestValidators:
    """バリデーション関数のテスト"""
    
    def test_validate_file_upload_success(self):
        """ファイルアップロード検証成功のテスト"""
        mock_file = Mock()
        mock_file.filename = "test.xlsx"
        mock_file.content_length = 1024
        
        # 例外が発生しないことを確認
        validate_file_upload(mock_file, {'xlsx', 'xls'}, 16*1024*1024)
    
    def test_validate_file_upload_no_file(self):
        """ファイルなしのテスト"""
        with pytest.raises(ValidationError) as exc_info:
            validate_file_upload(None, {'xlsx', 'xls'}, 16*1024*1024)
        
        assert "ファイルが選択されていません" in str(exc_info.value)
    
    def test_validate_file_upload_empty_filename(self):
        """空のファイル名のテスト"""
        mock_file = Mock()
        mock_file.filename = ""
        
        with pytest.raises(ValidationError) as exc_info:
            validate_file_upload(mock_file, {'xlsx', 'xls'}, 16*1024*1024)
        
        assert "ファイルが選択されていません" in str(exc_info.value)
    
    def test_validate_file_upload_invalid_extension(self):
        """無効な拡張子のテスト"""
        mock_file = Mock()
        mock_file.filename = "test.txt"
        mock_file.content_length = 1024
        
        with pytest.raises(ValidationError) as exc_info:
            validate_file_upload(mock_file, {'xlsx', 'xls'}, 16*1024*1024)
        
        assert "許可されていないファイル形式です" in str(exc_info.value)
    
    def test_validate_file_upload_large_file(self):
        """大きなファイルのテスト"""
        mock_file = Mock()
        mock_file.filename = "test.xlsx"
        mock_file.content_length = 20*1024*1024  # 20MB
        
        with pytest.raises(ValidationError) as exc_info:
            validate_file_upload(mock_file, {'xlsx', 'xls'}, 16*1024*1024)
        
        assert "ファイルサイズが大きすぎます" in str(exc_info.value)
    
    def test_validate_translation_params_success(self):
        """翻訳パラメータ検証成功のテスト"""
        source, target, context = validate_translation_params("JA", "EN-US", "テスト")
        
        assert source == "JA"
        assert target == "EN-US"
        assert context == "テスト"
    
    def test_validate_translation_params_invalid_source(self):
        """無効な翻訳元言語のテスト"""
        with pytest.raises(ValidationError) as exc_info:
            validate_translation_params("INVALID", "EN-US", "テスト")
        
        assert "サポートされていない翻訳元言語です" in str(exc_info.value)
    
    def test_validate_translation_params_invalid_target(self):
        """無効な翻訳先言語のテスト"""
        with pytest.raises(ValidationError) as exc_info:
            validate_translation_params("JA", "INVALID", "テスト")
        
        assert "サポートされていない翻訳先言語です" in str(exc_info.value)
    
    def test_validate_translation_params_same_language(self):
        """同じ言語のテスト"""
        with pytest.raises(ValidationError) as exc_info:
            validate_translation_params("JA", "JA", "テスト")
        
        assert "翻訳元言語と翻訳先言語が同じです" in str(exc_info.value)
    
    def test_validate_translation_params_long_context(self):
        """長い文脈のテスト"""
        long_context = "あ" * 201  # 201文字
        
        with pytest.raises(ValidationError) as exc_info:
            validate_translation_params("JA", "EN-US", long_context)
        
        assert "文脈が長すぎます" in str(exc_info.value)
    
    def test_validate_translation_params_empty_context(self):
        """空の文脈のテスト"""
        source, target, context = validate_translation_params("JA", "EN-US", "")
        
        assert source == "JA"
        assert target == "EN-US"
        assert context == ""
    
    def test_validate_api_key_success(self):
        """APIキー検証成功のテスト"""
        api_key = validate_api_key("valid-api-key-12345:fx")
        assert api_key == "valid-api-key-12345:fx"
    
    def test_validate_api_key_none(self):
        """APIキーがNoneのテスト"""
        with pytest.raises(ValidationError) as exc_info:
            validate_api_key(None)
        
        assert "DeepL APIキーが設定されていません" in str(exc_info.value)
    
    def test_validate_api_key_empty(self):
        """APIキーが空のテスト"""
        with pytest.raises(ValidationError) as exc_info:
            validate_api_key("")
        
        assert "DeepL APIキーが設定されていません" in str(exc_info.value)
    
    def test_validate_api_key_too_short(self):
        """APIキーが短すぎるテスト"""
        with pytest.raises(ValidationError) as exc_info:
            validate_api_key("short")
        
        assert "DeepL APIキーの形式が正しくありません" in str(exc_info.value)
    
    def test_validate_api_key_invalid_format(self):
        """APIキーの形式が無効のテスト"""
        with pytest.raises(ValidationError) as exc_info:
            validate_api_key("invalid-api-key-12345")
        
        assert "DeepL APIキーの形式が正しくありません" in str(exc_info.value)
    
    def test_validate_environment_success(self, monkeypatch):
        """環境変数検証成功のテスト"""
        monkeypatch.setenv("DEEPL_API_KEY", "valid-api-key-12345:fx")
        
        env_vars = validate_environment()
        assert env_vars["DEEPL_API_KEY"] == "valid-api-key-12345:fx"
    
    def test_validate_environment_missing_key(self, monkeypatch):
        """環境変数不足のテスト"""
        monkeypatch.delenv("DEEPL_API_KEY", raising=False)
        
        with pytest.raises(ValidationError) as exc_info:
            validate_environment()
        
        assert "必要な環境変数が設定されていません" in str(exc_info.value)
    
    def test_validate_environment_invalid_api_key(self, monkeypatch):
        """環境変数のAPIキーが無効のテスト"""
        monkeypatch.setenv("DEEPL_API_KEY", "invalid-key")
        
        with pytest.raises(ValidationError) as exc_info:
            validate_environment()
        
        assert "DeepL APIキーの形式が正しくありません" in str(exc_info.value)


if __name__ == "__main__":
    pytest.main([__file__])