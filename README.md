# DeskPet 🐧 桌面悬浮企鹅 · 工作速记助手

DeskPet 是一个支持 Ubuntu 与 Windows 的 PySide6 桌面挂件：

- 无交互时显示半透明时钟；鼠标悬停时变成会呼吸、眨眼的企鹅；
- 单击互动、拖动换位置、双击打开速记；
- 支持一次、每天和工作日提醒，完成、忽略或临时延后 5 分钟；
- 将当天速记和提醒整理成 Markdown 日报；
- 可调用 Qwen、GLM 或 OpenAI 兼容端点润色日报。

## Ubuntu 22.04+

最简单的安装方式是从 [Releases](https://github.com/chise0519/deskpet/releases) 下载对应架构的 `.deb`，然后运行：

```bash
sudo apt install ./deskpet_1.2.2_amd64.deb
```

安装后可在应用菜单搜索 **DeskPet**。卸载时运行：

```bash
sudo apt remove deskpet
```

用户配置和数据不会随软件包卸载而删除；如确定不再使用，可手动删除 `~/.config/deskpet` 和 `~/.local/share/deskpet`。

### 从源码安装

推荐在 X11 会话运行。安装脚本会创建项目虚拟环境、安装 Python 依赖，并添加应用菜单入口：

```bash
chmod +x install-ubuntu.sh run.sh
./install-ubuntu.sh
```

脚本需要安装以下 Ubuntu 组件，执行时可能要求管理员密码：

```bash
sudo apt install python3-venv libxcb-cursor0
```

安装后可在应用菜单搜索 **DeskPet**，也可运行：

```bash
./run.sh
```

Ubuntu 开机自启使用 XDG Autostart，设置文件位于：

```text
~/.config/autostart/io.github.chise0519.deskpet.desktop
```

### Ubuntu 数据目录

- 配置：`${XDG_CONFIG_HOME:-~/.config}/deskpet/config.json`
- 数据库：`${XDG_DATA_HOME:-~/.local/share}/deskpet/deskpet.db`
- 日报：`${XDG_DATA_HOME:-~/.local/share}/deskpet/reports/`
- 技能：`${XDG_DATA_HOME:-~/.local/share}/deskpet/skills/`

从旧版 `~/.deskpet/DeskPet/` 启动时会自动复制迁移数据，旧目录会保留以便回滚。配置目录权限为 `0700`，含 API Key 的配置文件和数据库权限为 `0600`。

## Windows

首次安装：

```powershell
py -3.10 -m venv .venv
.venv\Scripts\python.exe -m pip install -e .
```

之后双击 `run.bat`，或运行：

```powershell
.venv\Scripts\python.exe run_deskpet.py
```

Windows 数据仍保存在 `%APPDATA%\DeskPet\`，开机自启使用当前用户的注册表 Run 项。

## 功能与设置

- 日报存放目录：浏览选择或直接输入路径；
- 时钟：显示秒、日期星期、12 小时制；
- 互动与提醒：气泡、提示音、系统通知、轮询间隔；
- AI 润色：Qwen、GLM、自定义 OpenAI 兼容服务、本地 Ollama/vLLM；
- 润色技能：带 frontmatter 的 Markdown 指令文件；
- 系统：开机自启、重置企鹅位置。

双显示器环境会记录显示器名称和屏内相对位置；交换屏幕、调整主屏或临时拔掉显示器时，窗口会回到可见区域。

## 开发与测试

Ubuntu/macOS：

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'
.venv/bin/python -m pytest -v
QT_QPA_PLATFORM=offscreen .venv/bin/python tests/smoke_offscreen.py
.venv/bin/python tests/e2e_desktop.py
.venv/bin/ruff check deskpet tests
```

Windows 请把 `.venv/bin/python` 换成 `.venv\Scripts\python.exe`。

### 构建 Ubuntu `.deb`

构建脚本会用 PyInstaller 打包独立可执行程序，不要求目标电脑预装 Python 或 PySide6：

```bash
sudo apt install python3-venv libxcb-cursor0 libxkbcommon-x11-0
python3 -m venv .venv
.venv/bin/python -m pip install -e . pyinstaller
bash packaging/debian/build-deb.sh
```

安装包输出到 `dist/deskpet_<版本>_<架构>.deb`。推送 `v*` 标签时，GitHub Actions 会自动构建并上传到 GitHub Release。

## 项目结构

```text
deskpet/
├── config.py          XDG/Windows 数据路径、安全配置写入与迁移
├── display.py         多显示器选择、恢复与窗口夹取
├── autostart.py       Windows 注册表 / Linux XDG 开机自启
├── storage.py         SQLite CRUD
├── scheduler.py       提醒到期、重复推进和临时延后
├── report.py          日报 Markdown 生成
├── pet_widget.py      时钟与企鹅动画
├── quick_note.py      速记面板
├── reminder_dialog.py 提醒管理面板
├── alert_card.py      到点提醒卡片
├── report_window.py   日报编辑与保存
├── settings_window.py 设置窗口
└── main.py            单实例、托盘与应用组装
```

企鹅和图标均由 QPainter/SVG 绘制，不依赖外部图片素材。

## Windows 打包（可选）

```powershell
.venv\Scripts\python.exe -m pip install pyinstaller
.venv\Scripts\pyinstaller --noconsole --onefile --name DeskPet run_deskpet.py
```
