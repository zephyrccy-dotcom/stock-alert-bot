import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
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

def grok_analyze(ticker, event, extra_info=""):
    try:
        stock = yf.Ticker(ticker)
        news_text = "\n".join([f"- {n.get('title','')}" for n in stock.news[:3]]) if hasattr(stock, 'news') else ""
        prompt = f"股票 {ticker} 今日{event}。\n{extra_info}\n最近新聞：{news_text}\n用簡單中文80-120字總結意義同影響。"
        resp = client.chat.completions.create(
            model="grok-4.20-reasoning",
            messages=[{"role":"user","content":prompt}],
            max_tokens=280,
            temperature=0.7
        )
        return resp.choices[0].message.content.strip()
    except:
        return "AI 分析暫時無法取得"

print(f"🚀 開始每日監測 6 隻美股 ({datetime.now().strftime('%Y-%m-%d %H:%M')})")
print("股票名單：SNDK, LITE, COHR, GLW, INTC, DELL\n")

for ticker in TICKERS:
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period="3mo")
        info = stock.info
        name = info.get('longName', ticker)

        # 1. EMA 金叉 / 死叉
        if len(hist) >= 30:
            close = hist['Close']
            ema8 = close.ewm(span=8, adjust=False).mean()
            ema21 = close.ewm(span=21, adjust=False).mean()

            if ema8.iloc[-2] <= ema21.iloc[-2] and ema8.iloc[-1] > ema21.iloc[-1]:
                ai = grok_analyze(ticker, "出現 EMA8 上穿 EMA21（金叉）")
                send_telegram(f"🚨 **{ticker} ({name}) 金叉提醒**\nEMA8 上穿 EMA21\n\n**Grok分析**：\n{ai}")

            elif ema8.iloc[-2] >= ema21.iloc[-2] and ema8.iloc[-1] < ema21.iloc[-1]:
                ai = grok_analyze(ticker, "出現 EMA8 下穿 EMA21（死叉）")
                send_telegram(f"⚠️ **{ticker} ({name}) 死叉提醒**\nEMA8 下穿 EMA21\n\n**Grok分析**：\n{ai}")

        # 2. 52週新高 / 新低
        today_high = hist['High'].iloc[-1]
        today_low = hist['Low'].iloc[-1]
        week52_high = info.get('fiftyTwoWeekHigh')
        week52_low = info.get('fiftyTwoWeekLow')

        if week52_high and today_high > week52_high * 1.001:
            ai = grok_analyze(ticker, "升穿52週新高")
            send_telegram(f"🔥 **{ticker} ({name}) 52週新高提醒**\n今日高位突破52週高位\n\n**Grok分析**：\n{ai}")

        if week52_low and today_low < week52_low * 0.999:
            ai = grok_analyze(ticker, "跌穿52週新低")
            send_telegram(f"❄️ **{ticker} ({name}) 52週新低提醒**\n今日低位跌穿52週低位\n\n**Grok分析**：\n{ai}")

        # 3. 業績倒數 + 出業績結果
        try:
            cal = stock.calendar
            if not cal.empty:
                earnings_date = cal.index[0] if isinstance(cal.index, pd.DatetimeIndex) else cal.iloc[0].name
                if isinstance(earnings_date, str):
                    earnings_date = datetime.strptime(earnings_date, "%Y-%m-%d").date()
                days_to_earnings = (earnings_date - datetime.now().date()).days

                if 1 <= days_to_earnings <= 7:
                    send_telegram(f"📅 **{ticker} ({name}) 業績倒數**\n距離業績還有 **{days_to_earnings} 天**（{earnings_date}）")

                elif days_to_earnings == 0 or days_to_earnings == -1:  # 今日或昨日出業績
                    ai = grok_analyze(ticker, "剛出業績")
                    send_telegram(f"📊 **{ticker} ({name}) 業績已公佈**\n{Grok分析**：\n{ai}")
        except:
            pass

        # 4. 新聞 / 重大公告 / 派息（已包含在 Grok 分析中）

    except Exception as e:
        print(f"{ticker} 掃描出錯: {e}")

# 每日確認訊息
send_telegram("🟢 **今日掃描完成**\n已檢查 6 隻股票（SNDK, LITE, COHR, GLW, INTC, DELL）\n所有條件（EMA、52週、業績倒數、新聞）已掃描。\n工具正常運行中。")

print("掃描完成！🎯")
