# 🚀 外部アクセス設定 - クイックスタート

## 📋 何をするのか？

このシフト作成ツールを、別の Wi-Fi やモバイル回線からアクセスできるようにします。

---

## ⚡ 3ステップで完了

### ステップ 1️⃣: Cloudflared をインストール（5分）

Windows で以下のリンクからダウンロード：
👉 https://developers.cloudflare.com/cloudflare-one/connections/connect-applications/install-and-setup/installation/

**ファイル名:** `cloudflared-windows-amd64.msi`

ダウンロード後、ダブルクリックしてインストール（デフォルト設定でOK）

**インストール確認:**
```
cloudflared --version
```
バージョンが表示されれば OK ✓

---

### ステップ 2️⃣: アプリを起動

**方法 A（最も簡単）:**
```
run_external.bat
```
をダブルクリック

**方法 B（手動）:**
```
python app.py
```

---

### ステップ 3️⃣: トンネルを接続

新しいターミナルで：
```
cloudflared tunnel --url http://localhost:5000
```

出力に表示される URL をコピー：
```
https://shift-tool-xxxxxxxx.trycloudflare.com
```

---

## 📱 スマホでアクセス

コピーした URL をスマホのブラウザで開く

例：
```
https://shift-tool-xxxxxxxx.trycloudflare.com
```

✨ これで完了！

---

## ⚙️ 詳細設定

より詳しい説明は [SETUP_EXTERNAL.md](SETUP_EXTERNAL.md) を参照

---

## ❓ よくある質問

**Q. URL が毎回変わるのは？**
- A. Cloudflare Tunnel の仕様です。固定 URL が必要な場合は、Cloudflare Named Tunnel または PaaS へのデプロイをご検討ください。

**Q. セキュリティは大丈夫？**
- A. HTTPS で暗号化されており、Cloudflare のセキュリティが適用されます。

**Q. 料金は？**
- A. 完全無料です。

---

## 💡 トラブルシューティング

| エラー | 原因 | 解決方法 |
|--------|------|--------|
| `cloudflared is not recognized` | cloudflared がインストールされていない | インストーラーを再実行、PC を再起動 |
| Flask が起動しない | Python/Flask がインストールされていない | `python app.py` を実行して確認 |
| 外部からアクセスできない | URL を誤った | ターミナルに表示される `https://` で始まる URL を使用 |

詳細は [SETUP_EXTERNAL.md](SETUP_EXTERNAL.md) の「トラブルシューティング」セクションを参照

---

**サポート:**
問題が発生した場合は、ターミナルのエラーメッセージをコピーして確認してください。
