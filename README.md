<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10%2B-blue" alt="Python">
  <img src="https://img.shields.io/badge/License-MIT-green" alt="License">
  <img src="https://img.shields.io/badge/Status-Active-success" alt="Status">
</p>

<h1 align="center">🎯 ThemeHunter</h1>
<p align="center"><strong>A股新题材发现与埋伏系统</strong></p>
<p align="center">提前捕捉题材炒作机会，第一时间埋伏龙头股</p>

---

## ✨ 核心特性

<table>
<tr>
<td width="50%">

### 🔍 新题材发现
- **只做新题材**（30天内）
- 自动过滤已炒作题材
- 龙头涨幅监控
- 热度趋势追踪

</td>
<td width="50%">

### 📈 题材演化追踪
- 识别题材演化链条
- 预判下一阶段热点
- 催化剂时间预警
- 阶段判断（萌芽→爆发→炒作→退潮）

</td>
</tr>
<tr>
<td width="50%">

### 🤖 6大智能Agent
- 📜 政策解读师（权重1.3）
- 📰 新闻猎手（权重1.2）
- 🔬 技术前瞻者（权重1.1）
- 📅 事件策划师（权重1.0）
- 🎯 标的挖掘机（权重1.2）
- ⏰ 题材周期师（权重1.4）

</td>
<td width="50%">

### 📊 多源数据采集
- 官方媒体（新华社、央视、人民日报）
- 财经门户（财联社、东方财富、同花顺）
- 政府部门（国务院、发改委、工信部）
- 科技媒体（36氪、虎嗅、钛媒体）

</td>
</tr>
</table>

---

## 🚀 快速开始

### 安装

```bash
git clone https://github.com/xiaoxuan0820-ctrl/theme-hunter.git
cd theme-hunter
pip install -r requirements.txt
```

### 配置

```bash
cp .env.example .env
# 编辑 .env 填入配置
```

### 运行

```bash
# 启动定时调度
python scheduler.py

# 或手动运行
python main.py --test
```

---

## 📖 使用示例

### 早报输出

```
🎯 ThemeHunter 早报 | 2026-04-23

🆕 新题材发现

📌 【固态电池】得分 88 ⭐⭐⭐⭐⭐
├ 首次发现：3天前
├ 龙头涨幅：8%（未充分炒作）
├ 阶段：萌芽期
├ 催化剂：宁德时代发布会（4月28日）

【核心标的】
├ 宁德时代(300750) - 电池龙头
├ 赣锋锂业(002460) - 锂资源
└ 国轩高科(002074) - 固态电池

【埋伏建议】
时机：催化剂前5-7天
方向：龙头优先
风险：技术落地不及预期
```

---

## 🏗️ 项目架构

```
theme-hunter/
├── config/          # 配置中心
│   ├── config.yaml        # 主配置
│   ├── sources.yaml       # 数据源
│   └── keywords.yaml      # 题材关键词库
├── core/            # 核心引擎
│   ├── collector.py       # 新闻采集
│   ├── analyzer.py        # 题材分析
│   ├── predictor.py       # 预期预测
│   └── evolution.py       # 演化链追踪
├── agents/          # Agent系统
│   ├── policy_agent.py    # 政策解读师
│   ├── news_agent.py      # 新闻猎手
│   └── ...
├── main.py          # 主入口
└── scheduler.py     # 定时调度
```

---

## 🎭 Agent系统

| Agent | 权重 | 核心能力 |
|-------|:----:|----------|
| 📜 政策解读师 | 1.3 | 解读政策文件，提取利好方向 |
| 📰 新闻猎手 | 1.2 | 抓取热点新闻，识别题材萌芽 |
| 🔬 技术前瞻者 | 1.1 | 跟踪技术突破，预判产业变革 |
| 📅 事件策划师 | 1.0 | 分析重大事件时间线 |
| 🎯 标的挖掘机 | 1.2 | 挖掘龙头股/跟风股 |
| ⏰ 题材周期师 | 1.4 | 判断题材阶段，预警退潮 |

---

## 📅 定时报告

| 时间 | 报告 | 内容 |
|:----:|------|------|
| 08:30 | 早报 | 今日新题材机会 |
| 11:30 | 午扫 | 盘中热点追踪 |
| 14:30 | 午评 | 尾盘埋伏机会 |
| 20:00 | 晚报 | 明日题材预判 |
| 每小时 | 快报 | 实时题材更新 |

---

## 🔧 配置说明

### 环境变量

```bash
# 讯飞星辰LLM
XUNFEI_API_KEY=your_api_key
XUNFEI_MODEL_ID=astron-code-latest

# Telegram Bot
TELEGRAM_BOT_TOKEN=your_token
TELEGRAM_CHAT_ID=your_chat_id
```

---

## ⚠️ 免责声明

- 本系统仅供学习研究使用
- 所有分析仅供参考，不构成投资建议
- 股市有风险，投资需谨慎
- 请根据自身情况独立判断

---

## 📄 开源协议

[MIT License](LICENSE)

---

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

---

<p align="center">
  Made with ❤️ by <a href="https://github.com/xiaoxuan0820-ctrl">xiaoxuan0820-ctrl</a>
</p>

<p align="center">
  如果觉得有用，请给个 ⭐️ Star 支持一下！
</p>
