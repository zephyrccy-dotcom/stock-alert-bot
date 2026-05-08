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

summary_lines = ["**📊 6 隻股票今日收市數據總結**", ""]
summary_lines.append("| Ticker | 漲跌幅 | 成交量 | 成交金額 | 未平倉期權 |")
summary_lines.append("|--------|--------|--------|----------|------------|")

for ticker in TICKERS:
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period="5d")
        info = stock.info
        name = info.get('longName', ticker)[:25]

        if len(hist) >= 2:
            prev_close = hist['Close'].iloc[-2]
            close = hist['Close'].iloc[-1]
            change_pct = (close - prev_close) / prev_close * 100
            volume = int(hist['Volume'].iloc[-1])
            dollar_volume = int(close * volume)

            oi_text = "N/A"
            try:
                if stock.options:
                    expiry = stock.options[0]
                    opt = stock.option_chain(expiry)
                    total_oi = int(opt.calls['openInterest'].sum() + opt.puts['openInterest'].sum())
                    oi_text = f"{total_oi:,}"
            except:
                pass

            emoji = "🟢" if change_pct >= 0 else "🔴"
            summary_lines.append(f"| **{ticker}** | {emoji} **{change_pct:+.2f}%** | {volume:,} | **${dollar_volume:,}** | {oi_text} |")

    except:
        summary_lines.append(f"| **{ticker}** | 數據錯誤 | - | - | - |")

summary_lines.append("")
summary_lines.append("🟢 工具正常運行中。")

send_telegram("\n".join(summary_lines))

print("掃描完成！🎯")
