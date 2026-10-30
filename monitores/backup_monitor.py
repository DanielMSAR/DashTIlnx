import os
import platform
import asyncio
from datetime import datetime
from pathlib import Path

BACKUP_DIR = os.environ.get('BACKUP_DIR', '/mnt/backup_remoto')
MAX_AGE_DAYS = 10

def _get_backup_files_sync(directory: str = BACKUP_DIR, max_age_days: int = MAX_AGE_DAYS) -> dict:
    """Escanea el directorio de backups de forma sincrónica."""
    files_info = []
    has_alert = False
    now = datetime.now()
    dir_path = Path(directory)
    
    try:
        if not dir_path.exists():
            return {
                'status': 'ERROR',
                'message': f'No se pudo acceder a {directory}',
                'files': [],
                'has_alert': True,
                'last_check': now.strftime('%H:%M:%S')
            }

        # En Linux, verificar que el directorio sea efectivamente un punto de montaje activo
        if platform.system().lower() != 'windows' and not os.path.ismount(dir_path):
            return {
                'status': 'ERROR',
                'message': f'El recurso remoto no está montado en {directory}',
                'files': [],
                'has_alert': True,
                'last_check': now.strftime('%H:%M:%S')
            }

        for entry in os.scandir(directory):
            if entry.is_file() and entry.name.lower().endswith('.sql'):
                stat = entry.stat()
                mtime = datetime.fromtimestamp(stat.st_mtime)
                age = now - mtime
                age_days = age.days
                
                # Tamaño formateado
                size_bytes = stat.st_size
                if size_bytes >= 1024 ** 3:
                    size_str = f"{size_bytes / (1024 ** 3):.2f} GB"
                elif size_bytes >= 1024 ** 2:
                    size_str = f"{size_bytes / (1024 ** 2):.1f} MB"
                else:
                    size_str = f"{size_bytes / 1024:.1f} KB"
                
                is_outdated = age_days > max_age_days
                if is_outdated:
                    has_alert = True
                    
                files_info.append({
                    'name': entry.name,
                    'size': size_str,
                    'mtime': mtime.strftime('%d/%m/%Y %H:%M'),
                    'mtime_dt': mtime,
                    'age_days': age_days,
                    'is_outdated': is_outdated
                })

        if not files_info:
            return {
                'status': 'ERROR',
                'message': f'No se encontraron archivos .sql en {directory}',
                'files': [],
                'has_alert': True,
                'last_check': now.strftime('%H:%M:%S')
            }
                
        # Ordenar por fecha de modificación (más reciente primero)
        files_info.sort(key=lambda x: x['mtime_dt'], reverse=True)
        
        return {
            'status': 'ALERTA' if has_alert else 'OK',
            'message': 'Supervisión de respaldos SQL',
            'files': files_info,
            'has_alert': has_alert,
            'last_check': now.strftime('%H:%M:%S')
        }
    except Exception as e:
        return {
            'status': 'ERROR',
            'message': f'Error al leer directorio: {str(e)}',
            'files': [],
            'has_alert': True,
            'last_check': now.strftime('%H:%M:%S')
        }

async def check_backup_files(directory: str = BACKUP_DIR, max_age_days: int = MAX_AGE_DAYS) -> dict:
    """Ejecuta el escaneo de archivos de backup en un hilo para no bloquear asyncio."""
    return await asyncio.to_thread(_get_backup_files_sync, directory, max_age_days)
