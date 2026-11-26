"""Week 2：工具描述與分派——模型提出，程式執行。

依據 Fuyuan Cheng (@gloomcheng) 的「從模型 API 到執行迴圈：六週實作」。
https://gloomcheng.github.io/115-backend/agent-runtime/ （CC BY 4.0）

一次工具呼叫 = 兩筆 API 交易：
  1. 第一次呼叫帶 tools，模型回傳 tool_calls（只是建議，還沒執行）。
  2. 程式依 name 與 arguments 實際執行 http_get。
  3. 結果以 role: "tool" 回填，tool_call_id 必須等於第一次回應的 id。
  4. 第二次呼叫不帶 tools，模型只能根據 tool result 回答。

執行後會把重點紀錄寫入 week2_tool_use_log.md（不含 Authorization Header）。
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path

try:
    import requests
except ImportError:
    sys.exit("請先執行：python -m pip install -r requirements.txt")

API_URL = "https://integrate.api.nvidia.com/v1/chat/completions"
MODEL = os.environ.get("NVIDIA_MODEL", "minimaxai/minimax-m3.1-flash")
LOG_PATH = Path(__file__).resolve().parent / "week2_tool_use_log.md"
FAILED_LOG_PATH = Path(__file__).resolve().parent / "week2_tool_use_log_failed.md"
USER_TASK = "用 http_get 抓取 https://example.com，然後用一句話說明你看到什麼。"

HTTP_GET_TOOL = {
    "type": "function",
    "function": {
        "name": "http_get",
        "description": "Fetch a URL with HTTP GET. Return status code and a short body summary.",
        "parameters": {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "Absolute http(s) URL to fetch.",
                }
            },
            "required": ["url"],
        },
    },
}


def redact(text):
    key = os.environ.get("NVIDIA_API_KEY", "").strip()
    return text.replace(key, "***") if key else text


def to_json(obj):
    return json.dumps(obj, ensure_ascii=False, indent=2)


def call_model(messages, tools=None):
    """送出一次 Chat Completions 請求，回傳 (status_code, message, finish_reason)。"""
    api_key = os.environ.get("NVIDIA_API_KEY", "").strip()
    if not api_key or api_key == "YOUR_NVIDIA_API_KEY":
        raise RuntimeError("尚未設定 NVIDIA_API_KEY；請先取得金鑰。")

    payload = {
        "model": MODEL,
        "messages": messages,
        "max_tokens": 512,
        "temperature": 1,
        "top_p": 0.95,
    }
    if tools is not None:
        payload["tools"] = tools

    resp = requests.post(
        API_URL,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=60,
    )
    print("status:", resp.status_code)
    try:
        data = resp.json()
    except ValueError:
        raise RuntimeError(f"HTTP {resp.status_code}，回應不是 JSON：{resp.text[:200]}")
    if not resp.ok:
        error = json.dumps(data.get("error", data), ensure_ascii=False)
        raise RuntimeError(f"HTTP {resp.status_code}：{error}")

    choice = data["choices"][0]
    print("finish_reason:", choice.get("finish_reason"))
    return resp.status_code, choice["message"], choice.get("finish_reason")


def http_get(url):
    """真正發出 HTTP 請求的是這個函式，不是模型。"""
    resp = requests.get(url, timeout=10)
    return {
        "status_code": resp.status_code,
        "body_summary": resp.text[:120],
    }


def dispatch(name, arguments):
    if name != "http_get":
        raise ValueError(f"unknown tool: {name}")
    args = json.loads(arguments)  # arguments 是 JSON 字串，要先轉成 dict
    return http_get(args["url"])


def run(record):
    messages = [{"role": "user", "content": USER_TASK}]

    print("\n== [1] 第一次 API 呼叫（帶 tools）==")
    status, first, reason = call_model(messages, tools=[HTTP_GET_TOOL])
    record["first"] = {"status": status, "finish_reason": reason, "message": first}
    print("tool_calls:", to_json(first.get("tool_calls")))
    if not first.get("tool_calls"):
        raise RuntimeError("沒有拿到 tool_calls；先檢查工具描述與 user message。")

    messages.append(first)

    print("\n== [2] 程式執行工具，回填 role: \"tool\" ==")
    for call in first["tool_calls"]:
        name = call["function"]["name"]
        arguments = call["function"]["arguments"]
        print("模型建議:", name, arguments)
        result = dispatch(name, arguments)
        print("程式執行:", json.dumps(result, ensure_ascii=False))
        messages.append({
            "role": "tool",
            "tool_call_id": call["id"],
            "content": json.dumps(result, ensure_ascii=False),
        })
        record["tools"].append({
            "id": call["id"],
            "name": name,
            "arguments": arguments,
            "result": result,
        })

    print("\n== [3] 第二次 API 呼叫（不帶 tools）==")
    record["second_request"] = [dict(m) for m in messages]
    status, final, reason = call_model(messages)
    record["second"] = {"status": status, "finish_reason": reason, "message": final}

    print("\n== [4] 第二次 API 回應 ==")
    if final.get("tool_calls"):
        print("模型又提出 tool_calls：任務需要更多步驟，Week 3 會改成迴圈。")
    if not final.get("content") and reason == "length":
        print("content 是空的且 finish_reason 為 length：max_tokens 可能被思考過程用完。")
    print("reply:", final.get("content"))


def cell(value, limit=120):
    """把值轉成可以放進 Markdown 表格的一格。"""
    text = " ".join(str(value).split())
    if len(text) > limit:
        text = text[:limit] + "…"
    return "`" + text.replace("`", "'").replace("|", "\\|") + "`"


def write_log(record):
    first = record.get("first")
    second = record.get("second")
    tools = record["tools"]
    missing = "（未取得）"

    if first and first["message"].get("tool_calls"):
        suggested = "<br>".join(
            f"name: {cell(c['function']['name'])}，arguments: {cell(c['function']['arguments'])}"
            for c in first["message"]["tool_calls"]
        )
    else:
        suggested = missing
    executed = "<br>".join(
        f"status_code: {cell(t['result']['status_code'])}，body_summary: {cell(t['result']['body_summary'])}"
        for t in tools
    ) or missing
    ids = "<br>".join(
        f"tool_call_id: {cell(t['id'])}（與第一次回應的 id 相同）" for t in tools
    )
    second_req = f"{ids}；請求未帶 tools" if record.get("second_request") else missing
    reply = cell(second["message"].get("content")) if second else missing

    lines = [
        "# Week 2 tool-use 對話紀錄",
        "",
        f"- 執行時間：{record['started']}",
        f"- model：`{MODEL}`",
        f"- 結果：{'完成' if not record.get('error') else '未完成'}",
    ]
    if record.get("error"):
        lines.append(f"- 錯誤：{cell(record['error'], limit=300)}")
    lines += [
        "- Authorization Header 不寫入本紀錄。",
        "",
        "## 四步驟重點",
        "",
        "| 步驟 | 模型建議 | 程式實際執行 |",
        "|---|---|---|",
        f"| 第一次 API 回應 | {suggested} | 尚未執行；只收到建議 |",
        f"| 工具執行 | 無 | {executed} |",
        f"| 第二次 API 請求 | 無 | {second_req} |",
        f"| 第二次 API 回應 | 無 | choices[0].message.content: {reply} |",
        "",
        "## 1. 第一次 API 回應（choices[0].message）",
        "",
    ]
    if first:
        lines += [
            f"HTTP status: {first['status']}，finish_reason: {first['finish_reason']}",
            "",
            "```json", to_json(first["message"]), "```",
        ]
    else:
        lines.append(missing)
    lines += ["", "## 2. 工具執行結果", ""]
    if tools:
        for t in tools:
            lines += ["```json", to_json(t), "```"]
    else:
        lines.append(missing)
    lines += ["", "## 3. 第二次 API 請求的 messages", ""]
    if record.get("second_request"):
        lines += ["```json", to_json(record["second_request"]), "```"]
    else:
        lines.append(missing)
    lines += ["", "## 4. 第二次 API 回應（choices[0].message）", ""]
    if second:
        lines += [
            f"HTTP status: {second['status']}，finish_reason: {second['finish_reason']}",
            "",
            "```json", to_json(second["message"]), "```",
        ]
    else:
        lines.append(missing)

    # 失敗的執行另存一份，不覆蓋已成功的紀錄。
    path = FAILED_LOG_PATH if record.get("error") else LOG_PATH
    path.write_text(redact("\n".join(lines) + "\n"), encoding="utf-8")
    print(f"\n紀錄已寫入：{path}")


if __name__ == "__main__":
    record = {"started": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "tools": []}
    try:
        run(record)
    except Exception as exc:
        record["error"] = redact(str(exc))
        print("error:", record["error"], file=sys.stderr)
    if "first" in record:  # 至少收到一次 API 回應才寫紀錄
        write_log(record)
    sys.exit(1 if record.get("error") else 0)
