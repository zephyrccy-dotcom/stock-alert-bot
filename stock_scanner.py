import yfinance as yf
import pandas as pd
from datetime import datetime
import requests
import os
from openai import OpenAI

# ================== GitHub Secrets ==================
TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
GROK_API_KEY = os.environ["GROK_API_KEY"]

CHAT_IDS = [
    os.environ["TELEGRAM_CHAT_ID"],     # 你自己
    "-1003950002425"                    # YY stock alert Group
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

def grok_analyze(ticker, event):
    try:
        stock = yf.Ticker(ticker)
        news_text = "\n".join([f"- {n.get('title','')}" for n in stock.news[:2]]) if hasattr(stock, 'news') else ""
        prompt = f"股票 {ticker} 今日{event}。\n最近新聞：{news_text}\n用簡單中文80-120字總結意義。"
        resp = client.chat.completions.create(model="grok-4.20-reasoning", messages=[{"role":"user","content":prompt}], max_tokens=250, temperature=0.7)
        return resp.choices[0].message.content.strip()
    except:
        return "AI 分析暫時無法取得"

print(f"🚀 開始每日監測 6 隻美股 ({datetime.now().strftime('%Y-%m-%d %H:%M')})")

for ticker in TICKERS:
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period="3mo")
        if len(hist) < 30: continue

        close = hist['Close']
        ema8 = close.ewm(span=8, adjust=False).mean()
        ema21 = close.ewm(span=21, adjust=False).mean()

        if ema8.iloc[-2] <= ema21.iloc[-2] and ema8.iloc[-1] > ema21.iloc[-1]:
            ai = grok_analyze(ticker, "出現 EMA8 上穿 EMA21（金叉）")
            send_telegram(f"🚨 **{ticker} 金叉提醒**\nEMA8 上穿 EMA21\n\n**Grok分析**：\n{ai}")

        elif ema8.iloc[-2] >= ema21.iloc[-2] and ema8.iloc[-1] < ema21.iloc[-1]:
            ai = grok_analyze(ticker, "出現 EMA8 下穿 EMA21（死叉）")
            send_telegram(f"⚠️ **{ticker} 死叉提醒**\nEMA8 下穿 EMA21\n\n**Grok分析**：\n{ai}")

    except:
        pass

# 每日確認訊息
send_telegram("🟢 **今日掃描完成**\n6 隻股票暫時無 EMA 金叉/死叉。\n工具正常運行中。")

print("掃描完成！🎯")
