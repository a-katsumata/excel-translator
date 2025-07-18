# Excel翻訳ツール

DeepL APIを使用してExcelファイルを翻訳するWebアプリケーションです。セルの結合、フォーマット、構造を完全に保持したまま翻訳を行います。

## 機能

- **Excelファイル翻訳**: .xlsx、.xlsファイルに対応
- **文脈対応翻訳**: 文脈に応じた前処理で翻訳精度を向上
- **構造保持**: セルの結合、フォーマット、数式をそのまま保持
- **多言語対応**: 日本語、英語、中国語、韓国語など複数言語に対応
- **直感的なUI**: ドラッグ&ドロップでファイルアップロード可能

## 文脈対応機能

以下の文脈に応じて最適化された翻訳を提供：

- **日程表**: 旅行や出張の旅程表
- **事業計画**: ビジネスプランや戦略文書
- **財務諸表**: 会計・財務関連文書
- **会議議事録**: 会議記録や打ち合わせ資料
- **カスタム**: 独自の文脈を設定可能

## 必要な環境

- Python 3.7以上
- DeepL API キー（無料版または有料版）

## インストール方法

1. リポジトリをクローンまたはダウンロード
2. 必要なライブラリをインストール：
   ```bash
   pip install -r requirements.txt
   ```

3. `app.py`内のAPIキーを設定：
   ```python
   DEEPL_API_KEY = "your-deepl-api-key-here"
   ```

## 使用方法

1. アプリケーションを起動：
   ```bash
   python app.py
   ```

2. ブラウザで `http://localhost:5001` にアクセス

3. 翻訳したいExcelファイルをアップロード

4. 文脈を選択・入力

5. 翻訳言語を設定

6. 翻訳を実行し、結果をダウンロード

## ファイル構成

```
exceltrans/
├── app.py              # Flaskアプリケーション本体
├── excel_translator.py # 翻訳エンジン
├── trans.py           # 元のスクリプト（参考用）
├── requirements.txt   # 必要なライブラリ
├── templates/
│   ├── index.html     # アップロード画面
│   └── result.html    # 結果画面
└── uploads/           # アップロードファイル一時保存
```

## API仕様

### POST /upload
ファイルアップロード用エンドポイント

**パラメータ:**
- `file`: Excelファイル
- `context`: 文脈情報
- `source_lang`: 翻訳元言語
- `target_lang`: 翻訳先言語

### POST /api/translate
API形式での翻訳エンドポイント

**レスポンス:**
```json
{
  "success": true,
  "translated_file": "base64-encoded-data",
  "original_filename": "original.xlsx",
  "context": "日程表"
}
```

## 注意事項

- 大きなファイルは処理に時間がかかる場合があります
- 機密情報を含むファイルの翻訳時は十分ご注意ください
- DeepL APIの利用制限に注意してください
- 翻訳結果は必ず内容を確認してから使用してください

## ライセンス

このツールは教育・研究目的で作成されています。商用利用時は適切なライセンスを確認してください。