"""
FAQ 初始化脚本
启动服务前运行一次，将 data/faq.json 导入向量库
"""
import json
import requests
import sys

FAQ_JSON_PATH = "data/faq.json"
API_URL = "http://localhost:8082/faq/seed"


def main():
    try:
        with open(FAQ_JSON_PATH, "r", encoding="utf-8") as f:
            faqs = json.load(f)
    except FileNotFoundError:
        print(f"错误：找不到文件 {FAQ_JSON_PATH}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"错误：JSON 解析失败 - {e}")
        sys.exit(1)

    print(f"正在导入 {len(faqs)} 条 FAQ...")

    try:
        resp = requests.post(API_URL, json={"faqs": faqs}, timeout=300)
        resp.raise_for_status()
        data = resp.json()
        print(f"OK {data['message']}")
    except requests.exceptions.ConnectionError:
        print("ERR 连接失败，请确保服务已启动：uvicorn app.main:app --reload")
        sys.exit(1)
    except requests.exceptions.HTTPError as e:
        print(f"ERR 请求失败：{e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
