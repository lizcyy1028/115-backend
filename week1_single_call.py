"""Week 1：觀察 NVIDIA Chat Completions 的 status、reply 與 usage。

依據 Fuyuan Cheng (@gloomcheng) 的「從模型 API 到執行迴圈：六週實作」。
https://gloomcheng.github.io/115-backend/agent-runtime/ （CC BY 4.0）
"""

import json
import os
import sys

API_URL = "https://integrate.api.nvidia.com/v1/chat/completions"
MODEL = "meta/llama-3.1-8b-instruct"


def call_model(messages):
    api_key = os.environ.get("NVIDIA_API_KEY", "").strip()
    if not api_key or api_key == "YOUR_NVIDIA_API_KEY":
        raise RuntimeError("尚未設定 NVIDIA_API_KEY；請先取得金鑰。")
    try:
        import requests
    except ImportError as exc:
        raise RuntimeError("請先執行：python -m pip install -r requirements.txt") from exc

    resp = requests.post(
        API_URL,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": MODEL,
            "messages": messages,
            "max_tokens": 128,
            "temperature": 0.2,
        },
        timeout=60,
    )
    print("status:", resp.status_code)
    try:
        data = resp.json()
    except ValueError:
        print("error:", resp.text.replace(api_key, "***"))
        return False
    if not resp.ok:
        print("error:", json.dumps(data, ensure_ascii=False).replace(api_key, "***"))
        return False
    choices = data.get("choices", [])
    if not choices or not isinstance(choices[0].get("message", {}).get("content"), str):
        print("error: 回應缺少 choices[0].message.content")
        return False
    print("reply:", str(choices[0]["message"]["content"]).replace(api_key, "***"))
    print("usage:", json.dumps(data.get("usage"), ensure_ascii=False).replace(api_key, "***"))
    return True


if __name__ == "__main__":
    try:
        ok = call_model([{"role": "user", "content": "用一句話說明什麼是 HTTP"}])
    except Exception as exc:
        secret = os.environ.get("NVIDIA_API_KEY", "")
        message = str(exc)
        if secret:
            message = message.replace(secret, "***")
        print("error:", message, file=sys.stderr)
        sys.exit(1)
    sys.exit(0 if ok else 1)
