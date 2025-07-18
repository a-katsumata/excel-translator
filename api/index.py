from flask import Flask, jsonify, request, render_template, send_file
import os
import sys
import openpyxl
import requests
import io
import tempfile
from urllib.parse import quote
import re
from datetime import datetime

# パスを追加
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

app = Flask(__name__, template_folder='../templates')
app.secret_key = os.environ.get('SECRET_KEY', 'excel-translator-secret-key')

def should_translate_cell(cell_value):
    """セルの内容を分析して翻訳が必要かどうかを判定"""
    if not cell_value:
        return False
    
    # 文字列以外は翻訳しない
    if not isinstance(cell_value, str):
        return False
    
    # 空白文字のみは翻訳しない
    if not cell_value.strip():
        return False
    
    # 数値のみの場合は翻訳しない
    if re.match(r'^[\d\s,.\-+%$€¥]+$', cell_value.strip()):
        return False
    
    # 日付形式の場合は翻訳しない
    date_patterns = [
        r'^\d{4}[-/]\d{1,2}[-/]\d{1,2}$',  # 2023-12-31, 2023/12/31
        r'^\d{1,2}[-/]\d{1,2}[-/]\d{4}$',  # 31-12-2023, 31/12/2023
        r'^\d{4}年\d{1,2}月\d{1,2}日$',     # 2023年12月31日
    ]
    
    for pattern in date_patterns:
        if re.match(pattern, cell_value.strip()):
            return False
    
    # 数式の場合は翻訳しない
    if cell_value.startswith('='):
        return False
    
    # URLの場合は翻訳しない
    if re.match(r'^https?://', cell_value.strip()):
        return False
    
    # メールアドレスの場合は翻訳しない
    if re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', cell_value.strip()):
        return False
    
    # 長すぎる場合は翻訳しない（API制限回避）
    if len(cell_value) > 5000:
        return False
    
    # 短すぎる場合（1文字）で日本語/中国語/韓国語でない場合は翻訳しない
    if len(cell_value.strip()) == 1:
        if not re.match(r'[ひらがなカタカナ漢字가-힣]', cell_value):
            return False
    
    return True

def generate_context_from_headers(sheet, cell_row, cell_col):
    """ヘッダー情報から文脈を生成"""
    context_parts = []
    
    # 同じ行の左側のセルから文脈を取得（見出し）
    for col in range(max(1, cell_col - 3), cell_col):
        if col < cell_col:
            header_cell = sheet.cell(row=cell_row, column=col)
            if header_cell.value and isinstance(header_cell.value, str):
                context_parts.append(header_cell.value)
    
    # 同じ列の上側のセルから文脈を取得（カラムヘッダー）
    for row in range(max(1, cell_row - 3), cell_row):
        if row < cell_row:
            header_cell = sheet.cell(row=row, column=cell_col)
            if header_cell.value and isinstance(header_cell.value, str):
                context_parts.append(header_cell.value)
    
    return ' '.join(context_parts[:5])  # 最大5つの要素で文脈を作成

def analyze_sheet_structure(sheet):
    """シート構造を分析して翻訳単位を決定"""
    # シートの全セルを取得
    all_cells = []
    for row in sheet.iter_rows():
        for cell in row:
            if cell.value is not None:
                all_cells.append({
                    'row': cell.row,
                    'column': cell.column,
                    'value': cell.value,
                    'coordinate': cell.coordinate
                })
    
    # ヘッダー行を特定（最初の数行でテキストが多い行）
    header_rows = []
    for row_num in range(1, min(6, sheet.max_row + 1)):
        text_cells = 0
        for col_num in range(1, sheet.max_column + 1):
            cell = sheet.cell(row=row_num, column=col_num)
            if cell.value and isinstance(cell.value, str) and len(cell.value.strip()) > 0:
                text_cells += 1
        if text_cells >= sheet.max_column * 0.5:  # 50%以上がテキスト
            header_rows.append(row_num)
    
    # データ領域を特定
    data_start_row = max(header_rows) + 1 if header_rows else 1
    
    return {
        'header_rows': header_rows,
        'data_start_row': data_start_row,
        'total_cells': len(all_cells),
        'max_row': sheet.max_row,
        'max_column': sheet.max_column
    }

def create_sheet_context(sheet, structure):
    """シート全体の文脈を作成"""
    context_parts = []
    
    # シート名を文脈に追加
    if sheet.title:
        context_parts.append(f"シート名: {sheet.title}")
    
    # ヘッダー行から文脈を作成
    for header_row in structure['header_rows']:
        header_texts = []
        for col_num in range(1, min(sheet.max_column + 1, 10)):  # 最大10列
            cell = sheet.cell(row=header_row, column=col_num)
            if cell.value and isinstance(cell.value, str):
                header_texts.append(cell.value)
        if header_texts:
            context_parts.append(' | '.join(header_texts))
    
    return '. '.join(context_parts)

def create_cell_mapping(sheet):
    """セルの位置と内容のマッピングを作成"""
    cell_mapping = {}
    translation_tasks = []
    
    for row in range(1, sheet.max_row + 1):
        for col in range(1, sheet.max_column + 1):
            cell = sheet.cell(row=row, column=col)
            cell_key = f"{row}_{col}"
            
            # セルの情報を保存
            cell_mapping[cell_key] = {
                'row': row,
                'col': col,
                'coordinate': cell.coordinate,
                'original_value': cell.value,
                'needs_translation': should_translate_cell(cell.value),
                'cell_object': cell
            }
            
            # 翻訳が必要なセルを翻訳タスクに追加
            if should_translate_cell(cell.value):
                translation_tasks.append({
                    'cell_key': cell_key,
                    'text': str(cell.value),
                    'context': generate_context_from_headers(sheet, row, col)
                })
    
    return cell_mapping, translation_tasks

def translate_with_context_preservation(translation_tasks, sheet, context, target_lang, source_lang, formality, api_key):
    """文脈を保持しながら翻訳を実行"""
    if not translation_tasks:
        return {}
    
    # シート全体の概要を文脈として作成
    sheet_context = f"シート名: {sheet.title}. " if sheet.title else ""
    
    # ヘッダー行の情報を文脈に追加
    header_info = []
    for row in range(1, min(4, sheet.max_row + 1)):
        row_texts = []
        for col in range(1, min(sheet.max_column + 1, 10)):
            cell = sheet.cell(row=row, column=col)
            if cell.value and isinstance(cell.value, str):
                row_texts.append(str(cell.value))
        if row_texts:
            header_info.append(" | ".join(row_texts))
    
    if header_info:
        sheet_context += "ヘッダー情報: " + "; ".join(header_info) + ". "
    
    # 全体文脈を作成
    full_context = f"{context}. {sheet_context}" if context else sheet_context
    
    # 翻訳タスクを小さなバッチに分割
    batch_size = 50
    translations = {}
    
    for i in range(0, len(translation_tasks), batch_size):
        batch_tasks = translation_tasks[i:i + batch_size]
        batch_texts = [task['text'] for task in batch_tasks]
        
        # 各バッチの文脈を強化
        batch_context = full_context
        if batch_tasks:
            # バッチ内の文脈情報を追加
            local_contexts = [task['context'] for task in batch_tasks if task['context']]
            if local_contexts:
                batch_context += " ローカル文脈: " + "; ".join(local_contexts[:3])
        
        try:
            translated_batch = translate_batch(
                batch_texts,
                target_lang,
                source_lang,
                batch_context,
                api_key,
                formality
            )
            
            # 翻訳結果をマッピング
            for j, task in enumerate(batch_tasks):
                if j < len(translated_batch):
                    translations[task['cell_key']] = translated_batch[j]
                    
        except Exception as e:
            print(f"Translation batch error: {str(e)}")
            # エラーの場合は元のテキストを保持
            for task in batch_tasks:
                translations[task['cell_key']] = task['text']
    
    return translations

def apply_translations_to_sheet(sheet, cell_mapping, translations):
    """翻訳結果をシートに適用"""
    for cell_key, translation in translations.items():
        if cell_key in cell_mapping:
            cell_info = cell_mapping[cell_key]
            if cell_info['needs_translation']:
                cell_info['cell_object'].value = translation

def preserve_merged_cells(sheet):
    """結合セルの情報を保存"""
    merged_ranges = []
    for merged_range in sheet.merged_cells.ranges:
        merged_ranges.append(str(merged_range))
    return merged_ranges

def restore_merged_cells(sheet, merged_ranges):
    """結合セルの情報を復元"""
    for merged_range in merged_ranges:
        try:
            sheet.merge_cells(merged_range)
        except Exception as e:
            print(f"Failed to restore merged cell {merged_range}: {str(e)}")

def validate_translation_accuracy(sheet, cell_mapping, translations):
    """翻訳の正確性を検証"""
    validation_results = {
        'total_cells': len(cell_mapping),
        'cells_needing_translation': 0,
        'cells_translated': 0,
        'cells_preserved': 0,
        'errors': []
    }
    
    for cell_key, cell_info in cell_mapping.items():
        if cell_info['needs_translation']:
            validation_results['cells_needing_translation'] += 1
            
            if cell_key in translations:
                validation_results['cells_translated'] += 1
                
                # 翻訳結果の妥当性チェック
                original = cell_info['original_value']
                translated = translations[cell_key]
                
                # 明らかに不適切な翻訳の検出
                if len(str(translated)) == 0 and len(str(original)) > 0:
                    validation_results['errors'].append(f"Empty translation for cell {cell_info['coordinate']}")
                elif len(str(translated)) > len(str(original)) * 10:
                    validation_results['errors'].append(f"Suspiciously long translation for cell {cell_info['coordinate']}")
            else:
                validation_results['errors'].append(f"Missing translation for cell {cell_info['coordinate']}")
        else:
            validation_results['cells_preserved'] += 1
    
    return validation_results

@app.route('/')
def index():
    try:
        return render_template('index.html')
    except Exception as e:
        return jsonify({
            'error': 'Template error',
            'message': str(e),
            'working_directory': os.getcwd(),
            'template_folder': app.template_folder,
            'files_in_templates': os.listdir(os.path.join(parent_dir, 'templates')) if os.path.exists(os.path.join(parent_dir, 'templates')) else 'templates directory not found'
        }), 500

@app.route('/health')
def health():
    return jsonify({
        'status': 'healthy',
        'service': 'excel-translator',
        'python_version': sys.version,
        'working_directory': os.getcwd(),
        'parent_directory': parent_dir,
        'current_directory': current_dir,
        'template_folder': app.template_folder,
        'environment_variables': list(os.environ.keys()),
        'deepl_api_key_exists': bool(os.environ.get('DEEPL_API_KEY')),
        'files_in_current_dir': os.listdir(os.getcwd()),
        'files_in_parent_dir': os.listdir(parent_dir) if os.path.exists(parent_dir) else 'parent directory not found'
    })

def translate_batch(texts, target_lang, source_lang, context, api_key, formality=None):
    """DeepL APIを使用して複数のテキストを一括翻訳"""
    if not texts:
        return []
    
    # 空のテキストを除外し、インデックスを記録
    non_empty_texts = []
    text_indices = []
    
    for i, text in enumerate(texts):
        if text and text.strip():
            non_empty_texts.append(text)
            text_indices.append(i)
    
    if not non_empty_texts:
        return texts
    
    url = "https://api-free.deepl.com/v2/translate"
    
    data = {
        'auth_key': api_key,
        'text': non_empty_texts,
        'target_lang': target_lang,
        'source_lang': source_lang if source_lang != 'auto' else None
    }
    
    if context:
        data['context'] = context
    
    # フォーマリティの設定
    if formality and formality != 'default':
        data['formality'] = formality
    
    # 常に高品質モードを使用
    data['model_type'] = 'quality_optimized'
    
    response = requests.post(url, data=data)
    
    if response.status_code == 200:
        result = response.json()
        translated_texts = [t['text'] for t in result['translations']]
        
        # 結果を元の配列に戻す
        final_results = list(texts)
        for i, translated_text in enumerate(translated_texts):
            final_results[text_indices[i]] = translated_text
        
        return final_results
    else:
        raise Exception(f"DeepL API error: {response.status_code} - {response.text}")

@app.route('/api/translate', methods=['POST'])
def api_translate():
    try:
        # 環境変数チェック
        deepl_api_key = os.environ.get('DEEPL_API_KEY')
        if not deepl_api_key:
            return jsonify({'error': 'DEEPL_API_KEY not found in environment variables'}), 500
        
        # ファイルチェック
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        # パラメータ取得
        source_lang = request.form.get('source_lang', 'JA')
        target_lang = request.form.get('target_lang', 'EN-US')
        context = request.form.get('context', '')
        formality = request.form.get('formality', 'default')
        
        # Excelファイルを読み込み
        wb = openpyxl.load_workbook(io.BytesIO(file.read()))
        
        # 全シートを新しいセル対応保証アルゴリズムで処理
        for sheet_name in wb.sheetnames:
            sheet = wb[sheet_name]
            
            # 結合セルの情報を保存
            merged_ranges = preserve_merged_cells(sheet)
            
            # セルマッピングと翻訳タスクを作成
            cell_mapping, translation_tasks = create_cell_mapping(sheet)
            
            # 翻訳の実行
            translations = translate_with_context_preservation(
                translation_tasks,
                sheet,
                context,
                target_lang,
                source_lang,
                formality,
                deepl_api_key
            )
            
            # 翻訳結果をシートに適用
            apply_translations_to_sheet(sheet, cell_mapping, translations)
            
            # 翻訳の正確性を検証
            validation_results = validate_translation_accuracy(sheet, cell_mapping, translations)
            if validation_results['errors']:
                print(f"Validation errors for sheet {sheet_name}: {validation_results['errors']}")
            
            # 結合セルを復元
            restore_merged_cells(sheet, merged_ranges)
        
        # 翻訳されたファイルを一時ファイルに保存
        with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp_file:
            wb.save(tmp_file.name)
            tmp_file_path = tmp_file.name
        
        # ファイル名を生成（翻訳済みの接頭辞を追加）
        original_filename = file.filename
        name, ext = os.path.splitext(original_filename)
        translated_filename = f"{name}_translated{ext}"
        
        # ファイルをダウンロード用に送信
        return send_file(
            tmp_file_path,
            as_attachment=True,
            download_name=translated_filename,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Vercel用のエクスポート
def app_handler(environ, start_response):
    return app(environ, start_response)

# Vercel用のapp変数をエクスポート
if __name__ == '__main__':
    app.run(debug=False)