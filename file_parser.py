import os
from typing import Dict

# optional зависимости
try:
    import pandas as pd
except:
    pd = None

try:
    from PyPDF2 import PdfReader
except:
    PdfReader = None


# ===== TXT =====

def parse_text_file(file_path: str) -> str:
    if not os.path.exists(file_path):
        return "❌ Файл не найден"

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        return f"❌ Ошибка чтения TXT: {str(e)}"


# ===== CSV =====

def parse_csv_file(file_path: str) -> str:
    if not os.path.exists(file_path):
        return "❌ Файл не найден"

    if pd is None:
        return "❌ pandas не установлен"

    try:
        df = pd.read_csv(file_path)

        if df.empty:
            return "⚠️ CSV файл пустой"

        content = "📋 CSV:\n\n"
        for _, row in df.iterrows():
            content += " | ".join(str(v) for v in row.values) + "\n"

        return content

    except Exception as e:
        return f"❌ Ошибка чтения CSV: {str(e)}"


# ===== EXCEL =====

def parse_excel_file(file_path: str) -> str:
    if not os.path.exists(file_path):
        return "❌ Файл не найден"

    if pd is None:
        return "❌ pandas не установлен"

    try:
        df = pd.read_excel(file_path)

        if df.empty:
            return "⚠️ Excel файл пустой"

        content = "📊 Excel:\n\n"
        for _, row in df.iterrows():
            content += " | ".join(str(v) for v in row.values) + "\n"

        return content

    except Exception as e:
        return f"❌ Ошибка чтения Excel: {str(e)}"


# ===== PDF =====

def parse_pdf_file(file_path: str) -> str:
    if not os.path.exists(file_path):
        return "❌ Файл не найден"

    if PdfReader is None:
        return "❌ PyPDF2 не установлен"

    try:
        reader = PdfReader(file_path)

        if not reader.pages:
            return "⚠️ PDF пустой"

        text = ""
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"

        if not text.strip():
            return "⚠️ PDF без текста (возможно скан)"

        return text

    except Exception as e:
        return f"❌ Ошибка чтения PDF: {str(e)}"


# ===== ОБЩИЙ ПАРСЕР =====

def parse_file(file_path: str, file_type: str) -> str:
    file_type = file_type.lower().replace('.', '')

    parsers = {
        'txt': parse_text_file,
        'csv': parse_csv_file,
        'xlsx': parse_excel_file,
        'xls': parse_excel_file,
        'pdf': parse_pdf_file
    }

    parser = parsers.get(file_type)

    if not parser:
        return f"❌ Формат не поддерживается: {file_type}"

    return parser(file_path)


# ===== ВАЛИДАЦИЯ =====

def validate_file(file_path: str, max_size_mb: int = 10) -> Dict:
    if not os.path.exists(file_path):
        return {'valid': False, 'error': 'Файл не найден'}

    try:
        size_mb = os.path.getsize(file_path) / (1024 * 1024)
    except:
        return {'valid': False, 'error': 'Ошибка чтения файла'}

    if size_mb > max_size_mb:
        return {'valid': False, 'error': f'Файл слишком большой ({size_mb:.1f} МБ)'}

    ext = os.path.splitext(file_path)[1].lower()

    allowed = ['.txt', '.csv', '.xlsx', '.xls', '.pdf']

    if ext not in allowed:
        return {'valid': False, 'error': f'Неподдерживаемый формат {ext}'}

    return {
        'valid': True,
        'type': ext.replace('.', ''),
        'size_mb': size_mb
    }