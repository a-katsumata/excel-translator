# Gunicorn設定ファイル
import multiprocessing
import os

# サーバーソケット
bind = f"0.0.0.0:{os.environ.get('PORT', '5000')}"
backlog = 2048

# ワーカー設定
workers = min(multiprocessing.cpu_count() * 2 + 1, 4)
worker_class = "sync"
worker_connections = 1000
timeout = 300
keepalive = 2
max_requests = 1000
max_requests_jitter = 50

# セキュリティ
limit_request_line = 4094
limit_request_fields = 100
limit_request_field_size = 8190

# プロセス名
proc_name = "excel_translator"

# ログ設定
accesslog = "-"
errorlog = "-"
loglevel = "info"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s"'

# リロード
reload = False

# プリロード
preload_app = True

# 一時ディレクトリ
tmp_upload_dir = None