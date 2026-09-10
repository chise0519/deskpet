# DeskPet 🐧 桌面悬浮企鹅 · 工作速记助手

一个 Windows 桌面悬浮小挂件：

- **没碰它时** = 半透明悬浮时钟（HH:MM 大字 + 秒 + 日期）
- **鼠标放上去** = 变成一只会呼吸、眨眼、瞳孔跟鼠标转的小企鹅
- **点它** = 跳跃挥手 + 头顶冒气泡语录（类 QQ 宠物互动）
- **拖它** = 拎起来换位置（记住位置，重启还在）
- **双击它** = 速记面板，随手记工作事项
- **右键它** = 菜单：速记 / 提醒 / 写日报 / 设置 / 退出
- **提醒到点** = 企鹅举牌 + 弹窗卡片 + 系统通知，可完成 / 推迟5分钟 / 忽略
- **写日报** = 一键把当天速记+提醒汇总成 Markdown，保存为 `reports/YYYY-MM-DD.md`
- **一键润色** = 调 LLM（Qwen / GLM / 任意 OpenAI 兼容端点含本地 Ollama）润色日报，
  默认另存 `YYYY-MM-DD.polished.md` 保留原文，可在设置里改成覆盖

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

## 设置（右键企鹅 → 设置）

- 日报存放目录（浏览/打开/留空回默认）
- 时钟：显示秒 / 显示日期星期 / 12小时制
- 互动与提醒：气泡语录开关、beep 提示音、系统通知开关、轮询间隔
- AI 润色：服务商（Qwen DashScope / GLM 智谱 / 自定义 OpenAI 兼容）、Base URL、
  模型（可下拉选择也可手输）、API Key（密码框，仅存本机）、超时、润色后另存或覆盖；
  每个服务商各自记住一套 Base URL/模型/Key（切换不串），老版本单套配置自动迁移；
  "自动发现"并发扫描本地 Ollama / llama-server / LM Studio / vLLM 及已填端点，
  拉取 /models 列表自动填入；切换服务商或填完 Key 也会自动刷新模型列表；
  环境变量 DASHSCOPE_API_KEY / ZHIPUAI_API_KEY / OPENAI_API_KEY 有值时自动带入；
  "测试连接"按钮用当前填写值发自检请求，成功显示耗时与模型回复，失败给具体原因
- 润色技能：设置 → AI 润色 → 润色技能。技能是带 frontmatter 的 .md 指令文件
  （name/description + 正文），存放在 `%APPDATA%\DeskPet\skills\`；
  点"添加…"选 .md 入库并选中，"删除"移除；选中后其正文作为润色的 system prompt
  （自动附加"不编造事实"基础约束），选"内置润色提示"则用默认提示词。
  后续新增技能：丢 .md 进目录或设置里添加即可
- 系统：开机自启、重置企鹅位置

所有设置改完即存到 `%APPDATA%\DeskPet\config.json`。

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
