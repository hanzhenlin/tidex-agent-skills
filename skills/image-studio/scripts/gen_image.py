#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Image Studio - 开源级多模型 AI 图像生成工作站。

支持供应商命名路由与严格模型配套机制：
- 默认调度：不指定参数时，自动走根配置 default_provider 及该供应商的 default_model
- 指定供应商 (-p)：自动加载该供应商及其默认模型
- 指定模型 (-m)：自动匹配支持该模型的供应商
- 严格配套：若同时指定 -p 和 -m，强制校验配套关系，不配套立即拦截报错

三级交付流水线：
  直读 (Direct) > 代理 (Proxy via proxy_url) > 官方 URL 兜底 (Fallback)

配置位置（唯一硬核规则路径）：
  ~/.tidex/tidex-agent-skills/config/image-studio/config.json
"""

import argparse
import base64
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

# 正则匹配
DATA_URL_RE = re.compile(r"data:image/([a-zA-Z0-9.+-]+);base64,([A-Za-z0-9+/=\r\n]+)")
MARKDOWN_IMG_RE = re.compile(r"!\[.*?\]\((https?://[^\s\)]+)\)")

# 唯一硬核配置路径
CONFIG_FILE = (
    Path.home() / ".tidex" / "tidex-agent-skills" / "config" / "image-studio" / "config.json"
)
_CONFIG: dict = {}

# 宽高比映射
ASPECT_TO_SIZE_MAP = {
    "1:1": "1024x1024",
    "3:4": "1024x1792",
    "9:16": "1024x1792",
    "4:3": "1792x1024",
    "16:9": "1792x1024",
    "2:3": "1024x1792",
    "3:2": "1792x1024",
}


def fail(msg: str, code: int = 1) -> None:
    print(f"[✗] {msg}", file=sys.stderr)
    sys.exit(code)


def warn(msg: str) -> None:
    print(f"[!] {msg}", file=sys.stderr)


def load_config() -> dict:
    global _CONFIG
    if not CONFIG_FILE.is_file():
        fail(
            f"配置文件未找到: {CONFIG_FILE}\n"
            f"Tidex 严格推行单一硬核配置规范，请创建该配置目录与文件并配置供应商。\n"
            f"参考命令:\n"
            f"  mkdir -p {CONFIG_FILE.parent}\n"
            f"  chmod 700 {CONFIG_FILE.parent}\n"
            f"  touch {CONFIG_FILE} && chmod 600 {CONFIG_FILE}",
            1,
        )

    try:
        if CONFIG_FILE.stat().st_mode & 0o077:
            warn(f"config.json 权限过宽，建议执行: chmod 600 {CONFIG_FILE}")
        _CONFIG = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        return _CONFIG
    except Exception as e:
        fail(f"config.json 读取失败 ({CONFIG_FILE}): {e}", 1)


def get_providers() -> list:
    cfg = load_config()
    providers = cfg.get("providers") or []
    if not isinstance(providers, list) or len(providers) == 0:
        fail("config.json 中未定义任何有效供应商 (providers 列表为空)。", 1)
    return providers


def resolve_routing(args) -> tuple:
    """根据命令行与配置，完成供应商与模型的权威解析及严格配套校验。

    返回: (selected_provider, final_model)
    """
    cfg = load_config()
    providers = get_providers()
    default_p_name = cfg.get("default_provider", "")

    req_p_name = args.provider.strip() if args.provider else None
    req_model = args.model.strip() if args.model else None

    # 1. 确定目标供应商
    target_provider = None

    if req_p_name:
        # 用户显式指定了供应商名字
        for p in providers:
            if p.get("name") == req_p_name:
                target_provider = p
                break
        if not target_provider:
            avail_names = [p.get("name") for p in providers if p.get("name")]
            fail(f"指定的供应商 '{req_p_name}' 不存在！当前已配置的供应商有: {avail_names}", 1)
    elif req_model:
        # 用户未指定供应商，但指定了模型：在所有供应商中寻找支持该模型的供应商
        matched = []
        for p in providers:
            p_models = [m.lower() for m in p.get("models", [])]
            if req_model.lower() in p_models:
                matched.append(p)
        if len(matched) == 1:
            target_provider = matched[0]
        elif len(matched) > 1:
            # 多个供应商都支持此模型，优先看默认供应商是否支持
            for p in matched:
                if p.get("name") == default_p_name:
                    target_provider = p
                    break
            if not target_provider:
                target_provider = matched[0]
        else:
            # 无法按 models 精确匹配，尝试按类型模糊匹配
            target_type = "gemini" if "gemini" in req_model.lower() else "grok" if "grok" in req_model.lower() else None
            for p in providers:
                if p.get("type") == target_type:
                    target_provider = p
                    break
            if not target_provider:
                all_models_summary = []
                for p in providers:
                    all_models_summary.append(f"[{p.get('name')}] 支持: {', '.join(p.get('models', []))}")
                fail(
                    f"未找到支持模型 '{req_model}' 的供应商！\n"
                    f"当前各供应商模型支持清单:\n  " + "\n  ".join(all_models_summary),
                    1
                )
    else:
        # 用户既未指定供应商也未指定模型：走根配置默认供应商
        for p in providers:
            if p.get("name") == default_p_name:
                target_provider = p
                break
        if not target_provider and len(providers) > 0:
            target_provider = providers[0]

    if not target_provider:
        fail("未能定位到任何可用供应商，请检查 config.json 配置。", 1)

    # 2. 确定目标模型
    if not req_model:
        # 未显式指定模型，采用目标供应商的 default_model
        final_model = target_provider.get("default_model")
        if not final_model:
            models_list = target_provider.get("models") or []
            if models_list:
                final_model = models_list[0]
            else:
                fail(f"供应商 '{target_provider.get('name')}' 未配置 default_model 且 models 为空。", 1)
    else:
        final_model = req_model

    # 3. 严格配套校验 (Strict Compatibility Check)
    supported_models = [m.lower() for m in target_provider.get("models", [])]
    if supported_models and final_model.lower() not in supported_models:
        fail(
            f"严格配套校验失败 (Mismatched Provider & Model):\n"
            f"供应商 '{target_provider.get('name')}' (type: {target_provider.get('type')}) 不支持模型 '{final_model}'！\n"
            f"该供应商支持的全部官方模型为:\n  • " + "\n  • ".join(target_provider.get("models", [])),
            1
        )

    # 4. 覆盖 Base URL 或 API Key (如命令行传入)
    if args.base_url:
        target_provider["base_url"] = args.base_url.strip()
    if args.api_key:
        target_provider["api_key"] = args.api_key.strip()

    if not target_provider.get("api_key"):
        fail(f"供应商 '{target_provider.get('name')}' 尚未配置 api_key！", 1)
    if not target_provider.get("base_url"):
        fail(f"供应商 '{target_provider.get('name')}' 尚未配置 base_url！", 1)

    return target_provider, final_model


def download_image_pipeline(url: str, timeout: int = 25) -> tuple:
    """图片读取三级流水线：直读 (Direct) > 代理 (Proxy via proxy_url) > URL (Fallback)。"""
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
        "Accept": "*/*",
    }

    cfg = load_config()
    proxy_url = cfg.get("proxy_url") or os.environ.get("IMAGE_STUDIO_PROXY_URL") or ""

    # === Level 1: 直读 ===
    req = urllib.request.Request(url, headers=headers)
    direct_opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        with direct_opener.open(req, timeout=timeout) as resp:
            data = resp.read()
            mime = resp.headers.get_content_type() or "image/jpeg"
            if data and len(data) > 1000:
                return mime, data, "direct"
    except Exception:
        pass

    # === Level 2: 代理 (Proxy via proxy_url) ===
    if proxy_url:
        proxy_url = proxy_url.strip()
        if proxy_url.startswith("http://") or proxy_url.startswith("socks5://") or "127.0.0.1" in proxy_url or "localhost" in proxy_url:
            proxy_handler = urllib.request.ProxyHandler({'http': proxy_url, 'https': proxy_url})
            proxy_opener = urllib.request.build_opener(proxy_handler)
            try:
                with proxy_opener.open(req, timeout=timeout) as resp:
                    data = resp.read()
                    mime = resp.headers.get_content_type() or "image/jpeg"
                    if data and len(data) > 1000:
                        return mime, data, "proxy (tunnel)"
            except Exception:
                pass
        else:
            target_url = f"{proxy_url}{url}" if proxy_url.endswith("=") or proxy_url.endswith("/") else f"{proxy_url}/{url}"
            mirror_req = urllib.request.Request(target_url, headers=headers)
            try:
                with direct_opener.open(mirror_req, timeout=timeout) as resp:
                    data = resp.read()
                    mime = resp.headers.get_content_type() or "image/jpeg"
                    if data and len(data) > 1000:
                        return mime, data, "proxy (mirror)"
            except Exception:
                pass

    # === Level 3: URL 兜底 ===
    return None, None, "url-only"


def call_grok_images(endpoint: str, payload: dict, api_key: str) -> tuple:
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    }
    req = urllib.request.Request(
        endpoint,
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=300) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            items = data.get("data") or []
            local_images = []
            remote_urls = []
            delivery_mode = "unknown"
            for it in items:
                if isinstance(it, dict):
                    if it.get("b64_json"):
                        local_images.append(("image/png", base64.b64decode(it["b64_json"])))
                        delivery_mode = "inline-b64"
                    elif it.get("url"):
                        raw_url = it["url"]
                        remote_urls.append(raw_url)
                        mime, b, mode = download_image_pipeline(raw_url)
                        delivery_mode = mode
                        if b:
                            local_images.append((mime, b))
            return local_images, remote_urls, delivery_mode
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")
        fail(f"HTTP {e.code}: {detail[:600]}", 2)
    except Exception as e:
        fail(f"请求失败: {e}", 2)


def call_gemini_stream(endpoint: str, payload: dict, api_key: str) -> tuple:
    payload_copy = dict(payload)
    payload_copy["stream"] = True

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
        "Accept": "text/event-stream, application/json",
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    }
    req = urllib.request.Request(
        endpoint,
        data=json.dumps(payload_copy).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    local_images = []
    remote_urls = []
    delivery_mode = "stream-direct"
    try:
        with urllib.request.urlopen(req, timeout=300) as resp:
            for line in resp:
                line_str = line.decode("utf-8", errors="replace").strip()
                if not line_str.startswith("data: "):
                    continue
                data_part = line_str[6:].strip()
                if data_part == "[DONE]":
                    break
                try:
                    chunk = json.loads(data_part)
                    choices = chunk.get("choices") or []
                    if choices:
                        delta = choices[0].get("delta") or {}
                        for img_obj in delta.get("images") or []:
                            if isinstance(img_obj, dict):
                                url = img_obj.get("image_url", {}).get("url") or img_obj.get("url", "")
                                if url.startswith("data:image/"):
                                    m = DATA_URL_RE.match(url)
                                    if m:
                                        local_images.append((f"image/{m.group(1)}", base64.b64decode(m.group(2))))
                                        delivery_mode = "inline-b64"
                                elif url.startswith("http"):
                                    remote_urls.append(url)
                                    mime, b, mode = download_image_pipeline(url)
                                    delivery_mode = mode
                                    if b:
                                        local_images.append((mime, b))
                except Exception:
                    pass
        return local_images, remote_urls, delivery_mode
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")
        fail(f"HTTP {e.code}: {detail[:600]}", 2)
    except Exception as e:
        fail(f"请求失败: {e}", 2)


def save_images(args, images: list) -> list:
    out = Path(args.output).expanduser() if args.output else Path.cwd()
    single = out.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}
    if single and len(images) > 1:
        fail("--output 指定了单一文件名，但生成了多张图片，请指定目录", 1)
    if single:
        out.parent.mkdir(parents=True, exist_ok=True)
        if out.exists():
            fail(f"文件已存在，拒绝覆盖: {out}", 1)
        out.write_bytes(images[0][1])
        return [out]
    out.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d_%H%M%S")
    saved = []
    ext_map = {"image/png": ".png", "image/jpeg": ".jpg", "image/webp": ".webp"}
    for idx, (mime, raw_bytes) in enumerate(images, 1):
        ext = ext_map.get(mime, ".jpg")
        file_path = out / f"tidex_{stamp}_{idx}{ext}"
        file_path.write_bytes(raw_bytes)
        saved.append(file_path)
    return saved


def do_check(args) -> None:
    cfg = load_config()
    default_p = cfg.get("default_provider", "未指定")
    providers_summary = []

    for p in get_providers():
        is_default = (p.get("name") == default_p)
        providers_summary.append({
            "name": p.get("name"),
            "is_default": is_default,
            "type": p.get("type"),
            "base_url": p.get("base_url"),
            "default_model": p.get("default_model"),
            "supported_models": p.get("models", []),
            "api_key_configured": bool(p.get("api_key"))
        })

    info = {
        "status": "ok",
        "config_path": str(CONFIG_FILE),
        "default_provider": default_p,
        "proxy_url": cfg.get("proxy_url") or "未设置（纯直连）",
        "delivery_pipeline": "直读 (Direct) > 代理 (Proxy via proxy_url) > URL 兜底 (Fallback)",
        "configured_providers": providers_summary
    }
    print(json.dumps(info, ensure_ascii=False, indent=2))


def check_for_updates_silently() -> None:
    """启动前轻量静默版本预检，基于本地 TTL 缓存节流，绝不阻塞生图主任务。"""
    try:
        # 寻找仓库根目录下的 scripts/check_update.py
        checker_script = (
            Path(__file__).resolve().parent.parent.parent.parent
            / "scripts"
            / "check_update.py"
        )
        if checker_script.is_file():
            sys.path.insert(0, str(checker_script.parent))
            import check_update

            msg = check_update.check_update_silent(
                project_name="tidex-agent-skills",
                repo="hanzhenlin/tidex-agent-skills",
            )
            if msg:
                warn(msg)
    except Exception:
        pass


def main() -> None:
    check_for_updates_silently()
    parser = argparse.ArgumentParser(
        prog="gen_image.py",
        description="Image Studio - 开源级多模型 AI 图像生成工作站 (Grok & Gemini 官方原生引擎)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "调度规则:\n"
            "  • 全默认:   python3 gen_image.py \"提示词\"             -> 走默认供应商的默认模型\n"
            "  • 选供应商: python3 gen_image.py \"提示词\" -p gemini-provider -> 走指定供应商的默认模型\n"
            "  • 选模型:   python3 gen_image.py \"提示词\" -m gemini-3.1-flash-image -> 自动匹配对应供应商\n"
            "  • 严格配套: 同时指定 -p 和 -m 时，模型必须属于该供应商，否则强制拦截报错\n"
        ),
    )
    parser.add_argument("prompt", nargs="?", default=None, help="生图提示词")
    parser.add_argument("-p", "--provider", default=None, metavar="NAME",
                        help="指定使用的供应商名字（如 grok-provider, gemini-provider）")
    parser.add_argument("-m", "--model", default=None, metavar="ID",
                        help="指定模型名（如 grok-imagine-image, gemini-3.1-flash-image）")
    parser.add_argument("--aspect", default="1:1", choices=list(ASPECT_TO_SIZE_MAP.keys()),
                        help="宽高比（默认 1:1，如 16:9, 3:4 等）")
    parser.add_argument("-o", "--output", metavar="DIR|FILE", help="输出路径或文件名")
    parser.add_argument("--base-url", default=None, metavar="URL", help="临时覆盖 Base URL")
    parser.add_argument("--api-key", default=None, metavar="KEY", help="临时覆盖 API Key")
    parser.add_argument("--check", action="store_true", help="离线自检供应商与配套模型清单")

    args = parser.parse_args()

    if args.check:
        do_check(args)
        return

    if not args.prompt:
        fail("缺少提示词。用法: python3 gen_image.py \"你的提示词\" [选项]\n执行 --check 可查看可用供应商及模型清单。", 1)

    provider, model = resolve_routing(args)
    p_name = provider.get("name")
    p_type = provider.get("type")
    base_url = provider.get("base_url").strip().rstrip("/")
    api_key = provider.get("api_key").strip()

    t0 = time.time()
    images = []
    remote_urls = []
    delivery_mode = "unknown"

    if p_type == "gemini":
        endpoint = base_url if base_url.endswith("/chat/completions") else f"{base_url}/v1/chat/completions"
        hint = f"\n\n[Image requirements: aspect ratio {args.aspect}; high quality.]"
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": args.prompt + hint}],
        }
        images, remote_urls, delivery_mode = call_gemini_stream(endpoint, payload, api_key)
    else:
        # grok / openai 图像端点
        base_clean = base_url[:-3] if base_url.endswith("/v1") else base_url
        endpoint = f"{base_clean}/v1/images/generations"
        payload = {
            "model": model,
            "prompt": args.prompt,
        }
        images, remote_urls, delivery_mode = call_grok_images(endpoint, payload, api_key)

    if not images and not remote_urls:
        fail("未能从响应中提取到图像，请检查提示词或更换模型。", 2)

    saved = save_images(args, images) if images else []
    print(json.dumps({
        "status": "ok",
        "provider": p_name,
        "provider_type": p_type,
        "model": model,
        "aspect_ratio": args.aspect,
        "delivery_mode": delivery_mode,
        "saved": [str(p.resolve()) for p in saved],
        "urls": remote_urls,
        "elapsed_s": round(time.time() - t0, 1),
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
