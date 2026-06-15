"""
FAQ / 知识库初始化脚本
启动服务前运行一次，将 knowledge/faq.json 导入向量库
"""

import json
import sys

import requests

from app.core.logging import log

FAQ_JSON_PATH = "knowledge/faq.json"
API_URL = "http://localhost:8082/v1/faq/seed"


def main():
    try:
        with open(FAQ_JSON_PATH, "r", encoding="utf-8") as f:
            faqs = json.load(f)
    except FileNotFoundError:
        log.error(f"错误：找不到文件 {FAQ_JSON_PATH}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        log.error(f"错误：JSON 解析失败 - {e}")
        sys.exit(1)

    log.info(f"正在导入 {len(faqs)} 条 FAQ...")

    try:
        resp = requests.post(API_URL, json={"faqs": faqs}, timeout=300)
        resp.raise_for_status()
        data = resp.json()
        log.info(f"导入完成: {data.get('message', 'OK')}")
    except requests.exceptions.ConnectionError:
        log.error("连接失败，请确保服务已启动：uvicorn app.main:app --reload")
        sys.exit(1)
    except requests.exceptions.HTTPError as e:
        log.error(f"请求失败：{e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
