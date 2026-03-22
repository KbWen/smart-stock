# Model Signing Guide

> **Feature**: HMAC-SHA256 model integrity verification
> **Added**: v4 security hardening (PR#4, 2026-03-19)
> **Relevant files**: `core/ai/predictor.py`, `core/ai/trainer.py`, `core/config.py`

---

## Overview

Smart Stock 支援對 ML 模型檔案進行 HMAC-SHA256 簽名驗證，防止模型被竄改（supply-chain attack）。此功能為 **opt-in**：未設定 `MODEL_SIGNING_KEY` 時，系統以 SHA256 checksum 為主要完整性保護，行為與先前版本完全相容。

整合兩層保護：

| 層級 | 機制 | Sidecar 檔案 | 設定需求 |
|------|------|------------|----------|
| L1 | SHA256 checksum | `model.pkl.sha256` | 無（自動啟用）|
| L2 | HMAC-SHA256 簽名 | `model.pkl.sig` | `MODEL_SIGNING_KEY` |

---

## 環境變數

| 變數 | 預設值 | 說明 |
|------|--------|------|
| `MODEL_SIGNING_KEY` | `""` (空字串) | HMAC 簽名金鑰；空值表示停用 L2 簽名 |

設定位置：`core/config.py`

```python
MODEL_SIGNING_KEY = os.getenv("MODEL_SIGNING_KEY", "")
```

---

## 金鑰產生

建議使用至少 32 bytes 的隨機金鑰：

```bash
# 使用 openssl 產生 hex 金鑰（64 char）
openssl rand -hex 32

# 使用 Python 產生
python -c "import secrets; print(secrets.token_hex(32))"
```

將金鑰存入 `.env` 或 CI/CD secrets（**切勿 commit 到版本控制**）：

```env
MODEL_SIGNING_KEY=<your-64-char-hex-key>
```

---

## 訓練時行為（trainer.py）

當 `MODEL_SIGNING_KEY` 非空時，`train_and_save()` 完成後會：

1. 計算模型 bytes 的 HMAC-SHA256
2. 將簽名寫入 `<versioned_model>.sig`
3. 複製 `.sig` 到 `MODEL_PATH.sig`（使 default 模型也有對應簽名）

```
models/
├── model_sniper.pkl          ← 最新模型（symbolic copy）
├── model_sniper.pkl.sha256   ← SHA256 checksum（自動）
├── model_sniper.pkl.sig      ← HMAC-SHA256 簽名（opt-in）
├── model_sniper_20260321_0800.pkl
├── model_sniper_20260321_0800.pkl.sha256
└── model_sniper_20260321_0800.pkl.sig
```

---

## 載入時驗證（predictor.py）

`predict_prob()` 載入模型時的驗證流程：

```
if MODEL_SIGNING_KEY:
    read model bytes once
    ├── _verify_checksum()  → SHA256 mismatch → refuse load
    └── _verify_hmac()      → HMAC mismatch  → refuse load
    load via io.BytesIO (no double I/O)
else:
    _verify_checksum()      → SHA256 mismatch → refuse load
    joblib.load()
```

**回傳值語意**：

| 情境 | 回傳 |
|------|------|
| 簽名正確 | `True` |
| 簽名錯誤（金鑰設定 + sidecar 存在 + 不符） | `False` + `WARNING` log |
| 無金鑰（`MODEL_SIGNING_KEY = ""`） | `True`（signing 停用）|
| 無 sidecar（舊版模型無 `.sig`） | `True`（legacy 相容）|

---

## 測試

### 單元測試

```bash
pytest tests/test_core/test_predictor_hmac.py -v
pytest tests/test_core/test_trainer_hmac.py -v
```

測試涵蓋：

- AC1: 正確金鑰 + 正確簽名 → `True`
- AC2: 正確金鑰 + 錯誤簽名 → `False` + log 警告
- AC3: 未設定金鑰 → `True`（opt-out）
- AC4: 無 `.sig` 檔案 → `True`（legacy 相容）
- AC5: 訓練完成 + 金鑰設定 → `.sig` 檔案存在且內容正確
- AC6: 訓練完成 + 無金鑰 → 無 `.sig` 檔案

### 手動驗證端對端流程

```bash
# 1. 設定簽名金鑰
export MODEL_SIGNING_KEY=$(openssl rand -hex 32)

# 2. 訓練模型（會自動產生 .sig）
python backend/train_ai.py

# 3. 確認 .sig 存在
ls -la *.sig

# 4. 驗證簽名（Python）
python - <<'EOF'
import hashlib, hmac as _hmac
key = open(".env").read().split("MODEL_SIGNING_KEY=")[1].strip()
data = open("model_sniper.pkl", "rb").read()
expected = open("model_sniper.pkl.sig").read().strip()
actual = _hmac.new(key.encode(), data, hashlib.sha256).hexdigest()
print("VALID" if _hmac.compare_digest(actual, expected) else "INVALID")
EOF

# 5. 啟動 API，驗證模型正常載入
python -m uvicorn backend.main:app --port 8000
curl http://localhost:8000/api/health
```

---

## 生產環境建議

- 使用 CI/CD secret 注入 `MODEL_SIGNING_KEY`，不要寫死在程式碼或 `.env`
- 定期輪換金鑰：輪換後需重新訓練模型（舊模型的 `.sig` 以舊金鑰簽名，驗證將失敗）
- 監控 `WARNING: HMAC signature mismatch` log 事件
