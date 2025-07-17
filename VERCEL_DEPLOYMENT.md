# Excel翻訳ツール - Vercelデプロイガイド

## 概要
このガイドでは、Excel翻訳ツールをVercelに簡単にデプロイする方法を説明します。

## 前提条件
- GitHub アカウント
- Vercel アカウント
- DeepL API キー

## 1. GitHubリポジトリの準備

### 1.1 リポジトリの作成
```bash
# 新しいリポジトリを作成
git init
git add .
git commit -m "Initial commit: Excel翻訳ツール"

# GitHubリポジトリを作成し、プッシュ
git remote add origin https://github.com/your-username/excel-translator.git
git push -u origin main
```

### 1.2 必要ファイルの確認
以下のファイルがプロジェクトに含まれていることを確認：
- `vercel.json` - Vercel設定
- `api/index.py` - Vercel用のFlaskアプリケーション
- `requirements.txt` - Python依存関係
- `templates/` - HTMLテンプレート
- `excel_translator.py` - 翻訳エンジン

## 2. Vercelでのデプロイ

### 2.1 Vercelにプロジェクトをインポート
1. [Vercel](https://vercel.com) にログイン
2. 「New Project」をクリック
3. GitHubリポジトリを選択
4. プロジェクト名を設定（例：`excel-translator`）

### 2.2 環境変数の設定
Vercelダッシュボードで以下の環境変数を設定：

| 変数名 | 値 | 説明 |
|--------|-----|------|
| `DEEPL_API_KEY` | `your-deepl-api-key` | DeepL APIキー |
| `SECRET_KEY` | `your-secret-key` | Flask用のシークレットキー |

設定方法：
1. Vercelダッシュボードのプロジェクト設定
2. 「Environment Variables」タブ
3. 変数を追加

### 2.3 デプロイ実行
1. 「Deploy」ボタンをクリック
2. ビルドプロセスが完了するまで待機
3. デプロイ完了後、URLが表示される

## 3. ローカルでのテスト

### 3.1 Vercel CLIのインストール
```bash
npm install -g vercel
```

### 3.2 ローカルでの実行
```bash
# Vercelの設定
vercel login

# ローカルでの実行
vercel dev
```

## 4. 自動デプロイの設定

### 4.1 GitHubとの連携
- mainブランチにプッシュすると自動デプロイ
- プルリクエストでプレビューデプロイ

### 4.2 デプロイフック
```bash
# 手動デプロイ
vercel --prod

# 特定のブランチのデプロイ
vercel --prod --target production
```

## 5. カスタムドメインの設定

### 5.1 独自ドメインの追加
1. Vercelダッシュボード > Domains
2. 「Add Domain」をクリック
3. ドメイン名を入力
4. DNS設定を更新

### 5.2 SSL証明書
- Vercelが自動的にSSL証明書を提供
- HTTPSが自動的に有効化

## 6. 監視とデバッグ

### 6.1 ログの確認
```bash
# リアルタイムログ
vercel logs

# 特定のデプロイのログ
vercel logs [deployment-url]
```

### 6.2 パフォーマンス監視
- Vercel Analytics で使用状況を確認
- Function実行時間とメモリ使用量を監視

## 7. トラブルシューティング

### 7.1 一般的な問題と解決策

**問題**: モジュールが見つからない
```
ModuleNotFoundError: No module named 'excel_translator'
```
**解決策**: `api/index.py`でパスを正しく設定

**問題**: 環境変数が読み込まれない
**解決策**: Vercelダッシュボードで環境変数を再確認

**問題**: ファイルアップロードが失敗する
**解決策**: ファイルサイズ制限（16MB）を確認

### 7.2 デバッグ方法
```python
# api/index.py にデバッグコードを追加
import os
print(f"DEEPL_API_KEY: {os.environ.get('DEEPL_API_KEY')[:10]}...")
```

## 8. 制限事項

### 8.1 Vercel制限
- 関数実行時間: 最大60秒
- メモリ使用量: 最大1GB
- ファイルサイズ: 最大16MB

### 8.2 回避策
- 大きなファイルは分割処理
- 時間のかかる処理は最適化

## 9. 本番環境での最適化

### 9.1 パフォーマンス最適化
```python
# キャッシュの追加
@app.route('/api/translate', methods=['POST'])
@cache.cached(timeout=300)  # 5分間キャッシュ
def api_translate():
    # 翻訳処理
```

### 9.2 セキュリティ強化
```python
# レート制限の追加
from flask_limiter import Limiter

limiter = Limiter(
    app,
    key_func=lambda: request.remote_addr,
    default_limits=["10 per minute"]
)
```

## 10. 更新とメンテナンス

### 10.1 アップデート手順
```bash
# 変更をコミット
git add .
git commit -m "Update: 新機能追加"
git push origin main

# 自動的にVercelでデプロイされる
```

### 10.2 ロールバック
```bash
# 以前のデプロイメントに戻す
vercel rollback [deployment-url]
```

## 11. コスト管理

### 11.1 使用量監視
- Vercel Analytics で使用状況を確認
- 月次使用量レポートを確認

### 11.2 最適化
- 不要な機能の削除
- 効率的なコードの実装

## 完了

これでExcel翻訳ツールがVercelに公開されました！

**アクセス方法:**
- 公開URL: `https://your-project-name.vercel.app`
- カスタムドメイン: `https://your-domain.com`

**次のステップ:**
1. 動作確認
2. 独自ドメインの設定
3. 監視とメンテナンス

問題が発生した場合は、Vercelのログを確認し、必要に応じて設定を調整してください。