# Excel翻訳ツール - デプロイメントガイド

## 概要
このガイドでは、Excel翻訳ツールを本番環境にデプロイする手順を説明します。

## 前提条件
- Docker & Docker Compose がインストールされている
- DeepL API キーを取得済み
- 適切なサーバー環境（Linux推奨）

## 1. 環境変数の設定

### 1.1 環境変数ファイルの作成
```bash
cp .env.example .env
```

### 1.2 環境変数の編集
```bash
# .env ファイルを編集
DEEPL_API_KEY=your-actual-deepl-api-key
SECRET_KEY=your-strong-secret-key-here
FLASK_ENV=production
HOST=0.0.0.0
PORT=5000
```

## 2. Dockerを使用したデプロイ

### 2.1 単体でのデプロイ
```bash
# イメージをビルド
docker build -t excel-translator .

# コンテナを起動
docker run -d \
  --name excel-translator \
  -p 5000:5000 \
  --env-file .env \
  excel-translator
```

### 2.2 Docker Composeを使用したデプロイ（推奨）
```bash
# バックグラウンドで起動
docker-compose up -d

# ログを確認
docker-compose logs -f

# 停止
docker-compose down
```

## 3. 手動デプロイ（VPSやクラウドサーバー）

### 3.1 依存関係のインストール
```bash
# 必要なパッケージをインストール
pip install -r requirements.txt
```

### 3.2 Gunicornでの起動
```bash
# 本番環境用の起動
gunicorn --config gunicorn.conf.py app:app
```

### 3.3 systemdサービスの作成（推奨）
```bash
# サービスファイルを作成
sudo nano /etc/systemd/system/excel-translator.service
```

サービスファイルの内容：
```ini
[Unit]
Description=Excel Translator Web Application
After=network.target

[Service]
Type=exec
User=your-user
Group=your-group
WorkingDirectory=/path/to/excel-translator
Environment=PATH=/path/to/venv/bin
EnvironmentFile=/path/to/.env
ExecStart=/path/to/venv/bin/gunicorn --config gunicorn.conf.py app:app
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

サービスの有効化：
```bash
sudo systemctl daemon-reload
sudo systemctl enable excel-translator
sudo systemctl start excel-translator
sudo systemctl status excel-translator
```

## 4. Nginxリバースプロキシの設定

### 4.1 Nginxのインストール
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install nginx

# CentOS/RHEL
sudo yum install nginx
```

### 4.2 Nginxの設定
```bash
sudo nano /etc/nginx/sites-available/excel-translator
```

設定内容：
```nginx
server {
    listen 80;
    server_name your-domain.com;
    
    client_max_body_size 16M;
    
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

設定を有効化：
```bash
sudo ln -s /etc/nginx/sites-available/excel-translator /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

## 5. クラウドプラットフォームでのデプロイ

### 5.1 Heroku
```bash
# Herokuアプリを作成
heroku create your-app-name

# 環境変数を設定
heroku config:set DEEPL_API_KEY=your-api-key
heroku config:set SECRET_KEY=your-secret-key
heroku config:set FLASK_ENV=production

# デプロイ
git push heroku main
```

### 5.2 AWS ECS / Google Cloud Run
Docker Composeファイルをクラウドサービスに適用してデプロイ

### 5.3 DigitalOcean App Platform
```yaml
# app.yaml
name: excel-translator
services:
- name: web
  source_dir: /
  github:
    repo: your-username/excel-translator
    branch: main
  run_command: gunicorn --config gunicorn.conf.py app:app
  environment_slug: python
  instance_count: 1
  instance_size_slug: basic-xxs
  envs:
  - key: DEEPL_API_KEY
    value: your-api-key
    type: SECRET
  - key: SECRET_KEY
    value: your-secret-key
    type: SECRET
```

## 6. SSL証明書の設定

### 6.1 Let's Encryptを使用
```bash
# Certbotのインストール
sudo apt install certbot python3-certbot-nginx

# SSL証明書の取得
sudo certbot --nginx -d your-domain.com

# 自動更新の設定
sudo crontab -e
# 以下を追加
0 12 * * * /usr/bin/certbot renew --quiet
```

## 7. 監視とログ

### 7.1 ログの確認
```bash
# Gunicornログ
tail -f /var/log/excel-translator/gunicorn.log

# Nginxログ
tail -f /var/log/nginx/access.log
tail -f /var/log/nginx/error.log

# Dockerログ
docker-compose logs -f
```

### 7.2 ヘルスチェック
```bash
# ヘルスチェックエンドポイント
curl http://your-domain.com/health
```

## 8. セキュリティ設定

### 8.1 ファイアウォール設定
```bash
# ufw（Ubuntu）
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
```

### 8.2 セキュリティヘッダー（Nginx）
```nginx
add_header X-Frame-Options "SAMEORIGIN" always;
add_header X-Content-Type-Options "nosniff" always;
add_header X-XSS-Protection "1; mode=block" always;
add_header Referrer-Policy "strict-origin-when-cross-origin" always;
```

## 9. バックアップ

### 9.1 データベースバックアップ（該当する場合）
```bash
# 定期的なバックアップスクリプト
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
docker exec excel-translator-db pg_dump -U user dbname > backup_$DATE.sql
```

## 10. トラブルシューティング

### 10.1 一般的な問題
- ポート5000が使用中 → 他のプロセスを停止するか、ポートを変更
- DeepL API制限 → APIキーの制限を確認
- メモリ不足 → サーバーのメモリを増やすか、ワーカー数を調整

### 10.2 ログの確認方法
```bash
# アプリケーションログ
docker-compose logs excel-translator

# システムログ
journalctl -u excel-translator -f
```

## 11. 性能最適化

### 11.1 Gunicornワーカー数の調整
```python
# gunicorn.conf.py
workers = min(multiprocessing.cpu_count() * 2 + 1, 4)
```

### 11.2 Nginxキャッシュ設定
```nginx
location ~* \.(css|js|png|jpg|jpeg|gif|ico|svg)$ {
    expires 1y;
    add_header Cache-Control "public, immutable";
}
```

## 完了
これで Excel翻訳ツールが本番環境にデプロイされました。定期的にログを確認し、必要に応じて設定を調整してください。