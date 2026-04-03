import os
import shutil
from pathlib import Path
from django.conf import settings
from django.core.files import File
from datetime import datetime
class RecordingManager:
    """Менеджер для работы с записями звонков"""
    
    def __init__(self):
        self.source_path = settings.ASTERISK_RECORDINGS_PATH
        self.dest_path = os.path.join(settings.MEDIA_ROOT, 'call_recordings')
        
    def move_recording(self, filename: str, call_id: int) -> str:
        """Перемещение записи в медиа-директорию"""
        source = os.path.join(self.source_path, filename)
        
        if not os.path.exists(source):
            raise FileNotFoundError(f"Recording not found: {source}")
            
        # Создаем директорию по дате
        date_dir = datetime.now().strftime('%Y/%m/%d')
        dest_dir = os.path.join(self.dest_path, date_dir)
        Path(dest_dir).mkdir(parents=True, exist_ok=True)
        
        # Новое имя файла
        new_filename = f"call_{call_id}_{filename}"
        dest = os.path.join(dest_dir, new_filename)
        
        # Перемещаем файл
        shutil.move(source, dest)
        
        # Возвращаем относительный путь
        return os.path.join('call_recordings', date_dir, new_filename)
        
    def get_recording_url(self, recording_path: str) -> str:
        """Получение URL для записи"""
        if recording_path:
            return f"{settings.MEDIA_URL}{recording_path}"
        return None