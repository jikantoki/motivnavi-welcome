#!/usr/bin/env bash
# Motivnavi OSへようこそ (motivnavi) の .deb をビルドする
#
#   ./build-deb.sh            → ./dist/motivnavi.deb を作成
#   sudo apt install ./dist/motivnavi.deb
#
# 必要なもの: dpkg-deb（Ubuntu/Kubuntuなら最初から入っています）
set -euo pipefail

cd "$(dirname "$(readlink -f "$0")")"

PKG=motivnavi
VERSION="$(tr -d '[:space:]' < VERSION)"
ARCH=all
OUT_DIR="dist"
OUT="${OUT_DIR}/${PKG}.deb"
BUILD="$(mktemp -d)"
ROOT="${BUILD}/${PKG}"
trap 'rm -rf "${BUILD}"' EXIT

echo "==> ${PKG} ${VERSION} をビルドしています"

# --- アプリ本体 ---------------------------------------------------------
install -d "${ROOT}/usr/share/${PKG}"
install -m 0755 src/motivnavi.py "${ROOT}/usr/share/${PKG}/motivnavi.py"
echo "${VERSION}" > "${ROOT}/usr/share/${PKG}/VERSION"
cp -r src/web "${ROOT}/usr/share/${PKG}/web"
find "${ROOT}/usr/share/${PKG}/web" -type d -exec chmod 0755 {} +
find "${ROOT}/usr/share/${PKG}/web" -type f -exec chmod 0644 {} +

# --- 起動コマンド -------------------------------------------------------
install -D -m 0755 packaging/motivnavi "${ROOT}/usr/bin/${PKG}"

# --- メニュー登録・アイコン ---------------------------------------------
install -D -m 0644 packaging/xyz.enoki.motivnavi.desktop \
  "${ROOT}/usr/share/applications/xyz.enoki.motivnavi.desktop"
for dir in packaging/icons/*x*; do
  size="$(basename "${dir}")"
  install -D -m 0644 "${dir}/motivnavi.png" \
    "${ROOT}/usr/share/icons/hicolor/${size}/apps/motivnavi.png"
done
install -D -m 0644 packaging/icons/256x256/motivnavi.png \
  "${ROOT}/usr/share/pixmaps/motivnavi.png"

# --- ドキュメント -------------------------------------------------------
install -d "${ROOT}/usr/share/doc/${PKG}"
cat > "${ROOT}/usr/share/doc/${PKG}/copyright" <<'EOF'
Format: https://www.debian.org/doc/packaging-manuals/copyright-format/1.0/
Upstream-Name: motivnavi
Upstream-Contact: エノキ電気 / ENOKI ELECTRONICS <https://enoki.xyz>

Files: *
Copyright: 2026 エノキ電気 / ENOKI ELECTRONICS
License: All rights reserved
EOF

# --- control ------------------------------------------------------------
SIZE_KB="$(du -sk "${ROOT}" | cut -f1)"
install -d "${ROOT}/DEBIAN"
cat > "${ROOT}/DEBIAN/control" <<EOF
Package: ${PKG}
Version: ${VERSION}
Section: utils
Priority: optional
Architecture: ${ARCH}
Installed-Size: ${SIZE_KB}
Depends: python3 (>= 3.8), python3-gi, gir1.2-gtk-3.0, gir1.2-webkit2-4.1 | gir1.2-webkit2-4.0 | gir1.2-webkit-6.0
Recommends: fonts-noto-cjk
Suggests: chromium
Maintainer: エノキ電気 <https://enoki.xyz>
Homepage: https://motivnavi.enoki.xyz/
Description: Motivnavi OSへようこそ
 Motivnavi OSのウェルカムアプリです。OSの紹介、タブレットの車への
 設置方法を表示し、Linux Auto (Android Auto)、Mediablue (Bluetooth)、
 Castify (インターネットラジオ)、Motivnavi Screentweaks (画面設定)、
 Motivnavi Updater を起動できます。
EOF

# --- ビルド -------------------------------------------------------------
mkdir -p "${OUT_DIR}"
rm -f "${OUT}"
dpkg-deb --root-owner-group --build "${ROOT}" "${OUT}" >/dev/null
echo "==> 完成: $(pwd)/${OUT}"
echo "    インストール: sudo apt install ./${OUT}"
