# Image Studio (全能 AI 图像创作工作站)

> 🎨 **面向开源生态设计的企业级多供应商、多模型 AI 生图工作站**  
> 统一调度 Google Gemini 与 xAI Grok 等官方原生图像大模型，支持任意中转站无缝接入，具备智能命名路由、严格模型配套校验与「直读 > 代理 > URL」三级零丢图交付流水线。

---

## 🌟 核心特性

- **多大模型官方标准支持**：
  - **xAI Grok 官方生图家族**：`grok-imagine-image`（标准）、`grok-imagine-image-quality`（高画质）、`grok-imagine` 等；
  - **Google Gemini 官方生图家族**：`gemini-3.1-flash-image`、`gemini-3-pro-image`。
- **开源级多供应商配置**：用户可同时配置多家不同中转站（如 Sub2API、CC Host、官方直连等），赋予全局唯一 `name`，根配置自由切换 `default_provider`。
- **严格模型配套校验 (Strict Compatibility Check)**：防跨站乱调扣费，若指定模型不属于该供应商受支持的 `models` 列表，本地毫秒级拦截报错。
- **「直读 > 代理 > URL」三级交付流水线**：
  1. **直读 (Direct)**：优先直接拉取，境内外通畅时毫秒级存盘；
  2. **代理 (Proxy via proxy_url)**：若境外 CDN（如 `imgen.x.ai`）直连受阻超时，自动借力配置的本地代理（如 `127.0.0.1:7897`）保存图片；
  3. **官方直链 (URL Fallback)**：无代理时原样交付官方直链，保证 100% 任务必达，绝不丢图。
- **零外部依赖与纯净安全**：仅依赖 Python 3 标准库，零第三方 npm/pip 包，绝不引入外部公共镜像中转，100% 保护提示词与图片隐私。

---

## ⚙️ 快速配置

配置文件统一定位在当前用户的 Tidex 项目专属安全目录（不进入项目工作区，不进 Git）：
`~/.tidex/tidex-agent-skills/config/image-studio/config.json`

### 1. 复制示例配置
```bash
mkdir -p ~/.tidex/tidex-agent-skills/config/image-studio
chmod 700 ~/.tidex/tidex-agent-skills/config/image-studio
cp config.example.json ~/.tidex/tidex-agent-skills/config/image-studio/config.json
chmod 600 ~/.tidex/tidex-agent-skills/config/image-studio/config.json
```

### 2. 编辑填入凭证
```json
{
  "default_provider": "my-grok-relay",
  "proxy_url": "http://127.0.0.1:7897",
  "providers": [
    {
      "name": "my-grok-relay",
      "type": "grok",
      "base_url": "https://s2a.ii.sb",
      "api_key": "YOUR_GROK_KEY",
      "default_model": "grok-imagine-image",
      "models": [
        "grok-imagine-image",
        "grok-imagine-image-quality",
        "grok-imagine",
        "grok-imagine-edit",
        "grok-imagine-1"
      ]
    },
    {
      "name": "my-gemini-relay",
      "type": "gemini",
      "base_url": "https://cchost.ai",
      "api_key": "YOUR_GEMINI_KEY",
      "default_model": "gemini-3.1-flash-image",
      "models": [
        "gemini-3.1-flash-image",
        "gemini-3-pro-image"
      ]
    }
  ]
}
```

---

## 🚀 常用操作

### 1. 离线环境与流水线自检
```bash
python3 scripts/gen_image.py --check
```
*无需发起任何网络请求，清晰展示当前默认供应商、生效模型、三级流水线状态及各个供应商支持的官方模型池。*

### 2. 全默认出图（最简命令）
```bash
python3 scripts/gen_image.py "未来赛博朋克都市雨夜霓虹雄狮" -o ./output
```
*自动采用 `default_provider` 及其 `default_model`。*

### 3. 仅指定供应商 (`-p`)
```bash
python3 scripts/gen_image.py "水墨禅意白瓷茶杯" -p my-gemini-relay -o ./output
```
*自动使用指定供应商的 `default_model`。*

### 4. 仅指定模型 (`-m`)
```bash
python3 scripts/gen_image.py "奢华生日海报，大字立体雕刻穿出" -m gemini-3.1-flash-image --aspect 3:4 -o ./output
```
*自动定位唯一支持该模型的供应商发起请求。*

### 5. 严格配套校验拦截示例
```bash
python3 scripts/gen_image.py "测试" -p my-gemini-relay -m grok-imagine-image
```
*本地立即拦截报错：`供应商 my-gemini-relay 不支持模型 grok-imagine-image`，防跨站乱配白扣费。*

---

## 📊 参数说明

| 参数 | 说明 |
|---|---|
| `-p, --provider` | 指定使用的供应商名称（如 `my-grok-relay`, `my-gemini-relay`） |
| `-m, --model` | 指定官方模型名（如 `grok-imagine-image`, `gemini-3.1-flash-image`） |
| `--aspect` | 宽高比：`1:1`, `3:4`, `9:16`, `4:3`, `16:9`（默认 `1:1`） |
| `-o, --output` | 指定输出路径或单一文件名（防意外覆盖） |
| `--check` | 离线自检配置结构与交付流水线 |
| `--base-url` | 临时覆盖 Base URL |
| `--api-key` | 临时覆盖 API Key |

---

## 📄 开源许可证

本项目基于 MIT 许可证开源。
