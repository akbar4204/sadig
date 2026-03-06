"""Middleware untuk menyimpan user aktif di thread-local.

Tujuan: audit log (signals) bisa mengetahui siapa yang melakukan perubahan.
"""

import threading
from typing import Optional

_local = threading.local()

def get_current_user() -> Optional[object]:
    return getattr(_local, "user", None)

class CurrentUserMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        try:
            _local.user = getattr(request, "user", None)
        except Exception:
            _local.user = None

        response = self.get_response(request)

        _local.user = None
        return response
