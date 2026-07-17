"""起動前に管理者認証情報の設定状況を確認する。

使い方: python scripts/check_credentials.py [lan|internet]

- lan: 認証情報が未設定でも警告のみで起動を継続する（従来のLAN専用挙動との互換用）。
- internet: 認証情報が未設定なら起動を中止する（インターネット公開では認証必須）。
"""

from __future__ import annotations

import os
import sys


def main() -> int:
    mode = sys.argv[1] if len(sys.argv) > 1 else "lan"
    username = os.environ.get("PARKING_ADMIN_USERNAME")
    password = os.environ.get("PARKING_ADMIN_PASSWORD")
    configured = bool(username and password)

    if configured:
        print(f"[auth] 管理者認証: 有効（ユーザー名: {username}）")
        return 0

    if mode == "internet":
        print(
            "\n"
            "==================================================================\n"
            " エラー: インターネット公開には管理者認証の設定が必須です。\n"
            "\n"
            " set_credentials.bat を実行してユーザー名とパスワードを設定してから\n"
            " もう一度 run_internet.bat を実行してください。\n"
            "==================================================================\n",
            file=sys.stderr,
        )
        return 1

    print(
        "\n"
        "[警告] 管理者認証が設定されていません。同じネットワーク内の誰でも駐車枠の\n"
        "        変更や画像アップロードができる状態です。set_credentials.bat を実行して\n"
        "        認証を設定することを推奨します。\n"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
