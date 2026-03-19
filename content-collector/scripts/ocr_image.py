#!/usr/bin/env python3
"""
图片 OCR 识别
支持：提取图片中的文字和链接
"""

import json
import re
import sys
import os
from urllib.parse import urlparse

try:
    import pytesseract
    from PIL import Image
    HAS_TESSERACT = True
except ImportError:
    HAS_TESSERACT = False


def extract_urls_from_text(text: str) -> list:
    """从文本中提取 URL"""
    url_patterns = [
        r'https?://[^\s<>"\')\]]+',
        r"(?:www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b(?:[-a-zA-Z0-9()@:%_\+.~#?&/=]*)",
    ]

    urls = []
    for pattern in url_patterns:
        matches = re.findall(pattern, text)
        urls.extend(matches)

    seen = set()
    unique_urls = []
    for url in urls:
        url = url.strip()
        if url and url not in seen:
            seen.add(url)
            if url.startswith("www."):
                url = "https://" + url
            unique_urls.append(url)

    return unique_urls


def detect_platform_from_url(url: str) -> str:
    """从 URL 检测平台"""
    domain = urlparse(url).netloc.lower()

    if any(x in domain for x in ["x.com", "twitter.com"]):
        return "twitter"
    if "mp.weixin.qq.com" in domain:
        return "weixin"
    if any(x in domain for x in ["okjike.com", "jike.cn"]):
        return "jike"
    if "reddit.com" in domain:
        return "reddit"
    if any(x in domain for x in ["youtube.com", "youtu.be"]):
        return "youtube"
    if "bilibili.com" in domain:
        return "bilibili"
    if "zhihu.com" in domain:
        return "zhihu"
    if any(x in domain for x in ["douyin.com", "tiktok.com"]):
        return "tiktok"
    return "generic"


def ocr_image(image_path: str) -> dict:
    """对图片进行 OCR 识别"""
    if not os.path.exists(image_path):
        return {
            "success": False,
            "error": f"图片不存在: {image_path}",
            "text": "",
            "urls": [],
            "platforms": [],
        }

    result = {
        "success": False,
        "text": "",
        "urls": [],
        "platforms": [],
        "method": "none",
    }

    if HAS_TESSERACT:
        try:
            image = Image.open(image_path)
            text = pytesseract.image_to_string(image, lang="chi_sim+eng")
            result["text"] = text
            result["method"] = "tesseract"
            result["success"] = True
        except Exception as e:
            result["error"] = f"Tesseract OCR 失败: {str(e)}"

    if not result["success"]:
        result["note"] = "本地 Tesseract 不可用，可使用以下外部 OCR 方案"

    if not result["success"]:
        result["method"] = "external"
        result["note"] = "本地 OCR 不可用，请使用外部 OCR 服务"
        result["image_path"] = image_path
        result["recommendations"] = [
            "使用腾讯云数据万象 CI OCR",
            "使用飞书内置 OCR",
            "手动输入链接",
        ]

    if result["text"]:
        result["urls"] = extract_urls_from_text(result["text"])
        result["platforms"] = [detect_platform_from_url(url) for url in result["urls"]]

    return result


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 ocr_image.py <image_path>", file=sys.stderr)
        print("\n注意: 如需本地 OCR，请安装依赖:", file=sys.stderr)
        print("  pip install pytesseract pillow", file=sys.stderr)
        print("  apt-get install tesseract-ocr tesseract-ocr-chi-sim", file=sys.stderr)
        sys.exit(1)

    image_path = sys.argv[1]
    result = ocr_image(image_path)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
