#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""
Motivnavi OSへようこそ (motivnavi)

GTK + WebKitGTK で独立したウィンドウを開き、web/ 以下の HTML/CSS/JS を表示する。
画面側のボタンは「操作ID」だけを Python に送り、Python 側の許可リスト(ACTIONS)に
登録されたコマンドだけを起動する（任意コマンドは実行しない）。

(c) 2026 エノキ電気 / ENOKI ELECTRONICS
"""

import json
import os
import re
import shutil
import subprocess
import sys
import time

import gi

APP_ID = "xyz.enoki.motivnavi"
APP_TITLE = "Motivnavi OSへようこそ"
BASE_DIR = os.path.dirname(os.path.realpath(__file__))
WEB_DIR = os.path.join(BASE_DIR, "web")
VERSION_FILE = os.path.join(BASE_DIR, "VERSION")
CHROMIUM = "/snap/bin/chromium"

# 画面から起動できるもの（許可リスト）
ACTIONS = {
    "linux-auto": {
        "name": "Linux Auto",
        "cmd": ["linux-auto"],
    },
    "mediablue": {
        "name": "Mediablue",
        "cmd": ["mediablue"],
    },
    "castify": {
        "name": "Castify",
        "cmd": [CHROMIUM, "--app=https://castify.enoki.xyz/", "--no-first-run"],
    },
    "screentweaks": {
        "name": "Motivnavi Screentweaks",
        "cmd": ["motivnavi-screentweaks"],
    },
    "homepage": {
        "name": "Motivnavi OS公式ホームページ",
        "cmd": [CHROMIUM, "--app=https://motivnavi.enoki.xyz/", "--no-first-run"],
    },
    "enoki": {
        "name": "エノキ電気ホームページ",
        "cmd": [CHROMIUM, "--app=https://enoki.xyz/", "--no-first-run"],
    },
    "updater": {
        "name": "Motivnavi Updater",
        "cmd": ["motivnavi-updater"],
    },
}

# 画面倍率の補正
#   OSの拡大率（125%・150%など）を打ち消し、CSSの1pxを画面の物理1ピクセルに合わせる。
#   つまり150%の端末でも100%の端末と同じレイアウトで表示する。
#   物理解像度がこれより大きい画面では、この幅（px）相当で表示する。
DRM_DIR = "/sys/class/drm"
MAX_LAYOUT_WIDTH = 1920

# 同じボタンの連打で二重起動しないための間隔（秒）
LAUNCH_COOLDOWN = 3.0


def _select_webkit():
    """使える WebKitGTK を探す（4.1 → 4.0 → 6.0/GTK4 の順）。"""
    candidates = (
        ("WebKit2", "4.1", "3.0"),
        ("WebKit2", "4.0", "3.0"),
        ("WebKit", "6.0", "4.0"),
    )
    for namespace, version, gtk_version in candidates:
        try:
            gi.require_version(namespace, version)
        except ValueError:
            continue
        gi.require_version("Gtk", gtk_version)
        gi.require_version("Gdk", gtk_version)
        return namespace, gtk_version
    sys.stderr.write(
        "WebKitGTK が見つかりません。\n"
        "  sudo apt install gir1.2-webkit2-4.1\n"
        "を実行してから、もう一度起動してください。\n"
    )
    sys.exit(1)


WEBKIT_NS, GTK_VERSION = _select_webkit()
GTK4 = GTK_VERSION == "4.0"

from gi.repository import Gdk, GLib, Gtk  # noqa: E402

if WEBKIT_NS == "WebKit2":
    from gi.repository import WebKit2 as WebKit  # noqa: E402
else:
    from gi.repository import WebKit  # noqa: E402


def read_version():
    try:
        with open(VERSION_FILE, encoding="utf-8") as f:
            return f.read().strip()
    except OSError:
        return "dev"


def native_panel_size(connector_hint=None):
    """接続中ディスプレイの物理解像度 (幅, 高さ) を返す。分からなければ None。

    /sys/class/drm/<card>-<コネクタ>/modes の先頭行（推奨解像度）を読む。
    GTKが教えてくれたコネクタ名に一致するもの → 内蔵パネル(eDP/LVDS/DSI) → その他 の順で選ぶ。
    """
    try:
        names = sorted(os.listdir(DRM_DIR))
    except OSError:
        return None

    candidates = []
    for name in names:
        if "-" not in name:
            continue
        base = os.path.join(DRM_DIR, name)
        try:
            with open(os.path.join(base, "status"), encoding="ascii") as f:
                if f.read().strip() != "connected":
                    continue
            with open(os.path.join(base, "modes"), encoding="ascii") as f:
                first = f.readline().strip()
        except (OSError, UnicodeDecodeError):
            continue
        m = re.match(r"(\d+)x(\d+)", first)
        if not m:
            continue
        connector = name.split("-", 1)[1]  # card1-eDP-1 → eDP-1
        if connector_hint and connector == connector_hint:
            rank = 0
        elif connector.startswith(("eDP", "LVDS", "DSI")):
            rank = 1
        else:
            rank = 2
        candidates.append((rank, int(m.group(1)), int(m.group(2))))

    if not candidates:
        return None
    candidates.sort(key=lambda c: c[0])
    return candidates[0][1], candidates[0][2]


def launch(action_id):
    """許可リストにある操作だけを起動する。(成功したか, メッセージ) を返す。"""
    action = ACTIONS.get(action_id)
    if action is None:
        return False, "不明な操作です"

    name = action["name"]
    program = action["cmd"][0]
    executable = shutil.which(program)
    if executable is None:
        if program == CHROMIUM:
            return False, "Chromium が見つかりません（sudo snap install chromium）"
        return False, f"{name} が見つかりません（{program} コマンドがありません）"

    try:
        proc = subprocess.Popen(
            [executable, *action["cmd"][1:]],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
            close_fds=True,
        )
    except OSError as e:
        return False, f"{name} を起動できませんでした（{e.strerror}）"

    # 終了した子プロセスを回収してゾンビを残さない
    GLib.child_watch_add(GLib.PRIORITY_DEFAULT, proc.pid, lambda *_: None)
    return True, f"{name} を起動しています…"


class WelcomeApp(Gtk.Application):
    def __init__(self):
        super().__init__(application_id=APP_ID)
        self.window = None
        self.webview = None
        self.version = read_version()
        self.base_uri = GLib.filename_to_uri(WEB_DIR, None)
        self.last_launch = {}

    # ---- ウィンドウ ----------------------------------------------------
    def do_activate(self):
        if self.window is not None:
            self.window.present()
            return

        GLib.set_application_name(APP_TITLE)
        win = Gtk.ApplicationWindow(application=self)
        win.set_title(APP_TITLE)
        win.set_icon_name("motivnavi")
        win.set_default_size(1280, 800)

        manager = WebKit.UserContentManager()
        manager.connect("script-message-received::motivnavi", self.on_script_message)
        if GTK4:
            manager.register_script_message_handler("motivnavi", None)
        else:
            manager.register_script_message_handler("motivnavi")

        boot = "window.MOTIVNAVI = %s;" % json.dumps(
            {"native": True, "version": self.version}
        )
        manager.add_script(
            WebKit.UserScript.new(
                boot,
                WebKit.UserContentInjectedFrames.TOP_FRAME,
                WebKit.UserScriptInjectionTime.START,
                None,
                None,
            )
        )

        # 画面ファイルはローカルなのでキャッシュ不要（アップデート後に古い画面が出ないように）
        try:
            WebKit.WebContext.get_default().set_cache_model(WebKit.CacheModel.DOCUMENT_VIEWER)
        except (AttributeError, TypeError):
            pass

        webview = WebKit.WebView(user_content_manager=manager)
        settings = webview.get_settings()
        debug = bool(os.environ.get("MOTIVNAVI_DEBUG"))
        settings.set_enable_developer_extras(debug)
        if debug and hasattr(settings, "set_enable_write_console_messages_to_stdout"):
            settings.set_enable_write_console_messages_to_stdout(True)
        settings.set_allow_file_access_from_file_urls(True)

        bg = Gdk.RGBA()
        bg.parse("#070b16")
        webview.set_background_color(bg)

        webview.connect("decide-policy", self.on_decide_policy)
        webview.connect("context-menu", lambda *_: True)  # 長押しメニューを出さない
        webview.load_uri(GLib.filename_to_uri(os.path.join(WEB_DIR, "index.html"), None))

        # 表示されてモニターが決まったら倍率を合わせる（モニターの倍率が変わったときも）
        win.connect("map", lambda *_: GLib.idle_add(self.apply_zoom))
        win.connect("notify::scale-factor", lambda *_: GLib.idle_add(self.apply_zoom))

        if GTK4:
            win.set_child(webview)
        else:
            win.add(webview)
            win.show_all()
        win.maximize()
        win.present()

        self.window = win
        self.webview = webview

    # ---- 画面倍率の補正 ---------------------------------------------------
    def compute_zoom(self):
        override = os.environ.get("MOTIVNAVI_ZOOM")
        if override:
            try:
                return min(max(float(override), 0.25), 4.0)
            except ValueError:
                pass

        display = Gdk.Display.get_default()
        monitor = None
        try:
            if GTK4:
                surface = self.window.get_surface()
                monitor = display.get_monitor_at_surface(surface) if surface else None
            else:
                gdk_window = self.window.get_window()
                monitor = display.get_monitor_at_window(gdk_window) if gdk_window else None
        except (AttributeError, TypeError):
            monitor = None
        if monitor is None:
            return 1.0

        geometry = monitor.get_geometry()  # GTKから見た（拡大率適用後の）サイズ
        logical = max(geometry.width, geometry.height)
        native = native_panel_size(monitor.get_model())
        physical = max(native) if native else logical * monitor.get_scale_factor()
        if logical <= 0 or physical <= 0:
            return 1.0

        zoom = logical / min(physical, MAX_LAYOUT_WIDTH)
        return min(max(zoom, 0.25), 1.0)

    def apply_zoom(self):
        if self.webview is None or self.window is None:
            return False
        zoom = self.compute_zoom()
        if abs(self.webview.get_zoom_level() - zoom) > 0.001:
            self.webview.set_zoom_level(zoom)
        if os.environ.get("MOTIVNAVI_DEBUG"):
            print(f"[motivnavi] zoom = {zoom:.3f}", flush=True)
        return False

    # ---- 画面外への移動を禁止（アプリ内ページのみ表示） -------------------
    def on_decide_policy(self, webview, decision, decision_type):
        if decision_type in (
            WebKit.PolicyDecisionType.NAVIGATION_ACTION,
            WebKit.PolicyDecisionType.NEW_WINDOW_ACTION,
        ):
            uri = decision.get_navigation_action().get_request().get_uri() or ""
            if not uri.startswith(self.base_uri):
                decision.ignore()
                return True
        return False

    # ---- JS → Python ----------------------------------------------------
    def on_script_message(self, manager, result):
        value = result.get_js_value() if hasattr(result, "get_js_value") else result
        try:
            message = json.loads(value.to_string())
        except (TypeError, ValueError):
            return
        if not isinstance(message, dict) or message.get("type") != "launch":
            return

        action_id = str(message.get("action", ""))
        request_id = message.get("id")

        now = time.monotonic()
        if now - self.last_launch.get(action_id, -LAUNCH_COOLDOWN) < LAUNCH_COOLDOWN:
            ok, text = True, "起動中です。少しお待ちください…"
        else:
            ok, text = launch(action_id)
            if ok:
                self.last_launch[action_id] = now

        self.reply({"id": request_id, "action": action_id, "ok": ok, "message": text})

    # ---- Python → JS ----------------------------------------------------
    def reply(self, payload):
        script = "window.motivnavi && window.motivnavi.onResult(%s);" % json.dumps(payload)
        if hasattr(self.webview, "evaluate_javascript"):
            self.webview.evaluate_javascript(script, -1, None, None, None, None)
        else:
            self.webview.run_javascript(script, None, None)


def main():
    GLib.set_prgname("motivnavi")
    app = WelcomeApp()
    return app.run(sys.argv)


if __name__ == "__main__":
    sys.exit(main())
