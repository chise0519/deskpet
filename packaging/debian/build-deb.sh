#!/usr/bin/env bash
set -euo pipefail
umask 022

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PYTHON="${PYTHON:-${PROJECT_ROOT}/.venv/bin/python}"

if [[ "${PYTHON}" != */* ]]; then
    PYTHON="$(command -v "${PYTHON}" || true)"
fi

if [[ -z "${PYTHON}" || ! -x "${PYTHON}" ]]; then
    echo "Python environment not found. Set PYTHON to a usable interpreter." >&2
    echo "Create .venv and install the project plus PyInstaller first." >&2
    exit 1
fi

VERSION="${VERSION:-$("${PYTHON}" -c 'from deskpet import __version__; print(__version__)')}"
ARCH="${ARCH:-$(dpkg --print-architecture)}"
BUILD_DIR="${PROJECT_ROOT}/build/debian"
PYINSTALLER_DIR="${PROJECT_ROOT}/build/pyinstaller"
PACKAGE_ROOT="${BUILD_DIR}/deskpet_${VERSION}_${ARCH}"
OUTPUT_DIR="${OUTPUT_DIR:-${PROJECT_ROOT}/dist}"
PACKAGE_FILE="${OUTPUT_DIR}/deskpet_${VERSION}_${ARCH}.deb"

if ! "${PYTHON}" -m PyInstaller --version >/dev/null 2>&1; then
    echo "PyInstaller is not installed in ${PYTHON}." >&2
    echo "Run: ${PYTHON} -m pip install pyinstaller" >&2
    exit 1
fi

rm -rf "${BUILD_DIR}" "${PYINSTALLER_DIR}"
mkdir -p "${PACKAGE_ROOT}/DEBIAN" \
    "${PACKAGE_ROOT}/usr/bin" \
    "${PACKAGE_ROOT}/usr/share/applications" \
    "${PACKAGE_ROOT}/usr/share/icons/hicolor/scalable/apps" \
    "${OUTPUT_DIR}"

"${PYTHON}" -m PyInstaller \
    --noconfirm \
    --clean \
    --onefile \
    --windowed \
    --name deskpet \
    --distpath "${PYINSTALLER_DIR}/dist" \
    --workpath "${PYINSTALLER_DIR}/work" \
    --specpath "${PYINSTALLER_DIR}" \
    "${PROJECT_ROOT}/run_deskpet.py"

install -m 0755 "${PYINSTALLER_DIR}/dist/deskpet" "${PACKAGE_ROOT}/usr/bin/deskpet"
install -m 0644 \
    "${PROJECT_ROOT}/packaging/linux/io.github.chise0519.deskpet.svg" \
    "${PACKAGE_ROOT}/usr/share/icons/hicolor/scalable/apps/io.github.chise0519.deskpet.svg"

sed \
    -e 's|@EXEC@|/usr/bin/deskpet|g' \
    -e 's|@ICON@|io.github.chise0519.deskpet|g' \
    "${PROJECT_ROOT}/packaging/linux/io.github.chise0519.deskpet.desktop.in" \
    > "${PACKAGE_ROOT}/usr/share/applications/io.github.chise0519.deskpet.desktop"
chmod 0644 "${PACKAGE_ROOT}/usr/share/applications/io.github.chise0519.deskpet.desktop"

INSTALLED_SIZE="$(du -sk "${PACKAGE_ROOT}/usr" | cut -f1)"
cat > "${PACKAGE_ROOT}/DEBIAN/control" <<EOF
Package: deskpet
Version: ${VERSION}
Section: utils
Priority: optional
Architecture: ${ARCH}
Installed-Size: ${INSTALLED_SIZE}
Maintainer: chise0519 <114244347+chise0519@users.noreply.github.com>
Depends: libc6, libxcb-cursor0, libxkbcommon-x11-0
Homepage: https://github.com/chise0519/deskpet
Description: Floating desktop pet, quick-note and reminder assistant
 DeskPet is a PySide6 desktop companion with a clock, animated penguin,
 quick notes, recurring reminders and Markdown work reports.
EOF

cat > "${PACKAGE_ROOT}/DEBIAN/postinst" <<'EOF'
#!/bin/sh
set -e

if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database -q /usr/share/applications || true
fi
if command -v gtk-update-icon-cache >/dev/null 2>&1; then
    gtk-update-icon-cache -q -t -f /usr/share/icons/hicolor || true
fi

exit 0
EOF

cat > "${PACKAGE_ROOT}/DEBIAN/postrm" <<'EOF'
#!/bin/sh
set -e

if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database -q /usr/share/applications || true
fi
if command -v gtk-update-icon-cache >/dev/null 2>&1; then
    gtk-update-icon-cache -q -t -f /usr/share/icons/hicolor || true
fi

exit 0
EOF
chmod 0755 "${PACKAGE_ROOT}/DEBIAN/postinst" "${PACKAGE_ROOT}/DEBIAN/postrm"

dpkg-deb --root-owner-group --build "${PACKAGE_ROOT}" "${PACKAGE_FILE}"
sha256sum "${PACKAGE_FILE}"
