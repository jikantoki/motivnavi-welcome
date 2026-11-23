# Motivnavi OSへようこそ（motivnavi）

Motivnavi OSのウェルカムアプリです。OSの紹介や、タブレットを車に設置する方法を表示します。また、Linux Auto・Mediablue・Castify・Motivnavi Screentweaks・Motivnavi Updaterを起動できます。

## ビルドとインストール

```sh
./build-deb.sh                  # → dist/motivnavi.deb ができる（毎回同じ場所・同じ名前で上書き）
sudo apt install ./dist/motivnavi.deb
motivnavi                       # 起動（アプリメニューの「Motivnavi OSへようこそ」からも起動可）
```

アンインストールするときは `sudo apt remove motivnavi` を実行します。

## 構成

| パス | 内容 |
|---|---|
| `src/motivnavi.py` | Python本体（GTK + WebKitGTKでウィンドウを表示） |
| `src/web/` | 画面（HTML / CSS / JS / 画像） |
| `packaging/` | 起動コマンド、.desktopファイル、アイコン（16〜512px） |
| `VERSION` | バージョン番号（debのVersionに使われます） |
| `build-deb.sh` | debのビルドスクリプト（dpkg-debのみ使用）。出力先は `dist/motivnavi.deb` |

インストール先：`/usr/bin/motivnavi`、`/usr/share/motivnavi/`、`/usr/share/applications/xyz.enoki.motivnavi.desktop`

## ボタンと実行されるコマンド

`src/motivnavi.py` の `ACTIONS` に登録されたコマンドだけを実行します（7種類）。画面側からは操作IDだけが送られるので、任意のコマンドが実行されることはありません。

| ボタン | コマンド |
|---|---|
| Android Autoを使う | `linux-auto` |
| Bluetoothで音声を再生する・通話をする | `mediablue` |
| インターネットラジオを聞く | `/snap/bin/chromium --app=https://castify.enoki.xyz/ --no-first-run` |
| カーナビ向けに画面を設定する | `motivnavi-screentweaks` |
| Motivnavi OS公式ホームページ | `/snap/bin/chromium --app=https://motivnavi.enoki.xyz/ --no-first-run` |
| 製作者情報 → ホームページを開く | `/snap/bin/chromium --app=https://enoki.xyz/ --no-first-run` |
| アップデートを確認 | `motivnavi-updater` |

コマンドが見つからない場合は、画面下にエラーメッセージを表示します。同じボタンを3秒以内に連打しても、二重には起動しません。

## 画面の拡大率（DPI）について

OSの拡大率が125%・150%・200%などの端末でも、100%の端末と同じレイアウトで表示します。

- 起動時に、画面の物理解像度（`/sys/class/drm/*/modes`）とGTKから見えるサイズを比べ、WebViewの倍率でOSの拡大を打ち消します（CSSの1px＝画面の1ピクセル）。
- 物理解像度が1920pxを超える画面では、1920px相当の大きさで表示します（`src/motivnavi.py` の `MAX_LAYOUT_WIDTH`）。
- 倍率を手動で指定したいときは `MOTIVNAVI_ZOOM=0.8 motivnavi` のように起動します。
- WebKitGTKは倍率を変えると `vw`/`vh` の計算がずれるため、CSSでは `vw`/`vh` を使わず、`app.js` が設定する `--vw`/`--vh` 変数を使っています。

## 開発メモ

- `MOTIVNAVI_DEBUG=1 motivnavi` で起動すると、右クリックで開発者ツール（Web Inspector）が使え、JSのconsole出力と、適用した倍率（zoom）が端末に表示されます。
- `src/web/index.html` は普通のブラウザでも開いて見た目を確認できます（アプリの起動はできません）。
- WebKitGTKは 4.1 → 4.0 → 6.0（GTK4）の順に探します。
- 戻る操作：「もどる」ボタン、Escキー、Backspaceキー
