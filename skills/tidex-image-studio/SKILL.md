---
name: tidex-image-studio
description: Use when 用户需要进行 AI 图像生成、艺术插画创作、海报设计或视觉渲染——统一驱动 Google Gemini Nano Banana 与 xAI Grok 多官方大模型，支持供应商命名路由与严格模型配套校验，自适应「直读 > 代理 > URL」三级交付流水线
version: 3.0.0
display_name: "Tidex AI 图像创作工作站"
display_name_en: "Tidex Image Studio"
---

# Tidex Image Studio (全能 AI 图像创作工作站)

面向开源生态设计的多供应商、多模型工业级图像生成工作站。支持任意中转站接入，提供供应商命名路由、严格模型配套校验，以及「直读 > 代理 > URL」三级零故障交付流水线。

---

## 🎯 官方标准模型池与供应商类型

本技能严格遵循各上游官方标准模型命名，彻底杜绝非官方别名：

| 供应商类型 (`type`) | 官方生图模型 (`models`) | 专长场景 | 协议通道 |
|---|---|---|---|
| **`grok`** | `grok-imagine-image`<br>`grok-imagine-image-quality`<br>`grok-imagine`<br>`grok-imagine-edit`<br>`grok-imagine-1` | 电影级抓拍、前卫超现实、赛博朋克、机械钟表、野生动物细节 | `/v1/images/generations` |
| **`gemini`** | `gemini-3.1-flash-image`<br>`gemini-3-pro-image` | 极致复杂英文文字排版、3D立体穿出海报、禅意摄影、15秒闪电交付 | `/v1/chat/completions` (SSE 流式) |

---

## ⚙️ 统一配置规范 (`~/.config/tidex-image-studio/config.json`)

配置文件结构清晰、面向开源设计，用户可自由对接任意中转站（Sub2API、CC Host、官方直连等）：

```json
{
  "default_provider": "s2a-grok",
  "proxy_url": "http://127.0.0.1:7897",
  "providers": [
    {
      "name": "s2a-grok",
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
      "name": "cchost-gemini",
      "type": "gemini",
      "base_url": "https://cchost.ai",
      "api_key": "YOUR_GEMINI_KEY",
      "default_model": "gemini-3.1-flash-image",
      "models": [
        "gemini-3.1-flash-image"
      ]
    }
  ]
}
```

### 配置字段说明：
- **`default_provider`**：全局默认供应商唯一名字。不传参数时自动走它；
- **`proxy_url`**：唯一代理配置。自动智能适配（本地 Clash 端口 `http://127.0.0.1:7897` 或反代前缀镜像）；
- **`name`**：供应商全局唯一标识名，供 `-p` 显式指定；
- **`type`**：协议类型，目前支持 `"grok"` 和 `"gemini"`；
- **`default_model`**：该供应商的默认出图模型；
- **`models`**：该供应商真实支持的模型清单，**用于严格配套校验，防跨站乱配白扣费**。

*铁律：配置文件严格执行 `chmod 600`，只保存在本机，绝不进入 Git 与同步工作区。*

---

## 🧭 四维调度与严格配套规则

脚本内置防呆严格校验引擎：

1. **全默认模式（最常用）**：
   ```bash
   python3 scripts/gen_image.py "未来科幻都市"
   ```
   *自动走 `default_provider` 及其 `default_model`。*

2. **仅指定供应商 (`-p`)**：
   ```bash
   python3 scripts/gen_image.py "水墨禅意白瓷茶杯" -p cchost-gemini
   ```
   *自动走该供应商的 `default_model`。*

3. **仅指定模型 (`-m`)**：
   ```bash
   python3 scripts/gen_image.py "奢华生日海报" -m gemini-3.1-flash-image --aspect 3:4
   ```
   *全自动定位并匹配唯一支持该模型的供应商通道。*

4. **严格配套拦截（防跨站乱调）**：
   ```bash
   python3 scripts/gen_image.py "测试" -p cchost-gemini -m grok-imagine-image
   ```
   *立即毫秒级报错拦截：`供应商 cchost-gemini 不支持模型 grok-imagine-image`，绝不发出错误请求！*

---

## 🛡️ 三级交付流水线 (Delivery Pipeline)

```text
生图完成 
  ├─ 1. 直读 (Direct Native)       → 直连拉取，成功即存盘本地 .jpg
  ├─ 2. 代理 (Proxy via proxy_url) → 境外受阻时自动切入 proxy_url 本地存盘
  └─ 3. 官方直链 (URL Fallback)    → 代理不可达时交付官方 URL，100% 不丢图
```

---

## 📊 参数速查

| 参数 | 说明 |
|---|---|
| `-p, --provider` | 指定供应商名字（如 `s2a-grok`, `cchost-gemini`） |
| `-m, --model` | 指定官方模型名（如 `grok-imagine-image`, `gemini-3.1-flash-image`） |
| `--aspect` | 宽高比：`1:1`, `3:4`, `9:16`, `4:3`, `16:9` |
| `-o, --output` | 指定本地输出目录或文件名（防覆盖保护） |
| `--check` | 离线自检供应商命名、默认状态与配套模型池 |
