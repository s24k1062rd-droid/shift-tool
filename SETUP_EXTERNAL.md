# 外部ネットワークからのアクセス設定ガイド

## 概要

このガイドでは、別の Wi-Fi ネットワークやモバイル回線からシフト作成ツールにアクセスできるようにします。

## 方法 1: Cloudflare Tunnel（推奨）

Cloudflare Tunnel は、複雑な設定なしにローカルサーバーを公開 URL で安全にアクセスできる方法です。

### インストール手順

#### 1. Cloudflared のダウンロード・インストール

以下のリンクからダウンロード：
https://developers.cloudflare.com/cloudflare-one/connections/connect-applications/install-and-setup/installation/

**Windows の場合：**
- `cloudflared-windows-amd64.msi` をダウンロード
- ファイルをダブルクリックしてインストール
- 「Next」を複数回クリックして完了

#### 2. インストール確認

PowerShell またはコマンドプロンプトで以下を実行：

```powershell
cloudflared --version
```

バージョン番号が表示されたら、インストール成功です。

### 実行方法

#### 方法 A: バッチファイル（最も簡単）

`run_external.bat` をダブルクリック

または

`start_with_tunnel.bat` をダブルクリック

#### 方法 B: 手動実行

**ターミナル 1（Flask サーバー）：**

```bash
cd "C:\Users\81808\Desktop\シフト作成ツール2"
python app.py
```

出力例：
```
 * Running on http://0.0.0.0:5000
 * Debug mode: on
```

**ターミナル 2（Cloudflare Tunnel）：**

```bash
cloudflared tunnel --url http://localhost:5000
```

出力例：
```
2026-02-07T12:00:00Z INF Tunnel credentials have been saved to [パス]
2026-02-07T12:00:00Z INF Tunnel running at: https://shift-tool-abcd1234.trycloudflare.com
```

### スマホでアクセス

Cloudflare Tunnel が起動すると、以下のような URL が表示されます：

```
https://shift-tool-abcd1234.trycloudflare.com
```

この URL をスマホなど外部デバイスのブラウザで開くだけで、外部ネットワークからアクセスできます。

**特徴：**
- ✅ 外部インターネットからアクセス可能
- ✅ 複雑な設定不要
- ✅ HTTPS で暗号化される（安全）
- ✅ ファイアウォール対応
- ✅ 毎回異なる URL が発行される（セッションごと）

---

## 方法 2: 固定 URL を使用（有料・上級）

より安定した固定 URL が必要な場合、以下を検討：

### Cloudflare Named Tunnel

Cloudflare アカウントを作成すると、固定の `yourname.workers.dev` URL を使用できます。

詳細：https://developers.cloudflare.com/cloudflare-one/connections/connect-applications/install-and-setup/tunnel-guide/

---

## 方法 3: PaaS へのデプロイ（最も安定）

より本格的なホスティングが必要な場合：

### Fly.io（推奨）

```bash
# インストール
curl -L https://fly.io/install.sh | sh

# ログイン
flyctl auth login

# デプロイ
flyctl launch
```

詳細：https://fly.io

### Render.com

ブラウザから GUI でデプロイ可能：https://render.com

### Heroku

```bash
# デプロイ手順は Procfile + requirements.txt で対応
```

---

## トラブルシューティング

### ❌ 「cloudflared is not recognized」エラー

**原因：** Cloudflared がインストールされていない、または PATH が設定されていない

**解決：**
1. インストーラーを再実行
2. PC を再起動
3. PowerShell を管理者として実行

### ❌ Flask サーバーが起動しない

```bash
# Python が正しくインストールされているか確認
python --version

# 仮想環境を有効化
.\.venv\Scripts\activate

# Flask がインストールされているか確認
pip list | findstr Flask
```

### ❌ トンネル接続後も外部からアクセスできない

1. ターミナルに表示される URL をコピー（例：`https://shift-tool-xxxxx.trycloudflare.com`）
2. 別デバイスのブラウザで URL を開く
3. `https://` から始まることを確認（`http://` ではなく）

### ❌ 毎回 URL が変わる

**これは仕様です。** Cloudflare Tunnel が起動するたびに新しい URL が発行されます。

固定 URL が必要な場合は、Cloudflare Named Tunnel または PaaS のデプロイをご検討ください。

---

## よくある質問

**Q. 既存の Wi-Fi アクセスはまだ使える？**

A. はい。`run.bat` で起動した場合は同じ Wi-Fi 内でのみ、`run_external.bat` で起動した場合は Cloudflare Tunnel の URL でアクセス可能です。

**Q. セキュリティは大丈夫？**

A. Cloudflare Tunnel は HTTPS で暗号化され、Cloudflare のセキュリティが適用されます。個人情報を含む場合は、パスワード認証の追加を検討してください。

**Q. 料金は発生する？**

A. Cloudflare Tunnel は無料です。

**Q. 固定 URL が必要な場合は？**

A. Cloudflare Named Tunnel（無料）または PaaS（Fly.io、Render など）へのデプロイをご検討ください。

---

## 関連リンク

- [Cloudflare Tunnel 公式ドキュメント](https://developers.cloudflare.com/cloudflare-one/connections/connect-applications/)
- [Fly.io](https://fly.io)
- [Render.com](https://render.com)
