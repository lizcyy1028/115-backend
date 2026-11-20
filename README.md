# 115-backend

網頁程式設計課程作業：Harness runtime 開發（一）。

依據 Fuyuan Cheng (@gloomcheng) 的[Week 1 教材](https://gloomcheng.github.io/115-backend/agent-runtime/)撰寫。教材授權：[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/deed.zh-hant)。

## 檔案

- `week1_single_call.py`：以 Python 呼叫 NVIDIA 的 OpenAI 相容 Chat Completions API，印出 HTTP 狀態碼、模型回覆及 token 用量。
- `requirements.txt`：執行需要的 Python 套件。
- `.gitignore`：排除金鑰設定、虛擬環境及 Python 暫存檔。

## 執行方式

需要 Python 3.9 以上，以及具備 NVIDIA Public API Endpoints 權限的 API Key。

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

在 macOS 預設的 zsh 終端機中輸入以下指令，金鑰輸入不會顯示，也不會寫進指令歷史：

```zsh
read -rs 'NVIDIA_API_KEY?請貼上 NVIDIA API Key：'
echo
export NVIDIA_API_KEY
python week1_single_call.py
unset NVIDIA_API_KEY
```

## 請求與回應

程式向 `https://integrate.api.nvidia.com/v1/chat/completions` 發出 POST，使用課堂指定的 `meta/llama-3.1-8b-instruct` 模型，請模型「用一句話說明什麼是 HTTP」。

- `status`：HTTP 回應狀態碼。
- `reply`：回應 JSON 的 `choices[0].message.content`。
- `usage`：API 回傳的 token 用量資料。
- `error`：未提供金鑰、套件缺少、連線失敗，或 API 回傳非成功狀態時的錯誤資訊。

金鑰透過環境變數讀取，未寫入原始碼。未提供金鑰時，程式會顯示提示並結束，不會發送 API 請求。

## 驗證狀態

已完成 Python 語法及本機模擬回應測試。NVIDIA 帳號的 API 權限仍待開通，因此尚未完成真實 NVIDIA API 呼叫，未將模擬資料當成實際成功結果。
