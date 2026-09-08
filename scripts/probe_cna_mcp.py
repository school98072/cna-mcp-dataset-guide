#!/usr/bin/env python3
"""
CNA MCP 連線與資料查詢示範腳本
=======================================
本腳本示範如何使用 Python 直接與中央社 CNA MCP Server (HTTP/SSE) 通訊，
執行新聞關鍵字檢索、特定分類查詢與譯名對照。

使用方式:
    export CNA_API_TOKEN="your_token_here"
    python scripts/probe_cna_mcp.py
"""

import os
import sys
import json
import requests

CNA_ENDPOINT = "https://ask.cna.com.tw/mcp/connect"
TOKEN = os.environ.get("CNA_API_TOKEN") or "cna_5f3a8fd0b7e1511c67d0f0d2509565f644772f141726a2ee"

def call_mcp_tool(tool_name: str, arguments: dict):
    headers = {
        "Authorization": f"Bearer {TOKEN}",
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream"
    }
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": tool_name,
            "arguments": arguments
        }
    }
    
    response = requests.post(CNA_ENDPOINT, json=payload, headers=headers, timeout=30)
    response.raise_for_status()
    
    # 處理可能的多行 SSE 格式或純 JSON 回應
    text = response.text.strip()
    if text.startswith("data:"):
        for line in text.split("\n"):
            if line.startswith("data:"):
                data_str = line[5:].strip()
                if data_str:
                    return json.loads(data_str)
    return response.json()

def main():
    print("==================================================")
    print("  中央社 CNA MCP 連線測試與數據範例")
    print("==================================================")
    
    # 1. 測試最新焦點新聞
    print("\n[1] 正在調用 cna-news-latest-newslist ...")
    try:
        res = call_mcp_tool("cna-news-latest-newslist", {})
        content = res.get("result", {}).get("content", [{}])[0].get("text", "")
        print("最新頭條新聞 (前 300 字):")
        print(content[:300] + ("..." if len(content) > 300 else ""))
    except Exception as e:
        print(f"調用失敗: {e}")

    # 2. 測試外文譯名查詢
    print("\n[2] 正在調用 cna-translation-lookup (查詢 'NVIDIA') ...")
    try:
        res = call_mcp_tool("cna-translation-lookup", {"name": "NVIDIA"})
        content = res.get("result", {}).get("content", [{}])[0].get("text", "")
        print(f"官方標準譯名結果:\n{content}")
    except Exception as e:
        print(f"調用失敗: {e}")

    # 3. 測試 2024 年歷史新聞量檢索
    print("\n[3] 正在調用 cna-news-qsearch (檢索 2024-01 全月發稿) ...")
    try:
        res = call_mcp_tool("cna-news-qsearch", {
            "query": "*",
            "start_date": "2024-01-01",
            "end_date": "2024-01-31"
        })
        total = res.get("result", {}).get("total_hits", 0)
        print(f"2024年1月份總發稿量: {total} 篇")
    except Exception as e:
        print(f"調用失敗: {e}")

if __name__ == "__main__":
    main()
