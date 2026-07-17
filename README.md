# 駐車場空き台数カウントシステム（MVP）

余っているAndroidスマートフォンを固定カメラ代わりに使い、駐車場の空き台数を
低コストで判定するための実験的なシステムです。

## 1. このシステムの目的

商用の完成品ではなく、**「安く・小さく作って、実運用できそうか確認する」ための
MVP（実用最小限の製品）** です。クラウドやAI APIを使わず、Windows PC上の
PythonとOpenCVによる画像差分だけで「空き／使用中／判定不能」を判定します。

## 2. システム構成

```text
Androidスマートフォン（カメラ）
    ↓ 一定間隔でブラウザから静止画をアップロード
Windows PC上のPythonサーバー（FastAPI + Uvicorn）
    ↓ OpenCVで駐車枠ごとに空き・使用中を判定
    ↓ 3回連続で同じ判定が出たら状態を確定
ブラウザのダッシュボードに空き台数を表示
    ↓
SQLiteに判定結果（時刻・台数・枠ごとの状態）のみを保存
```

- 元の駐車場画像は保存しません（判定に使うのはメモリ上だけ）。
- 基準画像として保存するのは、駐車枠を切り出した小さな画像だけです。
- ナンバープレート認識・顔認識・人物認識は一切行いません。
- 同じWi-Fi内での利用（`run.bat`）と、Cloudflare Tunnelを使ったインターネット
  経由での利用（`run_internet.bat`）の両方に対応しています。インターネット
  経由で使う場合は、次章の管理者認証（ユーザー名・パスワード）の設定が必須です。

## 3. 必要環境

- Windows 11
- Python 3.11以上（開発・動作確認は Python 3.12 で実施）
- GPUは不要
- 同じWi-Fiで使う場合: スマートフォンとPCが同じWi-Fiに接続されていること
- インターネット経由で使う場合: [cloudflared](https://github.com/cloudflare/cloudflared/releases)
  （`winget install --id Cloudflare.cloudflared` でも導入できます）

## 4. Windowsでのセットアップ

1. このフォルダ（`parking-counter`）をPCの好きな場所に置きます。
2. Pythonが未インストールの場合は、[python.org](https://www.python.org/) から
   Python 3.11以上をインストールしてください（インストール時に
   「Add python.exe to PATH」にチェックを入れてください）。
3. `set_credentials.bat` をダブルクリックし、管理者ユーザー名とパスワードを
   設定します（詳細は次章）。
4. あとは「起動方法」の通り `run.bat`（同じWi-Fi内）または
   `run_internet.bat`（インターネット経由）をダブルクリックするだけです。
   仮想環境の作成とライブラリのインストールは自動で行われます。

## 5. 管理者認証の設定（初回のみ）

このシステムには駐車枠の登録・削除や画像アップロードのエンドポイントがあり、
認証なしで動かすと**サーバーに到達できる人なら誰でも操作できてしまいます**。
`run.bat`（同じWi-Fi内）でも設定を推奨し、`run_internet.bat`
（インターネット公開）では設定必須です。

1. `set_credentials.bat` をダブルクリックします。
2. ユーザー名とパスワードを入力します（画面にそのまま表示されるので、
   他人に画面を見られない状態で入力してください）。
3. 設定はWindowsのユーザー環境変数
   （`PARKING_ADMIN_USERNAME` / `PARKING_ADMIN_PASSWORD`）に保存されます。
   反映するには、開いているコマンドプロンプトを閉じてから
   `run.bat` / `run_internet.bat` を実行し直してください。

設定後は、ブラウザでアクセスするとユーザー名/パスワードを求めるダイアログが
表示されます（HTTP Basic認証）。スマートフォンのブラウザでも同様です。

未設定のまま `run.bat`（同じWi-Fi内）を起動すると、起動時に警告が表示されます
が起動は継続します。`run_internet.bat` は未設定だと起動そのものを中止します。

## 6. 起動方法

### 6.1 同じWi-Fi内で使う場合

`run.bat` をダブルクリックしてください。

- 初回のみ、仮想環境（`.venv`）の作成とライブラリのインストールが走ります
  （数分かかることがあります）。
- 2回目以降は、インストール済みのライブラリを再利用するため、すぐに起動します。
- 起動すると、コマンドプロンプトの画面に以下のようなアクセス先が表示されます。

```text
PCでのアクセス
http://127.0.0.1:8000

同じWi-Fi内のスマートフォンからのアクセス
http://<PCのローカルIPアドレス>:8000
```

PCのローカルIPアドレスは、コマンドプロンプトで `ipconfig` を実行し、
「IPv4 アドレス」（例: `192.168.1.23`）を確認してください。

終了するときは、起動したウィンドウで `Ctrl+C` を押してください。

#### Windows Defenderファイアウォールについて

初回起動時に「Windows Defender ファイアウォールでこのアプリの機能の一部を
ブロックしました」という確認画面が出ることがあります。スマートフォンなど
同じWi-Fi内の他の端末からアクセスしたい場合は、「プライベートネットワーク」
にチェックを入れて「アクセスを許可する」を選んでください。

### 6.2 インターネット経由で使う場合（Cloudflare Tunnel）

ルーターのポート開放や固定IP・ドメインの用意なしに、HTTPSでインターネットから
アクセスできるようにする方法です。PCから外向きに接続する仕組みのため、
ルーター側の設定変更は不要です。

1. [管理者認証を設定](#5-管理者認証の設定初回のみ)しておきます（必須）。
2. cloudflared をインストールします。
   ```bat
   winget install --id Cloudflare.cloudflared
   ```
   または [リリースページ](https://github.com/cloudflare/cloudflared/releases)
   から `cloudflared.exe` をダウンロードし、このフォルダか PATH の通った
   場所に置きます。
3. `run_internet.bat` をダブルクリックします。
   - サーバーはこのPCだけからアクセス可能な状態（`127.0.0.1`）で起動し、
     別ウィンドウでCloudflare Tunnelが起動します。
   - 別ウィンドウに `https://xxxxx.trycloudflare.com` のようなURLが
     表示されます。これがインターネットからのアクセス先です。
   - このURLは実行のたびにランダムに変わります（Cloudflareアカウント不要の
     「クイックトンネル」機能を使っています）。
4. スマートフォンなど任意の端末から、表示されたURLの `/upload` を開きます
   （例: `https://xxxxx.trycloudflare.com/upload`）。
   ユーザー名/パスワードの入力を求められるので、設定した認証情報を入力します。
5. 終了するときは、サーバー側のウィンドウで `Ctrl+C` を押し、
   Cloudflare Tunnel側のウィンドウも閉じてください。

#### 固定URL・独自ドメインで公開したい場合

毎回URLが変わると不便な場合は、無料のCloudflareアカウントと
（任意で）独自ドメインを使って「名前付きトンネル」を作成できます。

```bat
cloudflared tunnel login
cloudflared tunnel create parking-counter
cloudflared tunnel route dns parking-counter parking.example.com
cloudflared tunnel run --url http://127.0.0.1:8000 parking-counter
```

（`parking.example.com` は自分のドメインに置き換えてください。ドメインが
なければ Cloudflare の無料サブドメインでも設定可能です。詳細は
[Cloudflare Tunnel公式ドキュメント](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/)
を参照してください。）この場合、`run_internet.bat` の最後の
`cloudflared tunnel --url http://127.0.0.1:8000` の行を上記の
`cloudflared tunnel run ... parking-counter` に置き換えれば、
毎回同じURLで起動できます。

## 7. スマートフォンからのアクセス方法

1. スマートフォンを、PCと同じWi-Fi（同じWi-Fi内モードの場合）に接続するか、
   `run_internet.bat` が表示したURLにアクセスできる状態にします。
2. スマートフォンのブラウザで `http://<PCのローカルIPアドレス>:8000/upload`
   （同じWi-Fi内）または `https://xxxxx.trycloudflare.com/upload`
   （インターネット経由）を開きます。
3. 認証ダイアログが表示されたら、設定したユーザー名/パスワードを入力します。
4. 「カメラで撮影」からその場で撮影するか、「画像ファイルを選択」から
   既存の画像を選び、「判定実行」を押します。

専用アプリのインストールは不要です。ブラウザだけで完結します。

## 8. 駐車枠の登録方法

1. ブラウザで `http://127.0.0.1:8000/admin/spaces`（駐車枠管理画面）を開きます。
2. 「駐車枠の登録」欄で駐車場全体が写った画像を選択します
   （この画像はサーバーには送信されません。位置決めのためだけに使われます）。
3. 表示された画像の上を、駐車枠1つ分だけマウスでドラッグします。
4. 枠の名前（例: `A-01`）を入力すると登録されます。
5. 同様にすべての駐車枠を登録してください。
6. 登録済みの一覧表からは、名前・座標・サイズの編集や削除もできます。

## 9. 基準画像の登録方法

1. すべての駐車枠が「空き」の状態のときに、駐車場全体を撮影します。
2. `/admin/spaces` 画面の「空車基準画像の登録」欄からその画像を選択し、
   「基準画像として登録」を押します。
3. サーバー側で駐車枠ごとに自動的に切り出され、`data/reference/` に
   `space_001.jpg` のような形式で保存されます（全体画像は保存されません）。
4. 駐車場のレイアウトや光の当たり方が大きく変わった場合は、同じ手順で
   基準画像を再登録してください。

## 10. 判定しきい値の変更方法

`config/settings.json` を編集してください。編集後はサーバーを再起動すると
反映されます。

```json
{
  "occupied_threshold": 0.12,
  "uncertain_margin": 0.02,
  "required_consecutive_results": 3,
  "image_max_width": 1280,
  "max_upload_size_mb": 10
}
```

- `occupied_threshold`: この差分率を超えたら「使用中」寄りと判定します。
- `uncertain_margin`: しきい値の前後どのくらいを「判定不能」の幅とするか。
- `required_consecutive_results`: 何回連続で同じ判定が出たら状態を確定するか。
- `image_max_width`: アップロード画像をこの幅以下に縮小してから処理します。
- `max_upload_size_mb`: アップロードを許可する最大ファイルサイズ（MB）。

## 11. テスト実行方法

```bat
call .venv\Scripts\activate
pytest
```

コード品質チェック（Ruff・mypy）は以下で実行できます。

```bat
ruff check .
ruff format --check .
mypy app --ignore-missing-imports
```

## 12. 現時点の制約

- 動画・RTSPストリーミングには対応していません（静止画のみ）。
- 駐車枠の座標は、判定時に画像をリサイズする幅（`image_max_width`）を
  基準に登録されます。極端に解像度の異なる画像を混在させると、枠の位置が
  ずれる場合があります。
- 判定は単純な画像差分（グレースケール＋GaussianBlur＋明るさ正規化＋
  絶対差分）によるものです。夜間や強い逆光、積雪などの条件では精度が
  下がる可能性があります。
- 状態確定に必要な連続判定（デフォルト3回）が完了するまでは、
  最新の判定結果がすぐに反映されません。
- 連続判定の途中経過（pending状態）はプロセスのメモリ上にのみ保持され、
  サーバーを再起動するとリセットされます。
- 認証はユーザー名/パスワード1組によるHTTP Basic認証のみです（複数管理者、
  権限分離、ログイン試行回数制限などはありません）。
- 複数駐車場の管理、予約・決済機能は実装していません。

## 13. プライバシー・セキュリティ上の注意

- アップロードされた駐車場全体の画像は、判定処理中もメモリ上でのみ扱われ、
  ディスクに保存されません。
- 基準画像として保存されるのは、駐車枠部分を切り出した小さな画像のみです。
- SQLiteに保存されるのは、判定時刻・空き台数・駐車枠ごとの状態と差分率
  のみで、画像データやナンバープレート情報は一切保存しません。
- ダッシュボードに表示する「判定結果画像」は一時ファイルとして保存され、
  次回判定時に上書きされます（`data/tmp/latest_annotated.jpg`）。
- インターネット経由で公開する場合は、必ず管理者認証（第5章）を設定して
  ください。認証情報はWindowsのユーザー環境変数に平文で保存されます。
  他のユーザーとPCを共有している場合はご注意ください。
- `run_internet.bat` の Cloudflare Tunnel はCloudflareの経路を通ります。
  Cloudflareとの通信は自動的にHTTPS化されますが、駐車枠の画像や判定結果は
  Cloudflareのネットワークを経由する点にご留意ください。

## 14. 今後の拡張候補

- YOLOなどの物体検出モデルへの判定ロジック差し替え
  （`ParkingDetector` インターフェースは差し替え可能な設計にしてあります）
- 判定履歴のCSVエクスポート、グラフ表示
- 複数駐車場・複数カメラへの対応
- 通知機能（空きが出たらSlack/LINE通知など）
- 複数管理者アカウント、ログイン試行回数制限などの認証強化

---

## 開発方針（参考）

本プロジェクトは、以下の方針で開発されたMVPです。

- クラウドサービス・外部AI APIを使用しない（画像判定ロジックそのものは
  ローカルのOpenCVのみで完結。Cloudflare Tunnelは公開経路であり、
  画像判定処理自体はクラウドに送っていません）
- GPU不要
- 動画ではなく静止画を使用
- 同じWi-Fi内・インターネット経由のどちらでも動作できる構成にする
- 元画像は原則保存しない
- 過剰設計を避け、小さく動くものを優先する

## ディレクトリ構成

```text
parking-counter/
├── app/
│   ├── main.py            FastAPIエントリポイント
│   ├── auth.py             管理者認証（HTTP Basic）
│   ├── config.py          設定読み込み
│   ├── database.py        SQLiteアクセス
│   ├── models.py          内部ドメインオブジェクト
│   ├── schemas.py         APIの入出力スキーマ
│   ├── services/          判定ロジック・状態管理・画像/基準画像管理
│   ├── routers/           dashboard / detection / history / admin
│   ├── templates/         Jinja2テンプレート（HTML）
│   └── static/            CSS / JS
├── config/settings.json   しきい値などの設定
├── data/                  駐車枠定義・基準画像・SQLite DB（元画像は含まない）
├── tests/                 pytest（画像差分・状態管理・API）
├── scripts/
│   ├── create_sample_data.py    テスト用の合成画像生成
│   └── check_credentials.py     起動前の認証情報チェック
├── requirements.txt
├── run.bat                 同じWi-Fi内で起動
├── run_internet.bat        Cloudflare Tunnel経由でインターネットに公開
├── set_credentials.bat     管理者ユーザー名/パスワードの設定
└── README.md
```
