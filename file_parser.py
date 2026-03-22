"""
📄 Tempo Bot — Парсер файлов с расписанием
Поддерживаемые форматы: TXT, CSV, XLSX, PDF (текст)
"""

import os
import pandas as pd
from PyPDF2 import PdfReader
from typing import List, Dict


def parse_text_file(file_path: str) -> str:
    """Чтение текстового файла"""
    if not os.path.exists(file_path):
        return ""
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        return content
    except Exception as e:
        return f"Ошибка чтения: {str(e)}"


def parse_csv_file(file_path: str) -> str:
    """Чтение CSV файла"""
    if not os.path.exists(file_path):
        return ""
    
    try:
        df = pd.read_csv(file_path, encoding='utf-8')
        
        content = "📋 Расписание из CSV:\n\n"
        for _, row in df.iterrows():
            if 'day' in df.columns and 'task' in df.columns:
                day = row.get('day', '')
                task = row.get('task', '')
                hours = row.get('hours', row.get('duration', ''))
                content += f"{day}: {task} ({hours}ч)\n"
            else:
                content += " | ".join(str(v) for v in row.values) + "\n"
        
        return content
    except Exception as e:
        return f"Ошибка чтения CSV: {str(e)}"


def parse_excel_file(file_path: str) -> str:
    """Чтение Excel файла"""
    if not os.path.exists(file_path):
        return ""
    
    try:
        df = pd.read_excel(file_path, engine='openpyxl')
        
        content = "📊 Расписание из Excel:\n\n"
        for _, row in df.iterrows():
            if 'day' in df.columns and 'task' in df.columns:
                day = row.get('day', '')
                task = row.get('task', '')
                hours = row.get('hours', row.get('duration', ''))
                content += f"{day}: {task} ({hours}ч)\n"
            else:
                content += " | ".join(str(v) for v in row.values) + "\n"
        
        return content
    except Exception as e:
        return f"Ошибка чтения Excel: {str(e)}"


def parse_pdf_file(file_path: str) -> str:
    """Чтение PDF файла (только текст, без картинок)"""
    if not os.path.exists(file_path):
        return ""
    
    try:
        reader = PdfReader(file_path)
        content = "📄 Расписание из PDF:\n\n"
        
        if len(reader.pages) == 0:
            return "PDF пустой"
        
        for page in reader.pages:
            text = page.extract_text()
            if text:
                content += text + "\n"
        
        if len(content.strip()) < 50:
            return "⚠️ PDF содержит мало текста. Возможно, это скан изображения."
        
        return content
    except Exception as e:
        return f"Ошибка чтения PDF: {str(e)}"


def parse_file(file_path: str, file_type: str) -> str:
    """Универсальный парсер файлов"""
    parsers = {
        'txt': parse_text_file,
        'csv': parse_csv_file,
        'xlsx': parse_excel_file,
        'xls': parse_excel_file,
        'pdf': parse_pdf_file
    }
    
    file_type = file_type.lower().strip('.')
    
    if file_type in parsers:
        return parsers[file_type](file_path)
    else:
        return f"❌ Неподдерживаемый формат: {file_type}"


def validate_file(file_path: str, max_size_mb: int = 10) -> Dict:
    """Валидация файла перед загрузкой"""
    result = {
        'valid': False,
        'error': None,
        'size_mb': 0,
        'type': None
    }
    
    if not os.path.exists(file_path):
        result['error'] = "Файл не найден"
        return result
    
    size_mb = os.path.getsize(file_path) / (1024 * 1024)
    result['size_mb'] = size_mb
    
    if size_mb > max_size_mb:
        result['error'] = f"Файл слишком большой ({size_mb:.1f} МБ)"
        return result
    
    allowed_extensions = ['.txt', '.csv', '.xlsx', '.xls', '.pdf']
    ext = os.path.splitext(file_path)[1].lower()
    
    if ext not in allowed_extensions:
        result['error'] = f"Неподдерживаемый формат: {ext}"
        return result
    
    result['valid'] = True
    result['type'] = ext[1:]
    return result