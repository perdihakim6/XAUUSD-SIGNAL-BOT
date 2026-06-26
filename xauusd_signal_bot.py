#!/usr/bin/env python3
"""
XAUUSD ULTIMATE SIGNAL BOT v3
All 7 Intelligence Upgrades:
1. News & Sentiment Realtime
2. Economic Calendar
3. DXY Monitoring
4. Multi-Timeframe (M15/H1/H4/D1)
5. Full Indicators (BB/Stoch/ATR/ADX/Fibo)
6. Market Sentiment (Fear&Greed/COT/ETF)
7. Master AI Prompt
"""

import requests
import json
import time
from datetime import datetime, timedelta
import schedule
import logging
import pytz
import math

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class XAUUSDUltimateBot:
    def __init__(self, twelve_key, groq_key, telegram_token, chat_id):
        self.twelve_key = twelve_key
        self.groq_key = groq_key
        self.telegram_token = telegram_token
        self.chat_id = chat_id
        self.groq_url = "https://api.groq.com/openai/v1/chat/completions"
        self.twelve_url = "https://api.twelvedata.com"
        self.wib = pytz.timezone('Asia/Jakarta')

    # ════════════════════════════════════════
    # 1. MARKET DATA
    # ════════════════════════════════════════

    def fetch_ohlcv(self, interval="1h", outputsize=50):
        try:
            params = {
                "symbol": "XAU/USD",
                "interval": interval,
                "outputsize": outputsize,
                "apikey": self.twelve_key
            }
            r = requests.get(f"{self.twelve_url}/time_series", params=params, timeout=15)
            if r.status_code == 200:
                data = r.json()
                if data.get("status") == "ok":
                    logger.info(f"✅ OHLCV {interval}: {len(data['values'])} candles")
                    return data["values"]
            return None
        except Exception as e:
            logger.error(f"OHLCV {interval} error: {e}")
            return None

    def fetch_indicator(self, name, interval="1h", **kwargs):
        try:
            params = {"symbol": "XAU/USD", "interval": interval, "apikey": self.twelve_key, **kwargs}
            r = requests.get(f"{self.twelve_url}/{name}", params=params, timeout=15)
            if r.status_code == 200:
                data = r.json()
                if data.get("status") == "ok":
                    return data.get("values", [])
            return None
        except Exception as e:
            logger.error(f"{name} error: {e}")
            return None

    # ════════════════════════════════════════
    # 2. DXY MONITORING
    # ════════════════════════════════════════

    def fetch_dxy(self):
        try:
            logger.info("💵 Fetching DXY...")
            params = {"symbol": "DXY", "interval": "1h", "outputsize": 5, "apikey": self.twelve_key}
            r = requests.get(f"{self.twelve_url}/time_series", params=params, timeout=15)
            if r.status_code == 200:
                data = r.json()
                if data.get("status") == "ok":
                    c = data["values"]
                    curr = float(c[0]['close'])
                    prev1h = float(c[1]['close']) if len(c) > 1 else curr
                    prev4h = float(c[4]['close']) if len(c) > 4 else curr
                    chg1h = ((curr - prev1h) / prev1h) * 100
                    chg4h = ((curr - prev4h) / prev4h) * 100
                    trend = "STRENGTHENING 📈" if chg1h > 0.1 else "WEAKENING 📉" if chg1h < -0.1 else "STABLE ➡️"
                    impact = "BEARISH for Gold 🔴" if chg1h > 0.1 else "BULLISH for Gold 🟢" if chg1h < -0.1 else "NEUTRAL"
                    logger.info(f"✅ DXY: {curr:.2f} ({chg1h:+.3f}%)")
                    return {"current": curr, "chg1h": chg1h, "chg4h": chg4h, "trend": trend, "impact": impact}
            return {"current": "N/A", "chg1h": 0, "chg4h": 0, "trend": "Unknown", "impact": "Unknown"}
        except Exception as e:
            logger.error(f"DXY error: {e}")
            return {"current": "N/A", "chg1h": 0, "chg4h": 0, "trend": "Unknown", "impact": "Unknown"}

    # ════════════════════════════════════════
    # 3. NEWS & SENTIMENT
    # ════════════════════════════════════════

    def fetch_news(self):
        try:
            logger.info("📰 Fetching gold news...")
            news = []

            # Source 1: Twelve Data news
            try:
                params = {"symbol": "XAU/USD", "outputsize": 5, "apikey": self.twelve_key}
                r = requests.get(f"{self.twelve_url}/news", params=params, timeout=10)
                if r.status_code == 200:
                    data = r.json()
                    if isinstance(data, list):
                        for item in data[:5]:
                            news.append({"title": item.get("title",""), "source": item.get("source",""), "time": item.get("datetime","")})
            except: pass

            # Source 2: RSS Yahoo Finance Gold
            if len(news) < 3:
                try:
                    import xml.etree.ElementTree as ET
                    r = requests.get(
                        "https://feeds.finance.yahoo.com/rss/2.0/headline?s=GC=F&region=US&lang=en-US",
                        timeout=8, headers={"User-Agent": "Mozilla/5.0"}
                    )
                    if r.status_code == 200:
                        root = ET.fromstring(r.content)
                        for item in root.findall('.//item')[:5]:
                            t = item.find('title')
                            d = item.find('pubDate')
                            if t is not None:
                                news.append({"title": t.text or "", "source": "Yahoo Finance", "time": d.text if d is not None else ""})
                except: pass

            # Source 3: MarketWatch RSS
            if len(news) < 3:
                try:
                    import xml.etree.ElementTree as ET
                    r = requests.get(
                        "https://feeds.marketwatch.com/marketwatch/realtimeheadlines/",
                        timeout=8, headers={"User-Agent": "Mozilla/5.0"}
                    )
                    if r.status_code == 200:
                        root = ET.fromstring(r.content)
                        for item in root.findall('.//item')[:5]:
                            t = item.find('title')
                            if t is not None and t.text and any(kw in t.text.lower() for kw in ['gold','fed','dollar','inflation','rate']):
                                news.append({"title": t.text, "source": "MarketWatch", "time": ""})
                except: pass

            logger.info(f"✅ News: {len(news)} articles")
            return news[:5] if news else [{"title": "No news available", "source": "", "time": ""}]
        except Exception as e:
            logger.error(f"News error: {e}")
            return [{"title": "News fetch failed", "source": "", "time": ""}]

    def analyze_news_sentiment(self, news):
        """Simple sentiment from headlines"""
        bullish_kw = ['rise','rally','surge','gain','jump','up','high','strong','buy','bull','rate cut','dovish','war','tension','inflation']
        bearish_kw = ['fall','drop','decline','down','low','weak','sell','bear','rate hike','hawkish','strong dollar','sell off']
        
        bull = bear = 0
        for n in news:
            title = n['title'].lower()
            bull += sum(1 for kw in bullish_kw if kw in title)
            bear += sum(1 for kw in bearish_kw if kw in title)
        
        if bull > bear + 1: return "BULLISH 🟢"
        if bear > bull + 1: return "BEARISH 🔴"
        return "NEUTRAL ➡️"

    # ════════════════════════════════════════
    # 4. ECONOMIC CALENDAR
    # ════════════════════════════════════════

    def fetch_economic_calendar(self):
        try:
            logger.info("📅 Fetching economic calendar...")
            now = datetime.now(self.wib)
            events = []

            try:
                params = {
                    "start_date": now.strftime("%Y-%m-%d"),
                    "end_date": (now + timedelta(days=2)).strftime("%Y-%m-%d"),
                    "apikey": self.twelve_key
                }
                r = requests.get(f"{self.twelve_url}/economic_calendar", params=params, timeout=10)
                if r.status_code == 200:
                    data = r.json()
                    results = data.get("result", []) if isinstance(data, dict) else []
                    for ev in results:
                        if ev.get("country") == "US" and ev.get("impact","").upper() in ["HIGH","MEDIUM"]:
                            events.append({
                                "name": ev.get("event",""),
                                "impact": ev.get("impact","").upper(),
                                "time": ev.get("time",""),
                                "previous": ev.get("previous",""),
                                "forecast": ev.get("forecast","")
                            })
            except: pass

            if not events:
                events = [{"name": "Check investing.com/economic-calendar", "impact": "INFO", "time": "", "previous": "", "forecast": ""}]

            logger.info(f"✅ Events: {len(events)}")
            return events[:5]
        except Exception as e:
            logger.error(f"Calendar error: {e}")
            return []

    # ════════════════════════════════════════
    # 5. MARKET SENTIMENT
    # ════════════════════════════════════════

    def fetch_fear_greed(self):
        try:
            logger.info("🌡️ Fetching Fear & Greed...")
            r = requests.get("https://api.alternative.me/fng/?limit=1", timeout=10)
            if r.status_code == 200:
                data = r.json()
                val = int(data['data'][0]['value'])
                label = data['data'][0]['value_classification']
                logger.info(f"✅ Fear&Greed: {val} ({label})")
                return {"value": val, "label": label,
                        "impact": "BEARISH for Gold 🔴" if val > 75 else "BULLISH for Gold 🟢" if val < 25 else "NEUTRAL"}
        except Exception as e:
            logger.error(f"Fear&Greed error: {e}")
        return {"value": 50, "label": "Neutral", "impact": "NEUTRAL"}

    def fetch_gold_etf_sentiment(self):
        try:
            logger.info("📦 Fetching Gold ETF (GLD)...")
            params = {"symbol": "GLD", "interval": "1day", "outputsize": 5, "apikey": self.twelve_key}
            r = requests.get(f"{self.twelve_url}/time_series", params=params, timeout=10)
            if r.status_code == 200:
                data = r.json()
                if data.get("status") == "ok":
                    c = data["values"]
                    curr = float(c[0]['close'])
                    prev = float(c[1]['close']) if len(c) > 1 else curr
                    chg = ((curr - prev) / prev) * 100
                    vol_curr = float(c[0].get('volume', 0))
                    vol_prev = float(c[1].get('volume', 0)) if len(c) > 1 else vol_curr
                    vol_trend = "HIGH VOLUME 🔥" if vol_curr > vol_prev * 1.2 else "LOW VOLUME" if vol_curr < vol_prev * 0.8 else "NORMAL VOLUME"
                    logger.info(f"✅ GLD ETF: ${curr:.2f} ({chg:+.2f}%)")
                    return {"price": curr, "change": chg, "volume_trend": vol_trend,
                            "flow": "INFLOW 🟢" if chg > 0.2 else "OUTFLOW 🔴" if chg < -0.2 else "NEUTRAL"}
        except Exception as e:
            logger.error(f"ETF error: {e}")
        return {"price": 0, "change": 0, "volume_trend": "N/A", "flow": "N/A"}

    # ════════════════════════════════════════
    # 6. ADVANCED INDICATORS (calculated)
    # ════════════════════════════════════════

    def calc_fibonacci(self, candles, period=20):
        try:
            highs = [float(c['high']) for c in candles[:period]]
            lows = [float(c['low']) for c in candles[:period]]
            high = max(highs)
            low = min(lows)
            diff = high - low
            return {
                "high": high, "low": low,
                "fib_236": high - diff * 0.236,
                "fib_382": high - diff * 0.382,
                "fib_500": high - diff * 0.500,
                "fib_618": high - diff * 0.618,
                "fib_786": high - diff * 0.786
            }
        except:
            return None

    def calc_bollinger(self, candles, period=20):
        try:
            closes = [float(c['close']) for c in candles[:period]]
            sma = sum(closes) / len(closes)
            std = math.sqrt(sum((x - sma)**2 for x in closes) / len(closes))
            upper = sma + 2 * std
            lower = sma - 2 * std
            curr = closes[0]
            width = ((upper - lower) / sma) * 100
            pos = "UPPER BAND (Overbought ⚠️)" if curr > upper else "LOWER BAND (Oversold ⚠️)" if curr < lower else "MIDDLE BAND ✅"
            return {"upper": upper, "middle": sma, "lower": lower, "width": width, "position": pos}
        except:
            return None

    def calc_atr(self, candles, period=14):
        try:
            trs = []
            for i in range(min(period, len(candles)-1)):
                h = float(candles[i]['high'])
                l = float(candles[i]['low'])
                pc = float(candles[i+1]['close'])
                trs.append(max(h-l, abs(h-pc), abs(l-pc)))
            atr = sum(trs) / len(trs) if trs else 0
            volatility = "HIGH 🔥" if atr > 15 else "MEDIUM" if atr > 8 else "LOW"
            return {"value": round(atr, 2), "volatility": volatility}
        except:
            return None

    def detect_pattern(self, candles):
        try:
            if len(candles) < 3: return "Unknown"
            c1 = candles[0]
            o1,c1v,h1,l1 = float(c1['open']),float(c1['close']),float(c1['high']),float(c1['low'])
            c2 = candles[1]
            o2,c2v = float(c2['open']),float(c2['close'])
            body1 = abs(c1v-o1); range1 = h1-l1
            lower_shadow = min(o1,c1v)-l1; upper_shadow = h1-max(o1,c1v)
            if range1 == 0: return "Flat Candle"
            if body1 < range1*0.1: return "Doji (Indecision ⚠️)"
            if lower_shadow > body1*2 and upper_shadow < body1*0.5: return "Hammer (Bullish Reversal 🟢)"
            if upper_shadow > body1*2 and lower_shadow < body1*0.5: return "Shooting Star (Bearish 🔴)"
            if c2v < o2 and c1v > o1 and c1v > o2 and o1 < c2v: return "Bullish Engulfing 🟢"
            if c2v > o2 and c1v < o1 and c1v < o2 and o1 > c2v: return "Bearish Engulfing 🔴"
            if c1v > o1 and body1 > range1*0.7: return "Strong Bullish Candle 🟢"
            if c1v < o1 and body1 > range1*0.7: return "Strong Bearish Candle 🔴"
            return "Normal Candle"
        except: return "Unknown"

    def calc_support_resistance(self, candles):
        try:
            highs = [float(c['high']) for c in candles[:20]]
            lows = [float(c['low']) for c in candles[:20]]
            return {
                "resistance": max(highs),
                "support": min(lows),
                "mid": (max(highs)+min(lows))/2
            }
        except: return None

    # ════════════════════════════════════════
    # 7. MASTER AI PROMPT
    # ════════════════════════════════════════

    def analyze_master(self, d):
        try:
            logger.info("🤖 Master AI analyzing all data...")

            news_txt = "\n".join([f"  • {n['title'][:80]}" for n in d['news'][:4]])
            events_txt = "\n".join([f"  ⚡ [{e['impact']}] {e['name']} - Prev: {e['previous']} | Forecast: {e['forecast']}" for e in d['events'][:3]]) or "  No major events"
            fib = d.get('fib', {})
            bb = d.get('bb', {})
            atr = d.get('atr', {})
            fg = d.get('fear_greed', {})
            etf = d.get('etf', {})
            dxy = d.get('dxy', {})

            prompt = f"""You are a GRANDMASTER XAUUSD trader and analyst with 30 years experience.
You have access to the most complete trading data possible.
Your analysis combines: Technical + Fundamental + Sentiment + Macro.

════════════════════════════════════════════════
🥇 XAUUSD COMPLETE INTELLIGENCE REPORT
════════════════════════════════════════════════

💰 CURRENT PRICE: ${d['price']:,.2f}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 MULTI-TIMEFRAME ANALYSIS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[M15 - Entry Timing]
  Last candle: O:{d['m15_o']} H:{d['m15_h']} L:{d['m15_l']} C:{d['m15_c']}
  Pattern: {d['m15_pattern']}

[H1 - Signal Timeframe]
  Last 3 candles:
{d['h1_summary']}
  Pattern: {d['h1_pattern']}

[H4 - Confirmation]
  Close: ${d['h4_close']:,.2f} | Change: {d['h4_chg']:+.3f}%
  Pattern: {d['h4_pattern']}

[D1 - Big Picture Trend]
  Close: ${d['d1_close']:,.2f} | Change: {d['d1_chg']:+.3f}%

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📈 TECHNICAL INDICATORS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
EMA 20:  ${d['ema20']:,.2f} | Price {'ABOVE ✅' if d['price']>d['ema20'] else 'BELOW ❌'}
EMA 50:  ${d['ema50']:,.2f} | Price {'ABOVE ✅' if d['price']>d['ema50'] else 'BELOW ❌'}
EMA 200: ${d['ema200']:,.2f} | Price {'ABOVE ✅' if d['price']>d['ema200'] else 'BELOW ❌'}

RSI (14): {d['rsi']} {'⚠️ OVERBOUGHT' if d['rsi']>70 else '⚠️ OVERSOLD' if d['rsi']<30 else '✅ NORMAL'}
MACD: {d['macd']:+.3f} | Signal: {d['macd_sig']:+.3f} | Hist: {d['macd_hist']:+.3f}
  → MACD {'BULLISH CROSS 🟢' if d['macd']>d['macd_sig'] else 'BEARISH CROSS 🔴'}

Bollinger Bands:
  Upper: ${bb.get('upper',0):,.2f} | Mid: ${bb.get('middle',0):,.2f} | Lower: ${bb.get('lower',0):,.2f}
  Width: {bb.get('width',0):.2f}% | Position: {bb.get('position','N/A')}

ATR (14): {atr.get('value',0)} | Volatility: {atr.get('volatility','N/A')}

Fibonacci Levels:
  High: ${fib.get('high',0):,.2f} | Low: ${fib.get('low',0):,.2f}
  Fib 23.6%: ${fib.get('fib_236',0):,.2f}
  Fib 38.2%: ${fib.get('fib_382',0):,.2f}
  Fib 50.0%: ${fib.get('fib_500',0):,.2f}
  Fib 61.8%: ${fib.get('fib_618',0):,.2f} ← Golden Ratio

Support: ${d['sr'].get('support',0):,.2f}
Resistance: ${d['sr'].get('resistance',0):,.2f}
Mid: ${d['sr'].get('mid',0):,.2f}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💵 MACRO: DXY (US DOLLAR INDEX)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
DXY: {dxy.get('current','N/A')} | 1H: {dxy.get('chg1h',0):+.3f}% | 4H: {dxy.get('chg4h',0):+.3f}%
DXY Trend: {dxy.get('trend','N/A')}
Impact on Gold: {dxy.get('impact','N/A')}
Rule: DXY UP = Gold DOWN | DXY DOWN = Gold UP

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📰 NEWS & FUNDAMENTAL SENTIMENT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Overall Sentiment: {d['news_sentiment']}
Latest Headlines:
{news_txt}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📅 ECONOMIC CALENDAR (Next 48h)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{events_txt}
⚠️ HIGH IMPACT events = avoid trading 30min before/after!

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🌡️ MARKET SENTIMENT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Crypto Fear & Greed: {fg.get('value',50)} - {fg.get('label','Neutral')}
  Impact: {fg.get('impact','NEUTRAL')}

Gold ETF (GLD): ${etf.get('price',0):.2f} ({etf.get('change',0):+.2f}%)
  Flow: {etf.get('flow','N/A')} | Volume: {etf.get('volume_trend','N/A')}

════════════════════════════════════════════════

TRADING RULES:
1. ALL factors must be analyzed together
2. Technical + DXY + News must ALIGN
3. HIGH IMPACT event coming → WAIT (risk management!)
4. If DXY conflicts with technicals → WAIT
5. Confidence > 75% required for BUY/SELL signal
6. Minimum Risk/Reward = 1:2
7. Use Fibonacci + Support/Resistance for SL/TP
8. ATR high → wider SL needed
9. Fear & Greed extreme → contrarian signal possible

Based on COMPLETE analysis, provide your BEST signal:

Respond ONLY in JSON:
{{"action":"BUY/SELL/WAIT","confidence":0-100,"entry":price,"sl":price,"tp":price,"rr":"1:X","trend":"BULLISH/BEARISH/NEUTRAL","dxy_aligned":true/false,"news_sentiment":"BULLISH/BEARISH/NEUTRAL","event_risk":"HIGH/MEDIUM/LOW","key_level":"nearest fib or SR level","reason":"max 50 words - combine ALL factors"}}"""

            payload = {
                "model": "llama-3.1-70b-versatile",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.15,
                "max_tokens": 500
            }
            headers = {
                "Authorization": f"Bearer {self.groq_key}",
                "Content-Type": "application/json"
            }
            r = requests.post(self.groq_url, json=payload, headers=headers, timeout=30)
            if r.status_code == 200:
                result = r.json()
                content = result['choices'][0]['message']['content']
                if "```" in content:
                    content = content.split("```")[1]
                    if content.startswith("json"): content = content[4:]
                    content = content.split("```")[0]
                analysis = json.loads(content.strip())
                logger.info(f"✅ Master AI: {analysis.get('action')} ({analysis.get('confidence')}%)")
                return analysis
            else:
                logger.error(f"Groq error: {r.status_code} - {r.text[:200]}")
                return None
        except Exception as e:
            logger.error(f"Master AI error: {e}")
            return None

    # ════════════════════════════════════════
    # TELEGRAM
    # ════════════════════════════════════════

    def send_telegram(self, msg):
        try:
            url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
            requests.post(url, json={"chat_id": self.chat_id, "text": msg, "parse_mode": "HTML"}, timeout=10)
        except Exception as e:
            logger.error(f"Telegram error: {e}")

    # ════════════════════════════════════════
    # MAIN RUN
    # ════════════════════════════════════════

    def run(self):
        logger.info("=" * 65)
        logger.info(f"[{datetime.now(self.wib).strftime('%Y-%m-%d %H:%M:%S WIB')}] ULTIMATE ANALYSIS")
        logger.info("=" * 65)

        try:
            # FETCH ALL DATA
            m15 = self.fetch_ohlcv("15min", 10); time.sleep(0.5)
            h1  = self.fetch_ohlcv("1h", 50);   time.sleep(0.5)
            h4  = self.fetch_ohlcv("4h", 10);   time.sleep(0.5)
            d1  = self.fetch_ohlcv("1day", 5);  time.sleep(0.5)

            if not h1:
                self.send_telegram("⚠️ Failed to fetch XAUUSD H1 data")
                return

            price = float(h1[0]['close'])

            # INDICATORS
            ema20  = self.fetch_indicator("ema",  "1h", time_period=20);  time.sleep(0.5)
            ema50  = self.fetch_indicator("ema",  "1h", time_period=50);  time.sleep(0.5)
            ema200 = self.fetch_indicator("ema",  "1h", time_period=200); time.sleep(0.5)
            rsi    = self.fetch_indicator("rsi",  "1h", time_period=14);  time.sleep(0.5)
            macd   = self.fetch_indicator("macd", "1h", fast_period=12, slow_period=26, signal_period=9); time.sleep(0.5)

            # ADVANCED (calculated locally - saves API calls)
            bb  = self.calc_bollinger(h1)
            atr = self.calc_atr(h1)
            fib = self.calc_fibonacci(h1)
            sr  = self.calc_support_resistance(h1)

            # PATTERNS
            m15_pat = self.detect_pattern(m15) if m15 else "N/A"
            h1_pat  = self.detect_pattern(h1)
            h4_pat  = self.detect_pattern(h4) if h4 else "N/A"

            # DXY
            dxy = self.fetch_dxy(); time.sleep(0.5)

            # NEWS
            news = self.fetch_news(); time.sleep(0.5)
            news_sentiment = self.analyze_news_sentiment(news)

            # ECONOMIC CALENDAR
            events = self.fetch_economic_calendar(); time.sleep(0.5)

            # SENTIMENT
            fg  = self.fetch_fear_greed(); time.sleep(0.5)
            etf = self.fetch_gold_etf_sentiment()

            # PROCESS
            h1_summary = ""
            for c in h1[:3]:
                emoji = "🟢" if float(c['close']) > float(c['open']) else "🔴"
                chg = ((float(c['close'])-float(c['open']))/float(c['open']))*100
                h1_summary += f"  {emoji} O:{c['open']} H:{c['high']} L:{c['low']} C:{c['close']} ({chg:+.2f}%)\n"

            # BUILD DATA PACKAGE
            d = {
                "price": price,
                "m15_o": m15[0]['open'] if m15 else "N/A",
                "m15_h": m15[0]['high'] if m15 else "N/A",
                "m15_l": m15[0]['low'] if m15 else "N/A",
                "m15_c": m15[0]['close'] if m15 else "N/A",
                "m15_pattern": m15_pat,
                "h1_summary": h1_summary,
                "h1_pattern": h1_pat,
                "h4_close": float(h4[0]['close']) if h4 else price,
                "h4_chg": ((float(h4[0]['close'])-float(h4[1]['close']))/float(h4[1]['close'])*100) if h4 and len(h4)>1 else 0,
                "h4_pattern": h4_pat,
                "d1_close": float(d1[0]['close']) if d1 else price,
                "d1_chg": ((float(d1[0]['close'])-float(d1[1]['close']))/float(d1[1]['close'])*100) if d1 and len(d1)>1 else 0,
                "ema20":  float(ema20[0]['ema'])  if ema20  else price,
                "ema50":  float(ema50[0]['ema'])  if ema50  else price,
                "ema200": float(ema200[0]['ema']) if ema200 else price,
                "rsi":    round(float(rsi[0]['rsi']), 1) if rsi else 50.0,
                "macd":     round(float(macd[0]['macd']),3)        if macd else 0,
                "macd_sig": round(float(macd[0]['macd_signal']),3) if macd else 0,
                "macd_hist":round(float(macd[0]['macd_hist']),3)   if macd else 0,
                "bb": bb or {}, "atr": atr or {}, "fib": fib or {}, "sr": sr or {},
                "dxy": dxy, "news": news, "news_sentiment": news_sentiment,
                "events": events, "fear_greed": fg, "etf": etf
            }

            # MASTER AI ANALYSIS
            analysis = self.analyze_master(d)
            if not analysis: return

            action     = analysis.get("action", "WAIT")
            confidence = analysis.get("confidence", 0)
            entry      = analysis.get("entry", price)
            sl         = analysis.get("sl", 0)
            tp         = analysis.get("tp", 0)
            rr         = analysis.get("rr", "1:2")
            trend      = analysis.get("trend", "NEUTRAL")
            reason     = analysis.get("reason", "")
            dxy_align  = analysis.get("dxy_aligned", False)
            news_sent  = analysis.get("news_sentiment", "NEUTRAL")
            ev_risk    = analysis.get("event_risk", "LOW")
            key_level  = analysis.get("key_level", "")

            now_wib = datetime.now(self.wib)

            if action == "WAIT":
                msg = f"""
<b>⏸️ XAUUSD ULTIMATE - WAIT</b>

Price: <b>${price:,.2f}</b>
Trend: {trend} | RSI: {d['rsi']}

💵 DXY: {dxy.get('current','N/A')} ({dxy.get('chg1h',0):+.3f}%) → {dxy.get('impact','N/A')}
📰 News: {news_sentiment}
📅 Event Risk: {ev_risk}
🌡️ Fear&Greed: {fg.get('value',50)} ({fg.get('label','N/A')})

Reason: {reason}

<i>⏰ {now_wib.strftime('%Y-%m-%d %H:%M WIB')}</i>"""
                self.send_telegram(msg)
            else:
                emoji = "🟢" if action == "BUY" else "🔴"
                sl_pts = abs(entry - sl)
                tp_pts = abs(tp - entry)
                ev_warn = "\n⚡ <b>HIGH IMPACT EVENT SOON! Be careful!</b>" if ev_risk == "HIGH" else ""

                news_lines = ""
                for n in news[:3]:
                    if n['title'] and "No news" not in n['title']:
                        news_lines += f"\n  • {n['title'][:65]}..."

                events_lines = ""
                for e in events[:2]:
                    if e.get("impact") in ["HIGH","MEDIUM"]:
                        events_lines += f"\n  ⚡ [{e['impact']}] {e['name']}"

                msg = f"""
<b>{emoji} XAUUSD ULTIMATE SIGNAL - {action}</b>

💰 Entry:  <b>${entry:,.2f}</b>
🛑 SL:     <b>${sl:,.2f}</b>  (-${sl_pts:.2f})
✅ TP:     <b>${tp:,.2f}</b>  (+${tp_pts:.2f})
📊 RR:     <b>{rr}</b>
🎯 Confidence: <b>{confidence}%</b>

━━━━━━━━━━━━━━━━━━━━
📊 TECHNICAL
━━━━━━━━━━━━━━━━━━━━
Trend: {trend} | Pattern: {d['h1_pattern']}
M15: {m15_pat}
RSI: {d['rsi']} | MACD: {d['macd']:+.3f}
BB: {bb.get('position','N/A') if bb else 'N/A'}
ATR: {atr.get('value',0) if atr else 0} ({atr.get('volatility','N/A') if atr else 'N/A'})
Key Level: {key_level}
EMA20: ${d['ema20']:,.2f} | EMA200: ${d['ema200']:,.2f}
Support: ${sr.get('support',0):,.2f} | Resistance: ${sr.get('resistance',0):,.2f}

━━━━━━━━━━━━━━━━━━━━
💵 DXY & MACRO
━━━━━━━━━━━━━━━━━━━━
DXY: {dxy.get('current','N/A')} ({dxy.get('chg1h',0):+.3f}%)
Trend: {dxy.get('trend','N/A')}
Aligned: {'✅ YES' if dxy_align else '⚠️ NO'}

━━━━━━━━━━━━━━━━━━━━
📰 FUNDAMENTAL
━━━━━━━━━━━━━━━━━━━━
News: {news_sent}{news_lines}

━━━━━━━━━━━━━━━━━━━━
🌡️ SENTIMENT
━━━━━━━━━━━━━━━━━━━━
Fear&Greed: {fg.get('value',50)} ({fg.get('label','N/A')})
Gold ETF: {etf.get('change',0):+.2f}% | {etf.get('flow','N/A')}

━━━━━━━━━━━━━━━━━━━━
📅 EVENT RISK: {ev_risk}{ev_warn}{events_lines}

📝 <b>Master Analysis:</b>
{reason}

<i>⏰ {now_wib.strftime('%Y-%m-%d %H:%M WIB')}</i>
<i>⚠️ DYOR - Not financial advice</i>"""
                self.send_telegram(msg)
                logger.info(f"✅ Signal: {action} @ ${entry:,.2f} | Conf: {confidence}%")

        except Exception as e:
            logger.error(f"Run error: {e}")
            self.send_telegram(f"❌ Ultimate Bot Error: {str(e)[:150]}")

        logger.info("=" * 65)

    def start(self):
        schedule.every(15).minutes.do(self.run)
        now = datetime.now(self.wib)
        logger.info("\n" + "=" * 65)
        logger.info("🥇 XAUUSD ULTIMATE SIGNAL BOT v3")
        logger.info("=" * 65)
        logger.info("✅ Multi-Timeframe: M15 + H1 + H4 + D1")
        logger.info("✅ Indicators: EMA/RSI/MACD/BB/ATR/Fibonacci")
        logger.info("✅ DXY Monitoring")
        logger.info("✅ News Realtime")
        logger.info("✅ Economic Calendar")
        logger.info("✅ Fear & Greed + Gold ETF Sentiment")
        logger.info("✅ Master AI Prompt (Gemini)")
        logger.info(f"⏰ {now.strftime('%Y-%m-%d %H:%M:%S WIB')}")
        logger.info("=" * 65)

        self.send_telegram(f"""
<b>🥇 XAUUSD ULTIMATE SIGNAL BOT v3</b>

✅ M15 + H1 + H4 + D1 Analysis
✅ EMA / RSI / MACD / BB / ATR
✅ Fibonacci Key Levels
✅ DXY Monitoring
✅ News Realtime
✅ Economic Calendar
✅ Fear & Greed Index
✅ Gold ETF Flows
✅ Master AI (Gemini)

Interval: Every 15 minutes
<i>Live: {now.strftime('%Y-%m-%d %H:%M WIB')}</i>""")

        self.run()
        while True:
            try:
                schedule.run_pending()
                time.sleep(60)
            except KeyboardInterrupt:
                logger.info("🛑 Stopped")
                break
            except Exception as e:
                logger.error(f"Loop error: {e}")
                time.sleep(60)

def main():
    TWELVE_KEY     = "9a0122845399415ab64545e3fee3fa5b"
    GROQ_KEY       = "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"
    TELEGRAM_TOKEN = "8681007582:AAGybLJ9vxn3C8UVyWJEcHD-qVGRq38VUgk"
    CHAT_ID        = "5280470660"
    bot = XAUUSDUltimateBot(TWELVE_KEY, GROQ_KEY, TELEGRAM_TOKEN, CHAT_ID)
    bot.start()

if __name__ == "__main__":
    main()
