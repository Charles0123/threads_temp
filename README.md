# Threads 聲量分析工具

這是一個前後端分離的 Threads 公開貼文關鍵字分析工具：輸入關鍵字後，後端使用 Playwright 擷取 Threads 公開搜尋結果，依日期統計貼文數量，前端以圖表呈現討論趨勢。

## 專案結構

```text
backend/       FastAPI API、Threads 爬蟲與資料統計
frontend/      Vue 3 + TypeScript + Vite 使用者介面
.vscode/       VS Code 工作區設定
```

## 環境需求

- Windows
- Python 3.14.7（目前已安裝並可使用 `py` 啟動）
- Node.js 與 npm
- 可連線至網際網路，以擷取 Threads 公開資料

## 首次安裝

請在專案根目錄執行 PowerShell 指令。

### 1. 建立 Python 虛擬環境

```powershell
py -3.14 -m venv backend\.venv
```

VS Code 已透過 `.vscode/settings.json` 設定使用：

```text
backend\.venv\Scripts\python.exe
```

若 VS Code 尚未更新設定，可使用 `Ctrl+Shift+P`，執行 `Python: Select Interpreter`，選擇上述解譯器。

### 2. 安裝後端套件

```powershell
& .\backend\.venv\Scripts\python.exe -m pip install --upgrade pip
& .\backend\.venv\Scripts\python.exe -m pip install -r .\backend\requirements.txt
```

### 3. 安裝 Playwright 瀏覽器

```powershell
& .\backend\.venv\Scripts\python.exe -m playwright install chromium
```

### 4. 登入 Threads（建議）

首次使用或 Session 過期時，在專案根目錄執行：

```powershell
& .\backend\.venv\Scripts\python.exe .\backend\login_threads.py
```

程式會開啟 Chromium，請在瀏覽器內手動完成 Threads 登入；登入完成後回到終端機按 Enter。登入 Session 會保存在 `backend\.threads-session`，後續分析會自動沿用，不需要在程式中輸入或保存密碼。

### 5. 安裝前端套件

```powershell
Push-Location frontend
npm install
Pop-Location
```

## 啟動服務

請開啟兩個 VS Code 終端機視窗，並都位於專案根目錄。

### 終端機一：啟動後端

```powershell
& .\backend\.venv\Scripts\python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

後端網址：<http://127.0.0.1:8000>

健康檢查：<http://127.0.0.1:8000/api/health>

登入狀態：<http://127.0.0.1:8000/api/auth/status>

API 文件：<http://127.0.0.1:8000/docs>

### 終端機二：啟動前端

```powershell
Push-Location frontend
npm run dev
Pop-Location
```

前端網址：<http://localhost:5173>

在瀏覽器開啟前端網址，輸入關鍵字並按下「開始分析」。每次分析會啟動無頭 Chromium 擷取 Threads 公開搜尋結果，可能需要數十秒。

## API 說明

### `GET /api/health`

確認後端是否正常執行。

回應：

```json
{"status":"ok"}
```

### `POST /api/analyze`

依關鍵字分析公開貼文。

請求：

```json
{
  "keyword": "人工智慧",
  "start_date": "2026-08-01",
  "end_date": "2026-09-07"
}
```

回應：

```json
{
  "dates": ["2026-09-01", "2026-09-02"],
  "counts": [12, 18],
  "posts": [
    {
      "published_at": "2026-09-02T08:30:00+00:00",
      "text": "貼文內容",
      "url": "https://www.threads.com/@user/post/abc123",
      "likes": 1200,
      "engagement": 1200
    }
  ],
  "top_engagement": [],
  "top_likes": []
}
```

搜尋會使用 Threads 的相關性結果，再依日期區間篩選。公開頁面通常無法提供真實點擊數，因此 `top_engagement` 目前以公開可取得的按讚數作為排序依據。

## 建置與驗證

前端 production build：

```powershell
Push-Location frontend
npm run build
Pop-Location
```

驗證後端套件：

```powershell
& .\backend\.venv\Scripts\python.exe -c "import fastapi, uvicorn, playwright, pandas; print('backend dependencies: ok')"
```

## 常見問題

### `python` 顯示 Microsoft Store 錯誤

目前 Windows 的 `python` 指令可能仍指向 Microsoft Store 別名。本專案請使用 `py -3.14` 建立環境，或直接使用虛擬環境的完整路徑：

```powershell
& .\backend\.venv\Scripts\python.exe --version
```

也可以到 Windows 的「設定 → 應用程式 → 進階應用程式設定 → 應用程式執行別名」，關閉 `python.exe` 與 `python3.exe` 的 Microsoft Store 別名。

### 後端啟動時找不到 Playwright 瀏覽器

重新執行：

```powershell
& .\backend\.venv\Scripts\python.exe -m playwright install chromium
```

### 前端無法連線後端

確認後端正在 `http://127.0.0.1:8000` 執行，並先開啟健康檢查網址。前端目前會呼叫 `http://localhost:8000/api/analyze`，因此前後端都應使用本機預設埠號。

### 分析結果很少或沒有資料

Threads 對未登入訪客可能只顯示部分公開搜尋結果，之後要求登入或限制載入更多內容。因此本工具只能分析匿名訪客實際取得的公開貼文，不代表 Threads 的完整資料。Threads 頁面結構變更時，也可能需要同步調整爬蟲。

### 停止服務

在正在執行服務的終端機按 `Ctrl+C`。關閉終端機不會刪除虛擬環境或已安裝套件。

## 注意事項

- 僅分析 Threads 可公開存取的資料。
- Threads 頁面結構或存取限制變更時，爬蟲可能需要調整。
- 請遵守 Threads 使用條款、網站規範與適用的資料使用規定。
