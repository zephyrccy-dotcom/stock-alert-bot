import yfinance as yf
import pandas as pd
from datetime import datetime
import requests
import os
from openai import OpenAI

TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
GROK_API_KEY = os.environ["GROK_API_KEY"]

CHAT_IDS = [
    os.environ["TELEGRAM_CHAT_ID"],
    "-1003950002425"
]

client = OpenAI(api_key=GROK_API_KEY, base_url="https://api.x.ai/v1")

# ================== 更新後觀察列表（30隻，已去重） ==================
TICKERS = [
    "PICK", "IREN", "CRSP", "LITX", "SMCI", "APPX", "RGC", "NOK", "ABEV", "SJ",
    "SNDK", "LITE", "COHR", "GLW", "INTC", "DELL",
    "6990.HK", "2476.HK", "RKLB", "MDA", "IRDM", "PL", "TDY", "APH",
    "KTOS", "ASTS", "RDW", "GILT", "HXL", "ATI"
]

def send_telegram(message):
    for chat_id in CHAT_IDS:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        data = {"chat_id": chat_id, "text": message, "parse_mode": "Markdown"}
        try:
            requests.post(url, data=data)
        except:
            pass

print(f"🚀 開始每日監測 {len(TICKERS)} 隻股票 ({datetime.now().strftime('%Y-%m-%d %H:%M')})")

lines = ["**📊 今日收市數據總結**", ""]
lines.append("```")
lines.append("Ticker   漲跌幅     板塊")

for ticker in TICKERS:
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period="15d")
        info = stock.info

        if len(hist) >= 2:
            prev_close = hist['Close'].iloc[-2]
            close = hist['Close'].iloc[-1]
            change_pct = (close - prev_close) / prev_close * 100
            emoji = "🟢" if change_pct >= 0 else "🔴"

            sector = info.get('sector', info.get('industry', 'N/A'))[:18]

            line = f"{ticker:6}  {emoji} {change_pct:+6.2f}%   {sector}"
            lines.append(line)

            # 成交量異常放大提示
            if len(hist) >= 11:
                today_vol = hist['Volume'].iloc[-1]
                avg_vol_10d = hist['Volume'].iloc[-11:-1].mean()
                if today_vol > avg_vol_10d * 1.3:
                    ratio = (today_vol / avg_vol_10d - 1) * 100
                    send_telegram(f"🚀 **{ticker} 成交量異常放大**\n今日比10日平均高 **{ratio:.0f}%**")

    except:
        lines.append(f"{ticker:6}  ❌ 數據錯誤")

lines.append("```")
lines.append("")
lines.append("🟢 工具正常運行中。")

send_telegram("\n".join(lines))

print("掃描完成！🎯")
