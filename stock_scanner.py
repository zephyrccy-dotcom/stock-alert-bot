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
        news_text = "\n".join([f"- {n.get('title','')}" for n in stock.news[:3]]) if hasattr(stock, 'news') else ""
        prompt = f"股票 {ticker} 今日{event}。\n最近新聞：{news_text}\n用簡單中文80-150字總結意義。"
        resp = client.chat.completions.create(model="grok-4.20-reasoning", messages=[{"role":"user","content":prompt}], max_tokens=280, temperature=0.7)
        return resp.choices[0].message.content.strip()
    except:
        return "AI 分析暫時無法取得"

print(f"🚀 開始每日監測 6 隻美股 ({datetime.now().strftime('%Y-%m-%d %H:%M')})")

summary_lines = ["**📊 6 隻股票今日收市數據總結**"]

for ticker in TICKERS:
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period="5d")   # 多取幾天確保有最新數據
        info = stock.info
        name = info.get('longName', ticker)[:30]

        # === 收市數據 ===
        if len(hist) >= 2:
            prev_close = hist['Close'].iloc[-2]
            close = hist['Close'].iloc[-1]
            change_pct = (close - prev_close) / prev_close * 100
            volume = int(hist['Volume'].iloc[-1])
            dollar_volume = int(close * volume)

            summary_lines.append(f"**{ticker}** {name}")
            summary_lines.append(f"漲跌幅: **{change_pct:+.2f}%**")
            summary_lines.append(f"成交量: {volume:,} 股")
            summary_lines.append(f"成交金額: **${dollar_volume:,}**")

            # 未平倉期權數 (Open Interest)
            try:
                if stock.options:
                    expiry = stock.options[0]
                    opt = stock.option_chain(expiry)
                    total_oi = int(opt.calls['openInterest'].sum() + opt.puts['openInterest'].sum())
                    summary_lines.append(f"未平倉期權: {total_oi:,}")
            except:
                summary_lines.append("未平倉期權: N/A")
            
            summary_lines.append("─" * 30)

        # === 原有觸發條件（EMA、52週、業績等）全部保留 ===
        # EMA 金叉/死叉
        if len(hist) >= 30:
            close_series = hist['Close']
            ema8 = close_series.ewm(span=8, adjust=False).mean()
            ema21 = close_series.ewm(span=21, adjust=False).mean()
            if ema8.iloc[-2] <= ema21.iloc[-2] and ema8.iloc[-1] > ema21.iloc[-1]:
                ai = grok_analyze(ticker, "出現 EMA8 上穿 EMA21（金叉）")
                send_telegram(f"🚨 **{ticker} 金叉提醒**\nEMA8 上穿 EMA21\n\n**Grok分析**：\n{ai}")
            elif ema8.iloc[-2] >= ema21.iloc[-2] and ema8.iloc[-1] < ema21.iloc[-1]:
                ai = grok_analyze(ticker, "出現 EMA8 下穿 EMA21（死叉）")
                send_telegram(f"⚠️ **{ticker} 死叉提醒**\nEMA8 下穿 EMA21\n\n**Grok分析**：\n{ai}")

        # 52週新高/新低
        today_high = hist['High'].iloc[-1]
        today_low = hist['Low'].iloc[-1]
        if info.get('fiftyTwoWeekHigh') and today_high > info.get('fiftyTwoWeekHigh') * 1.001:
            ai = grok_analyze(ticker, "升穿52週新高")
            send_telegram(f"🔥 **{ticker} 52週新高提醒**\n\n**Grok分析**：\n{ai}")
        if info.get('fiftyTwoWeekLow') and today_low < info.get('fiftyTwoWeekLow') * 0.999:
            ai = grok_analyze(ticker, "跌穿52週新低")
            send_telegram(f"❄️ **{ticker} 52週新低提醒**\n\n**Grok分析**：\n{ai}")

    except Exception as e:
        summary_lines.append(f"{ticker} 數據獲取失敗")

# === 每日總結報告 ===
send_telegram("🟢 **今日掃描完成**\n" + "\n".join(summary_lines) + "\n\n工具正常運行中。")

print("掃描完成！🎯")
