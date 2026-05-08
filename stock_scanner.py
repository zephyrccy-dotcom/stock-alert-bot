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

TICKERS = ["SNDK", "LITE", "COHR", "GLW", "INTC", "DELL"]

def send_telegram(message):
    for chat_id in CHAT_IDS:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        data = {"chat_id": chat_id, "text": message, "parse_mode": "Markdown"}
        try:
            requests.post(url, data=data)
        except:
            pass

print(f"🚀 開始每日監測 6 隻美股 ({datetime.now().strftime('%Y-%m-%d %H:%M')})")

lines = ["**📊 6 隻股票今日收市數據總結**", ""]
lines.append("```")
lines.append("Ticker   漲跌幅     業績倒數")

for ticker in TICKERS:
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period="15d")   # 多取幾天計算10日平均
        info = stock.info

        # 漲跌幅
        if len(hist) >= 2:
            prev_close = hist['Close'].iloc[-2]
            close = hist['Close'].iloc[-1]
            change_pct = (close - prev_close) / prev_close * 100
            emoji = "🟢" if change_pct >= 0 else "🔴"

            # 業績倒數
            earnings_str = "N/A"
            try:
                cal = stock.calendar
                if not cal.empty:
                    earnings_date = cal.index[0] if hasattr(cal.index, 'date') else cal.iloc[0].name
                    if isinstance(earnings_date, str):
                        earnings_date = datetime.strptime(earnings_date[:10], "%Y-%m-%d").date()
                    days_left = (earnings_date - datetime.now().date()).days
                    if days_left > 0:
                        earnings_str = f"{days_left}天"
                    elif days_left == 0:
                        earnings_str = "今日"
                    else:
                        earnings_str = "已過"
            except:
                pass

            line = f"{ticker:5}  {emoji} {change_pct:+6.2f}%   {earnings_str:>6}"
            lines.append(line)

            # === 新增：成交量異常提示 ===
            if len(hist) >= 11:
                today_vol = hist['Volume'].iloc[-1]
                avg_vol_10d = hist['Volume'].iloc[-11:-1].mean()
                if today_vol > avg_vol_10d * 1.3:
                    ratio = (today_vol / avg_vol_10d - 1) * 100
                    send_telegram(f"🚀 **{ticker} 成交量異常放大**\n今日成交量比10日平均高 **{ratio:.0f}%**")

    except:
        lines.append(f"{ticker:5}  ❌ 數據錯誤")

lines.append("```")
lines.append("")
lines.append("🟢 工具正常運行中。")

send_telegram("\n".join(lines))

print("掃描完成！🎯")
