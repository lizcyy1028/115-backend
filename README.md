# 115-backend

網頁程式設計課程作業：Harness runtime 開發（一）。

依據 Fuyuan Cheng (@gloomcheng) 的[Week 1 教材](https://gloomcheng.github.io/115-backend/agent-runtime/)撰寫。教材授權：[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/deed.zh-hant)。

## 檔案

- `week1_single_call.py`：以 Python 呼叫 NVIDIA 的 OpenAI 相容 Chat Completions API，印出 HTTP 狀態碼、模型回覆及 token 用量。
- `week2_tool_dispatch.py`：Week 2 工具分派。第一次呼叫帶 `tools` 取得 `tool_calls`，程式執行 `http_get` 後以 `role: "tool"` 回填，第二次呼叫不帶 `tools` 取得最終回答。
- `week2_tool_use_log.md`：執行 `week2_tool_dispatch.py` 成功後自動產生的 tool-use 對話紀錄（實測後才會出現）。
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

## Week 2：工具描述與分派

模型只提出建議（`tool_calls`），執行與回填是程式的工作。執行方式與 Week 1 相同，最後一行改成：

```zsh
python week2_tool_dispatch.py
```

模型預設為講義目前指定的 `minimaxai/minimax-m3.1-flash`，參數為 `max_tokens: 512`、`temperature: 1`、`top_p: 0.95`。若課堂公告其他模型，可用環境變數覆寫，例如 `NVIDIA_MODEL=meta/llama-3.1-8b-instruct python week2_tool_dispatch.py`。

| 步驟 | 模型建議 | 程式實際執行 |
|---|---|---|
| 第一次 API 回應 | `tool_calls` 的 `name` 與 `arguments` | 尚未執行；只收到建議 |
| 工具執行 | 無 | `http_get()` 以 `requests.get` 發出請求，回傳 `status_code`、`body_summary`（前 120 字） |
| 第二次 API 請求 | 無 | 回填 `role: "tool"`，`tool_call_id` 與第一次的 id 相同；不帶 `tools` |
| 第二次 API 回應 | 無 | `choices[0].message.content` |

成功執行後，上表會以實測值寫入 `week2_tool_use_log.md`；失敗時另存為 `week2_tool_use_log_failed.md`，不覆蓋成功紀錄。紀錄不包含 Authorization Header。

### Week 2 驗證狀態

`week2_tool_dispatch.py` 已完成，並以本機模擬回應測試過成功、第二次呼叫失敗、401 三種情況。NVIDIA 帳戶仍在等待驗證，尚無法建立 API Key，因此尚未進行真實 API 呼叫，`week2_tool_use_log.md` 待實測後補上。模擬結果不作為對話紀錄繳交。
