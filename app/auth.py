"""HTTPベーシック認証。

環境変数 PARKING_ADMIN_USERNAME / PARKING_ADMIN_PASSWORD が設定されている場合のみ
認証を要求する。未設定時は認証なし（これまで通りのLAN専用・開発用途の挙動を維持する）。

インターネット公開時に認証なしで起動できないようにするチェックは、
scripts/check_credentials.py（起動スクリプト側）で別途行う。
"""

from __future__ import annotations

import os
import secrets

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials

_security = HTTPBasic(auto_error=False)


def _configured_credentials() -> tuple[str, str] | None:
    username = os.environ.get("PARKING_ADMIN_USERNAME")
    password = os.environ.get("PARKING_ADMIN_PASSWORD")
    if not username or not password:
        return None
    return username, password


def auth_enabled() -> bool:
    return _configured_credentials() is not None


def require_auth(
    credentials: HTTPBasicCredentials | None = Depends(_security),  # noqa: B008
) -> None:
    configured = _configured_credentials()
    if configured is None:
        return

    expected_username, expected_password = configured
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="認証が必要です。",
        headers={"WWW-Authenticate": "Basic"},
    )

    if credentials is None:
        raise unauthorized

    username_ok = secrets.compare_digest(credentials.username, expected_username)
    password_ok = secrets.compare_digest(credentials.password, expected_password)
    if not (username_ok and password_ok):
        raise unauthorized
