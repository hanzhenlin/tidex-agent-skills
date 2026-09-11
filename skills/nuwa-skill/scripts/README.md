# 🛠️ 女娲造人 (nuwa-skill) 辅助脚本与依赖说明

本目录包含女娲技能蒸馏过程中使用的自动化辅助脚本。

## 📋 脚本清单与运行依赖

| 脚本名称 | 功能说明 | 依赖环境 | 安装/运行指引 |
| :--- | :--- | :--- | :--- |
| **`merge_research.py`** | 汇总 6 个调研 Agent 的输出，生成 Phase 1.5 审查检查点摘要表 | **Python 3.8+ (纯标准库)** | 零第三方依赖，直接运行：<br>`python3 scripts/merge_research.py <skill目录>` |
| **`quality_check.py`** | 自动化质检生成的 `SKILL.md`（心智模型数量、启发式规则、反模式等） | **Python 3.8+ (纯标准库)** | 零第三方依赖，直接运行：<br>`python3 scripts/quality_check.py <SKILL.md路径>` |
| **`srt_to_transcript.py`** | 将 SRT/VTT 视频字幕清洗为纯文本（去时间戳、序号与重复行） | **Python 3.8+ (纯标准库)** | 零第三方依赖，直接运行：<br>`python3 scripts/srt_to_transcript.py input.srt [output.txt]` |
| **`download_subtitles.sh`** | 从 YouTube 视频快速提取并下载字幕作为一手语料（可选辅助） | **Bash + `yt-dlp`** | 需要本地安装 `yt-dlp`：<br>• macOS: `brew install yt-dlp`<br>• Linux: `pip install yt-dlp`<br>运行：`./scripts/download_subtitles.sh <YouTube_URL>` |

---

## 💡 使用建议
所有的核心蒸馏分析和思维框架提炼均由 AI Agent 原生完成，上述脚本作为质检与语料清洗的高效加速工具，大部分场景下仅需系统自带的 Python 3 即可直接运行。
