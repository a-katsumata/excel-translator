"""
Excel翻訳機能のテストコード
"""
import pytest
import io
import openpyxl
from unittest.mock import Mock, patch
from excel_translator import ExcelTranslator


class TestExcelTranslator:
    """Excel翻訳クラスのテスト"""
    
    @pytest.fixture
    def translator(self):
        """テスト用の翻訳インスタンス"""
        return ExcelTranslator("test-api-key:fx")
    
    @pytest.fixture
    def sample_excel_data(self):
        """テスト用のExcelデータ"""
        workbook = openpyxl.Workbook()
        sheet = workbook.active
        sheet['A1'] = 'こんにちは'
        sheet['B1'] = 'さようなら'
        sheet['A2'] = '○'
        sheet['B2'] = '×'
        
        output = io.BytesIO()
        workbook.save(output)
        output.seek(0)
        return output.read()
    
    def test_should_translate_text_with_japanese(self, translator):
        """日本語テキストの翻訳判定テスト"""
        assert translator.should_translate_text("こんにちは") == True
        assert translator.should_translate_text("テスト") == True
    
    def test_should_translate_text_with_symbols(self, translator):
        """記号の翻訳判定テスト"""
        assert translator.should_translate_text("○") == False
        assert translator.should_translate_text("×") == False
        assert translator.should_translate_text("△") == False
        assert translator.should_translate_text("---") == False
    
    def test_should_translate_text_with_numbers(self, translator):
        """数字の翻訳判定テスト"""
        assert translator.should_translate_text("123") == False
        assert translator.should_translate_text("1.5") == False
        assert translator.should_translate_text("(1)") == False
    
    def test_should_translate_text_with_short_english(self, translator):
        """短い英語の翻訳判定テスト"""
        assert translator.should_translate_text("A") == False
        assert translator.should_translate_text("ID") == False
        assert translator.should_translate_text("B1") == False
    
    def test_get_context_replacements_itinerary(self, translator):
        """日程表用の置換ルールテスト"""
        replacements = translator.get_context_replacements("日程表")
        assert "朝食" in replacements
        assert replacements["朝食"] == "Breakfast"
        assert "昼食" in replacements
        assert replacements["昼食"] == "Lunch"
    
    def test_get_context_replacements_business_plan(self, translator):
        """事業計画用の置換ルールテスト"""
        replacements = translator.get_context_replacements("事業計画")
        assert "売上" in replacements
        assert replacements["売上"] == "Revenue"
        assert "利益" in replacements
        assert replacements["利益"] == "Profit"
    
    def test_get_context_replacements_unknown(self, translator):
        """未知の文脈での置換ルールテスト"""
        replacements = translator.get_context_replacements("未知の文脈")
        assert len(replacements) == 0
    
    def test_preprocess_text(self, translator):
        """テキスト前処理のテスト"""
        replacements = {"朝食": "Breakfast", "昼食": "Lunch"}
        
        result = translator.preprocess_text("朝食と昼食", replacements)
        assert result == "Breakfastと Lunch"
    
    def test_preprocess_text_no_replacements(self, translator):
        """置換なしのテキスト前処理テスト"""
        result = translator.preprocess_text("テスト", {})
        assert result == "テスト"
    
    def test_get_translation_context(self, translator):
        """翻訳コンテキストメッセージのテスト"""
        context = translator._get_translation_context("日程表")
        assert "travel itinerary" in context
        
        context = translator._get_translation_context("事業計画")
        assert "business plan" in context
        
        context = translator._get_translation_context("")
        assert "general business document" in context
    
    @patch('deepl.Translator.translate_text')
    def test_validate_api_key_success(self, mock_translate, translator):
        """APIキー検証成功のテスト"""
        mock_result = Mock()
        mock_result.text = "Test"
        mock_translate.return_value = mock_result
        
        assert translator.validate_api_key() == True
        mock_translate.assert_called_once()
    
    @patch('deepl.Translator.translate_text')
    def test_validate_api_key_failure(self, mock_translate, translator):
        """APIキー検証失敗のテスト"""
        from deepl.exceptions import AuthorizationError
        mock_translate.side_effect = AuthorizationError("Invalid API key")
        
        assert translator.validate_api_key() == False
    
    @patch('deepl.Translator.translate_text')
    def test_translate_excel_file_success(self, mock_translate, translator, sample_excel_data):
        """Excel翻訳成功のテスト"""
        mock_result = Mock()
        mock_result.text = "Hello"
        mock_translate.return_value = [mock_result, mock_result]
        
        result = translator.translate_excel_file(
            file_data=sample_excel_data,
            context="テスト",
            source_lang="JA",
            target_lang="EN-US"
        )
        
        assert isinstance(result, bytes)
        assert len(result) > 0
        
        # 翻訳結果を確認
        workbook = openpyxl.load_workbook(io.BytesIO(result))
        sheet = workbook.active
        assert sheet['A1'].value == "Hello"
        assert sheet['B1'].value == "Hello"
        # 記号はそのまま保持
        assert sheet['A2'].value == "○"
        assert sheet['B2'].value == "×"
    
    @patch('deepl.Translator.translate_text')
    def test_translate_excel_file_api_error(self, mock_translate, translator, sample_excel_data):
        """Excel翻訳API エラーのテスト"""
        from deepl.exceptions import AuthorizationError
        mock_translate.side_effect = AuthorizationError("Invalid API key")
        
        with pytest.raises(Exception) as exc_info:
            translator.translate_excel_file(
                file_data=sample_excel_data,
                context="テスト",
                source_lang="JA",
                target_lang="EN-US"
            )
        
        assert "DeepL APIキーが無効です" in str(exc_info.value)
    
    @patch('deepl.Translator.translate_text')
    def test_translate_excel_file_quota_error(self, mock_translate, translator, sample_excel_data):
        """Excel翻訳クォータエラーのテスト"""
        from deepl.exceptions import QuotaExceededException
        mock_translate.side_effect = QuotaExceededException("Quota exceeded")
        
        with pytest.raises(Exception) as exc_info:
            translator.translate_excel_file(
                file_data=sample_excel_data,
                context="テスト",
                source_lang="JA",
                target_lang="EN-US"
            )
        
        assert "使用制限に達しました" in str(exc_info.value)
    
    def test_translate_excel_file_invalid_data(self, translator):
        """無効なExcelデータのテスト"""
        invalid_data = b"invalid excel data"
        
        with pytest.raises(Exception) as exc_info:
            translator.translate_excel_file(
                file_data=invalid_data,
                context="テスト",
                source_lang="JA",
                target_lang="EN-US"
            )
        
        assert "翻訳処理中にエラーが発生しました" in str(exc_info.value)


if __name__ == "__main__":
    pytest.main([__file__])