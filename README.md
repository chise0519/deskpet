# DeskPet 🐧 桌面悬浮企鹅 · 工作速记助手

一个 Windows 桌面悬浮小挂件：

- **没碰它时** = 半透明悬浮时钟（HH:MM 大字 + 秒 + 日期）
- **鼠标放上去** = 变成一只会呼吸、眨眼、瞳孔跟鼠标转的小企鹅
- **点它** = 跳跃挥手 + 头顶冒气泡语录（类 QQ 宠物互动）
- **拖它** = 拎起来换位置（记住位置，重启还在）
- **双击它** = 速记面板，随手记工作事项
- **右键它** = 菜单：速记 / 提醒 / 写日报 / 退出
- **提醒到点** = 企鹅举牌 + 弹窗卡片 + 系统通知，可完成 / 推迟5分钟 / 忽略
- **写日报** = 一键把当天速记+提醒汇总成 Markdown，保存为 `reports/YYYY-MM-DD.md`

## 运行

```bat
双击 run.bat
```

或命令行：

```bash
.venv\Scripts\python.exe run_deskpet.py        # 带控制台（调试）
.venv\Scripts\pythonw.exe run_deskpet.py       # 无控制台
```

首次安装依赖：

```bash
py -3.14 -m venv .venv
.venv\Scripts\pip install PySide6 pytest
```

## 数据位置

- 数据库：`%APPDATA%\DeskPet\deskpet.db`
- 日报：`%APPDATA%\DeskPet\reports\*.md`
- 窗口位置等：`%APPDATA%\DeskPet\config.json`

## 托盘

右下角托盘有小企鹅图标：
- 单击 = 速记面板
- 双击 = 日报窗口
- 右键 = 菜单（含"开机自启"开关）

## 测试

```bash
.venv\Scripts\python.exe -m pytest tests/ -v      # 逻辑层 17 个单测
.venv\Scripts\python.exe tests\smoke_offscreen.py # 离屏渲染冒烟
.venv\Scripts\python.exe tests\e2e_desktop.py     # 真桌面 E2E（约10秒，屏幕会闪窗口）
```

## 结构

```
deskpet/
├── config.py          路径/常量/语录
├── storage.py         SQLite CRUD（notes/reminders）
├── scheduler.py       提醒到期/重复推进（纯逻辑）
├── report.py          日报 Markdown 生成（纯逻辑）
├── autostart.py       开机自启（HKCU Run 注册表）
├── pet_widget.py      核心：时钟↔企鹅状态机、QPainter 绘制、气泡
├── quick_note.py      速记面板
├── reminder_dialog.py 提醒管理面板
├── alert_card.py      到点弹窗卡片
├── report_window.py   日报编辑/保存窗口
└── main.py            入口：单实例/托盘/轮询调度
```

企鹅是 QPainter 纯代码逐帧绘制的（无图片素材依赖），想要更精致的形象可换
[DyberPet](https://github.com/ChaozhongLiu/DyberPet)（GPL-3.0，同为 PySide6）的序列帧素材做皮肤。

## 打包 exe（可选）

```bash
.venv\Scripts\pip install pyinstaller
.venv\Scripts\pyinstaller --noconsole --onefile --name DeskPet run_deskpet.py
```
