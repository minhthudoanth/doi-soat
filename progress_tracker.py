import threading
from datetime import datetime

_LOCK = threading.Lock()

_PROGRESS = {
    'is_running': False,
    'total': 0,
    'current': 0,
    'percent': 0,
    'current_store': '',
    'status_text': 'Sẵn sàng',
    'success_count': 0,
    'failed_count': 0,
    'logs': [],
    'batch_id': '',
    'updated_at': ''
}

def reset_broadcast_progress(total=0, batch_id=''):
    global _PROGRESS
    with _LOCK:
        now_str = datetime.now().strftime('%H:%M:%S')
        _PROGRESS = {
            'is_running': True,
            'total': total,
            'current': 0,
            'percent': 0,
            'current_store': '',
            'status_text': f'Đang kết nối Telegram, chuẩn bị gửi {total} Siêu thị...',
            'success_count': 0,
            'failed_count': 0,
            'logs': [f"[{now_str}] 🚀 Bắt đầu phát sóng đến {total} Siêu thị..."],
            'batch_id': batch_id,
            'updated_at': now_str
        }

def update_broadcast_progress(current, total, store_desc='', status_text='', success_count=0, failed_count=0, log_entry=None):
    global _PROGRESS
    with _LOCK:
        now_str = datetime.now().strftime('%H:%M:%S')
        pct = round((current / total * 100) if total > 0 else 0)
        _PROGRESS['is_running'] = (current < total) if total > 0 else False
        _PROGRESS['total'] = total
        _PROGRESS['current'] = current
        _PROGRESS['percent'] = min(pct, 100)
        if store_desc:
            _PROGRESS['current_store'] = store_desc
        if status_text:
            _PROGRESS['status_text'] = status_text
        _PROGRESS['success_count'] = success_count
        _PROGRESS['failed_count'] = failed_count
        _PROGRESS['updated_at'] = now_str
        if log_entry:
            _PROGRESS['logs'].append(log_entry)
            if len(_PROGRESS['logs']) > 70:
                _PROGRESS['logs'] = _PROGRESS['logs'][-70:]

def finish_broadcast_progress(success_count=0, failed_count=0):
    global _PROGRESS
    with _LOCK:
        now_str = datetime.now().strftime('%H:%M:%S')
        total = _PROGRESS.get('total', 0)
        _PROGRESS['is_running'] = False
        _PROGRESS['current'] = total
        _PROGRESS['percent'] = 100
        _PROGRESS['status_text'] = f"✅ Hoàn tất phát sóng! Đã gửi {success_count}/{total} Siêu thị."
        _PROGRESS['success_count'] = success_count
        _PROGRESS['failed_count'] = failed_count
        _PROGRESS['updated_at'] = now_str
        _PROGRESS['logs'].append(f"[{now_str}] 🏁 Hoàn tất: {success_count} thành công, {failed_count} lỗi.")

def get_broadcast_progress():
    with _LOCK:
        return dict(_PROGRESS)
