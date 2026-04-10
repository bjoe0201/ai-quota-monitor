"""
GitHub Copilot Web 額度服務 — 透過 GitHub 的 user_session cookie
取得 Premium Request 使用量資訊。

使用方式:
  1. 用瀏覽器登入 https://github.com
  2. 開啟 DevTools (F12) → Application → Cookies → github.com
  3. 複製 user_session 的值
  4. 貼到設定中的「Session Cookie」欄位
"""
import re
import json
import requests
from .base import BaseService, ServiceResult

_GITHUB_BASE = "https://github.com"
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

# URL 參數說明:
# period: 時間範圍 (3=Current month)
# group: 分組方式 (7=Models)
# chart_selection: 圖表選擇
_DEFAULT_PARAMS = {
    "period": "3",       # Current month
    "group": "7",        # Group by Models
    "chart_selection": "2",
}


class GitHubCopilotWebService(BaseService):
    name = "GitHub Copilot 額度"

    def fetch(self, config: dict) -> ServiceResult:
        session_cookie = config.get("session_cookie", "").strip()
        if not session_cookie:
            return self._not_configured()

        cookies = {
            "user_session": session_cookie,
            "logged_in": "yes",
        }

        # 構建 URL
        params = dict(_DEFAULT_PARAMS)
        customer_id = config.get("customer_id", "").strip()
        if customer_id:
            params["customer"] = customer_id

        # ------ Step 1: 抓取 Premium Requests 頁面 ------
        try:
            r = requests.get(
                f"{_GITHUB_BASE}/settings/billing/premium_requests_usage",
                headers=_HEADERS,
                cookies=cookies,
                params=params,
                timeout=20,
                allow_redirects=True,
            )
        except requests.RequestException as e:
            return self._error(f"網路錯誤: {e}")

        if r.status_code == 401 or r.status_code == 403:
            return self._error("Session Cookie 無效或已過期，請重新從瀏覽器取得")
        if r.status_code == 404:
            return self._error("頁面不存在，可能需要 Copilot 訂閱")

        # 檢查是否被重導向到登入頁面
        if "/login" in r.url or "/session" in r.url:
            return self._error("Session Cookie 已過期，請重新從瀏覽器取得")

        if r.status_code != 200:
            return self._error(f"HTTP 錯誤 ({r.status_code})")

        html = r.text
        data = {}

        # ------ Step 2: 解析頁面 HTML ------
        self._parse_premium_requests_html(html, data)

        if not data:
            # 嘗試其他解析策略
            self._parse_with_json_embedded(html, data)

        if not data:
            return self._error("已連線但無法解析頁面資料，GitHub 頁面結構可能已變更")

        return ServiceResult(service_name=self.name, success=True, data=data)

    def _parse_premium_requests_html(self, html: str, data: dict):
        """解析 GitHub Premium Requests 頁面 HTML。"""

        # --- Included premium requests consumed ---
        # 格式: "716.59" of "1,500" 或類似
        included_pattern = re.compile(
            r'(?:Included\s+premium\s+requests?\s+consumed|included\s+requests?\s+consumed)'
            r'.*?'
            r'([\d,]+(?:\.\d+)?)\s*(?:of|/)\s*([\d,]+(?:\.\d+)?)',
            re.IGNORECASE | re.DOTALL
        )
        match = included_pattern.search(html)
        if match:
            consumed = float(match.group(1).replace(",", ""))
            total = float(match.group(2).replace(",", ""))
            data["included_consumed"] = consumed
            data["included_total"] = total
            if total > 0:
                data["included_percent"] = round(consumed / total * 100, 1)

        # 嘗試另一種模式來取得消耗量
        if "included_consumed" not in data:
            # 搜尋像 "716.59" 的大數字，後面跟著 "of 1,500"
            alt_pattern = re.compile(
                r'([\d,]+(?:\.\d+)?)\s*</?\w[^>]*>\s*(?:of|/)\s*([\d,]+(?:\.\d+)?)\s*included',
                re.IGNORECASE
            )
            match = alt_pattern.search(html)
            if match:
                consumed = float(match.group(1).replace(",", ""))
                total = float(match.group(2).replace(",", ""))
                data["included_consumed"] = consumed
                data["included_total"] = total
                if total > 0:
                    data["included_percent"] = round(consumed / total * 100, 1)

        # --- Billed premium requests ---
        billed_pattern = re.compile(
            r'(?:Billed\s+premium\s+requests?)\s*.*?\$\s*([\d,]+(?:\.\d+)?)',
            re.IGNORECASE | re.DOTALL
        )
        match = billed_pattern.search(html)
        if match:
            data["billed_amount"] = float(match.group(1).replace(",", ""))

        # --- 重置日期 ---
        reset_pattern = re.compile(
            r'(?:Monthly\s+limit\s+resets?\s+in|resets?\s+in)\s+(\d+)\s*days?',
            re.IGNORECASE
        )
        match = reset_pattern.search(html)
        if match:
            data["resets_in_days"] = int(match.group(1))

        # --- 每個 premium request 的價格 ---
        price_pattern = re.compile(
            r'Price\s+per\s+premium\s+request\s+is\s+\$([\d.]+)',
            re.IGNORECASE
        )
        match = price_pattern.search(html)
        if match:
            data["price_per_request"] = float(match.group(1))

        # --- 時間範圍 ---
        period_pattern = re.compile(
            r'Usage\s+for\s+([\w]+\s+\d+)\s*[-–]\s*([\w]+\s+\d+,?\s*\d*)',
            re.IGNORECASE
        )
        match = period_pattern.search(html)
        if match:
            data["usage_period"] = f"{match.group(1)} - {match.group(2)}"

        # --- 模型使用量明細表格 ---
        self._parse_model_table(html, data)

        # --- Copilot 方案 ---
        plan_pattern = re.compile(
            r'(?:your|included\s+in\s+your)\s+(?:<[^>]+>)?\s*(Copilot\s+\w+)\s*(?:</[^>]+>)?',
            re.IGNORECASE
        )
        match = plan_pattern.search(html)
        if match:
            data["copilot_plan"] = match.group(1).strip()

    def _parse_model_table(self, html: str, data: dict):
        """解析模型使用量表格。"""
        models = []

        # 嘗試找到表格行
        # GitHub HTML 中，每一行通常有: Model name, Included requests, Billed requests, Gross amount, Billed amount
        row_pattern = re.compile(
            r'<tr[^>]*>.*?</tr>',
            re.DOTALL
        )
        rows = row_pattern.findall(html)

        for row in rows:
            # 提取所有 <td> 內容
            td_pattern = re.compile(r'<td[^>]*>(.*?)</td>', re.DOTALL)
            cells = td_pattern.findall(row)
            if len(cells) >= 4:
                # 清理 HTML 標籤
                clean_cells = [re.sub(r'<[^>]+>', '', cell).strip() for cell in cells]
                model_name = clean_cells[0]

                # 跳過表頭或空行
                if not model_name or model_name.lower() in ("model", "total", ""):
                    continue

                # 嘗試解析數字
                try:
                    included_req = float(clean_cells[1].replace(",", "")) if clean_cells[1] else 0
                    model_info = {
                        "name": model_name,
                        "included_requests": included_req,
                    }
                    if len(clean_cells) >= 3:
                        billed_str = clean_cells[2].replace(",", "")
                        model_info["billed_requests"] = float(billed_str) if billed_str else 0
                    if len(clean_cells) >= 4:
                        gross = clean_cells[3].replace("$", "").replace(",", "").strip()
                        model_info["gross_amount"] = float(gross) if gross else 0
                    if len(clean_cells) >= 5:
                        billed = clean_cells[4].replace("$", "").replace(",", "").strip()
                        model_info["billed_amount"] = float(billed) if billed else 0

                    models.append(model_info)
                except (ValueError, IndexError):
                    continue

        if models:
            # 按使用量排序
            models.sort(key=lambda x: x.get("included_requests", 0), reverse=True)
            data["models"] = models
            data["total_models"] = len(models)

    def _parse_with_json_embedded(self, html: str, data: dict):
        """嘗試從 HTML 中尋找內嵌的 JSON 資料。"""
        # GitHub 有時會在 <script> 標籤中嵌入 JSON
        json_patterns = [
            re.compile(r'<script[^>]*data-target="react-app\.embeddedData"[^>]*>(.*?)</script>', re.DOTALL),
            re.compile(r'<react-partial[^>]*>.*?<script[^>]*>(.*?)</script>', re.DOTALL),
            re.compile(r'"premium_requests?":\s*({[^}]+})', re.DOTALL),
            re.compile(r'"usage":\s*({[^}]+})', re.DOTALL),
        ]

        for pattern in json_patterns:
            match = pattern.search(html)
            if match:
                try:
                    json_data = json.loads(match.group(1))
                    if isinstance(json_data, dict):
                        # 嘗試從 JSON 中提取有用的資訊
                        if "included" in json_data or "consumed" in json_data:
                            data["included_consumed"] = json_data.get("consumed", 0)
                            data["included_total"] = json_data.get("included", json_data.get("total", 0))
                            if data["included_total"] > 0:
                                data["included_percent"] = round(
                                    data["included_consumed"] / data["included_total"] * 100, 1
                                )
                            return
                except (json.JSONDecodeError, TypeError):
                    continue
