#!/usr/bin/env python3
"""
XAUUSD PRO SIGNAL BOT v2
UPGRADE STEP 1:
+ News Realtime (CryptoPanic + NewsAPI)
+ DXY Monitoring (US Dollar Index)
+ Economic Calendar (major events)
+ Smarter AI prompt with full context
"""

import requests
import json
import time
from datetime import datetime, timedelta
import schedule
import logging
import pytz

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class XAUUSDSignalBotV2:
    def __init__(self, twelve_key, gemini_key, telegram_token, chat_id):
        self.twelve_key = twelve_key
        self.gemini_key = gemini_key
        self.telegram_token = telegram_token
        self.chat_id = chat_id
        self.gemini_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={gemini_key}"
        self.twelve_url = "https://api.twelvedata.com"
        self.wib = pytz.timezone('Asia/Jakarta')
        self.last_signal = None

    # ═══════════════════════════════════════════
    # SECTION 1: MARKET DATA
    # ═══════════════════════════════════════════

    def fetch_ohlcv(self, interval="1h", outputsize=50):
        """Fetch OHLCV candlestick data"""
        try:
            url = f"{self.twelve_url}/time_series"
            params = {
                "symbol": "XAU/USD",
                "interval": interval,
                "outputsize": outputsize,
                "apikey": self.twelve_key
            }
            response = requests.get(url, params=params, timeout=15)
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "ok":
                    candles = data.get("values", [])
                    logger.info(f"✅ Fetched {len(candles)} candles ({interval})")
                    return candles
            return None
        except Exception as e:
            logger.error(f"OHLCV error: {e}")
            return None

    def fetch_indicator(self, indicator, interval="1h", **kwargs):
        """Fetch technical indicator from Twelve Data"""
        try:
            url = f"{self.twelve_url}/{indicator}"
            params = {
                "symbol": "XAU/USD",
                "interval": interval,
                "apikey": self.twelve_key,
                **kwargs
            }
            response = requests.get(url, params=params, timeout=15)
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "ok":
                    return data.get("values", [])
            return None
        except Exception as e:
            logger.error(f"{indicator} error: {e}")
            return None

    # ═══════════════════════════════════════════
    # SECTION 2: DXY MONITORING (NEW!)
    # ═══════════════════════════════════════════

    def fetch_dxy(self):
        """Fetch US Dollar Index (DXY) - inverse of Gold"""
        try:
            logger.info("📊 Fetching DXY...")
            url = f"{self.twelve_url}/time_series"
            params = {
                "symbol": "DXY",
                "interval": "1h",
                "outputsize": 5,
                "apikey": self.twelve_key
            }
            response = requests.get(url, params=params, timeout=15)
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "ok":
                    candles = data.get("values", [])
                    if candles:
                        current = float(candles[0]['close'])
                        prev = float(candles[1]['close']) if len(candles) > 1 else current
                        change = ((current - prev) / prev) * 100
                        prev_4h = float(candles[4]['close']) if len(candles) > 4 else current
                        change_4h = ((current - prev_4h) / prev_4h) * 100

                        logger.info(f"✅ DXY: {current:.2f} ({change:+.3f}%)")
                        return {
                            "current": current,
                            "change_1h": change,
                            "change_4h": change_4h,
                            "trend": "STRENGTHENING" if change > 0.1 else "WEAKENING" if change < -0.1 else "STABLE",
                            "impact_gold": "BEARISH" if change > 0.1 else "BULLISH" if change < -0.1 else "NEUTRAL"
                        }
            return None
        except Exception as e:
            logger.error(f"DXY error: {e}")
            return None

    # ═══════════════════════════════════════════
    # SECTION 3: NEWS REALTIME (NEW!)
    # ═══════════════════════════════════════════

    def fetch_gold_news(self):
        """Fetch latest gold/forex news"""
        try:
            logger.info("📰 Fetching gold news...")
            news_list = []

            # Source 1: GNews API (free)
            try:
                url = "https://gnews.io/api/v4/search"
                params = {
                    "q": "gold price XAU USD Federal Reserve",
                    "lang": "en",
                    "max": 5,
                    "token": "free"  # Will try without token first
                }
                response = requests.get(url, params=params, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    articles = data.get("articles", [])
                    for a in articles[:3]:
                        news_list.append({
                            "title": a.get("title", ""),
                            "source": a.get("source", {}).get("name", ""),
                            "time": a.get("publishedAt", "")
                        })
            except:
                pass

            # Source 2: RSS Feed (free, no auth)
            try:
                import xml.etree.ElementTree as ET
                rss_urls = [
                    "https://feeds.finance.yahoo.com/rss/2.0/headline?s=GC=F&region=US&lang=en-US",
                    "https://www.investing.com/rss/news_14.rss"
                ]
                for rss_url in rss_urls:
                    try:
                        response = requests.get(rss_url, timeout=8,
                            headers={"User-Agent": "Mozilla/5.0"})
                        if response.status_code == 200:
                            root = ET.fromstring(response.content)
                            items = root.findall('.//item')[:3]
                            for item in items:
                                title = item.find('title')
                                pubdate = item.find('pubDate')
                                if title is not None:
                                    news_list.append({
                                        "title": title.text or "",
                                        "source": "Yahoo Finance",
                                        "time": pubdate.text if pubdate is not None else ""
                                    })
                            if news_list:
                                break
                    except:
                        continue
            except:
                pass

            # Source 3: Fallback - Twelve Data news
            try:
                url = f"{self.twelve_url}/news"
                params = {
                    "symbol": "XAU/USD",
                    "outputsize": 5,
                    "apikey": self.twelve_key
                }
                response = requests.get(url, params=params, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    if isinstance(data, list):
                        for item in data[:5]:
                            news_list.append({
                                "title": item.get("title", ""),
                                "source": item.get("source", ""),
                                "time": item.get("datetime", "")
                            })
            except:
                pass

            if news_list:
                logger.info(f"✅ Fetched {len(news_list)} news items")
            else:
                logger.warning("⚠️ No news fetched, using default")
                news_list = [{"title": "No recent news available", "source": "", "time": ""}]

            return news_list[:5]

        except Exception as e:
            logger.error(f"News error: {e}")
            return [{"title": "News fetch failed", "source": "", "time": ""}]

    # ═══════════════════════════════════════════
    # SECTION 4: ECONOMIC CALENDAR (NEW!)
    # ═══════════════════════════════════════════

    def fetch_economic_calendar(self):
        """Fetch upcoming economic events that affect gold"""
        try:
            logger.info("📅 Checking economic calendar...")
            events = []
            now = datetime.now(self.wib)

            # Try Twelve Data economic calendar
            try:
                url = f"{self.twelve_url}/economic_calendar"
                params = {
                    "start_date": now.strftime("%Y-%m-%d"),
                    "end_date": (now + timedelta(days=2)).strftime("%Y-%m-%d"),
                    "apikey": self.twelve_key
                }
                response = requests.get(url, params=params, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    if isinstance(data, dict) and "result" in data:
                        for event in data["result"][:10]:
                            impact = event.get("impact", "").upper()
                            country = event.get("country", "")
                            name = event.get("event", "")

                            # Filter high impact USD events
                            if country == "US" and impact in ["HIGH", "MEDIUM"]:
                                events.append({
                                    "name": name,
                                    "impact": impact,
                                    "time": event.get("time", ""),
                                    "country": country,
                                    "previous": event.get("previous", ""),
                                    "forecast": event.get("forecast", "")
                                })
            except Exception as e:
                logger.warning(f"Economic calendar API error: {e}")

            # Manual key events if API fails
            if not events:
                # Default important events to watch
                events = [
                    {
                        "name": "Check manually: FOMC, NFP, CPI upcoming",
                        "impact": "HIGH",
                        "time": "See investing.com/economic-calendar",
                        "country": "US",
                        "previous": "-",
                        "forecast": "-"
                    }
                ]

            logger.info(f"✅ Found {len(events)} economic events")
            return events

        except Exception as e:
            logger.error(f"Economic calendar error: {e}")
            return []

    def check_high_impact_event(self, events):
        """Check if high impact event is coming soon (within 2 hours)"""
        now = datetime.now(self.wib)
        for event in events:
            if event.get("impact") == "HIGH":
                return True, event.get("name", "Unknown")
        return False, None

    # ═══════════════════════════════════════════
    # SECTION 5: TECHNICAL ANALYSIS
    # ═══════════════════════════════════════════

    def calculate_support_resistance(self, candles):
        """Calculate support/resistance levels"""
        try:
            highs = [float(c['high']) for c in candles[:20]]
            lows = [float(c['low']) for c in candles[:20]]

            resistance = max(highs)
            support = min(lows)
            mid = (resistance + support) / 2

            recent_highs = sorted(highs[:5], reverse=True)
            recent_lows = sorted(lows[:5])

            return {
                "resistance": resistance,
                "support": support,
                "mid": mid,
                "key_resistance": recent_highs[0],
                "key_support": recent_lows[0]
            }
        except:
            return None

    def detect_pattern(self, candles):
        """Detect candlestick patterns"""
        try:
            if len(candles) < 3:
                return "Unknown"

            c1 = candles[0]
            open1, close1 = float(c1['open']), float(c1['close'])
            high1, low1 = float(c1['high']), float(c1['low'])
            c2 = candles[1]
            open2, close2 = float(c2['open']), float(c2['close'])

            body1 = abs(close1 - open1)
            range1 = high1 - low1
            lower_shadow = min(open1, close1) - low1
            upper_shadow = high1 - max(open1, close1)

            if range1 == 0:
                return "Flat Candle"
            if body1 < range1 * 0.1:
                return "Doji (Indecision ⚠️)"
            if lower_shadow > body1 * 2 and upper_shadow < body1 * 0.5:
                return "Hammer (Bullish Reversal 🟢)"
            if upper_shadow > body1 * 2 and lower_shadow < body1 * 0.5:
                return "Shooting Star (Bearish Reversal 🔴)"
            if close2 < open2 and close1 > open1 and close1 > open2 and open1 < close2:
                return "Bullish Engulfing (Strong BUY 🟢)"
            if close2 > open2 and close1 < open1 and close1 < open2 and open1 > close2:
                return "Bearish Engulfing (Strong SELL 🔴)"
            if close1 > open1 and body1 > range1 * 0.7:
                return "Strong Bullish Candle 🟢"
            if close1 < open1 and body1 > range1 * 0.7:
                return "Strong Bearish Candle 🔴"

            return "Normal Candle"
        except:
            return "Unknown"

    # ═══════════════════════════════════════════
    # SECTION 6: AI ANALYSIS (UPGRADED!)
    # ═══════════════════════════════════════════

    def analyze_with_gemini(self, market_data):
        """Send FULL context to Gemini AI"""
        try:
            logger.info("🤖 Gemini AI analyzing with full context...")

            # Format news
            news_text = ""
            for i, n in enumerate(market_data.get('news', []), 1):
                news_text += f"  {i}. {n['title']} [{n['source']}]\n"

            # Format economic events
            events_text = ""
            for e in market_data.get('events', []):
                events_text += f"  ⚠️ {e['impact']} IMPACT: {e['name']} ({e['country']}) - {e['time']}\n"

            # DXY data
            dxy = market_data.get('dxy', {})
            dxy_text = f"""
DXY Current: {dxy.get('current', 'N/A')}
DXY 1H Change: {dxy.get('change_1h', 0):+.3f}%
DXY 4H Change: {dxy.get('change_4h', 0):+.3f}%
DXY Trend: {dxy.get('trend', 'N/A')}
DXY Impact on Gold: {dxy.get('impact_gold', 'N/A')}
""" if dxy else "DXY: Unavailable"

            prompt = f"""You are a MASTER XAUUSD trader with 20+ years experience.
You have access to COMPLETE market context including:
- Real-time chart data
- Latest news
- Economic calendar
- DXY (US Dollar) movement

Analyze ALL data and provide the BEST trading signal.

═══════════════════════════════════════════════
XAUUSD COMPLETE MARKET ANALYSIS
═══════════════════════════════════════════════

💰 CURRENT PRICE: ${market_data['current_price']:,.2f}

━━━━━━━━━━━━━━━━━━━━━━━━━
📊 TECHNICAL ANALYSIS
━━━━━━━━━━━━━━━━━━━━━━━━━
H1 Candles (latest 5):
{market_data['h1_candles']}

H4 Close: ${market_data['h4_close']:,.2f} ({market_data['h4_change']:+.3f}%)

EMA 20: ${market_data['ema20']:,.2f}
EMA 50: ${market_data['ema50']:,.2f}
EMA 200: ${market_data['ema200']:,.2f}

RSI (14): {market_data['rsi']} {'⚠️ OVERBOUGHT' if market_data['rsi'] > 70 else '⚠️ OVERSOLD' if market_data['rsi'] < 30 else '✅ NORMAL'}
MACD: {market_data['macd']:+.3f} | Signal: {market_data['macd_signal']:+.3f} | Hist: {market_data['macd_hist']:+.3f}

24H High: ${market_data['high_24h']:,.2f}
24H Low: ${market_data['low_24h']:,.2f}
24H Change: {market_data['change_24h']:+.3f}%

Resistance: ${market_data['resistance']:,.2f}
Support: ${market_data['support']:,.2f}
Mid Level: ${market_data['mid']:,.2f}

Candlestick Pattern: {market_data['pattern']}

Price vs EMA20: {'ABOVE ✅' if market_data['current_price'] > market_data['ema20'] else 'BELOW ❌'}
Price vs EMA50: {'ABOVE ✅' if market_data['current_price'] > market_data['ema50'] else 'BELOW ❌'}
Price vs EMA200: {'ABOVE ✅' if market_data['current_price'] > market_data['ema200'] else 'BELOW ❌'}

━━━━━━━━━━━━━━━━━━━━━━━━━
💵 DXY (US DOLLAR INDEX)
━━━━━━━━━━━━━━━━━━━━━━━━━
{dxy_text}

Note: DXY UP = Gold DOWN | DXY DOWN = Gold UP

━━━━━━━━━━━━━━━━━━━━━━━━━
📰 LATEST GOLD NEWS
━━━━━━━━━━━━━━━━━━━━━━━━━
{news_text if news_text else "No recent news available"}

━━━━━━━━━━━━━━━━━━━━━━━━━
📅 ECONOMIC CALENDAR (Next 48h)
━━━━━━━━━━━━━━━━━━━━━━━━━
{events_text if events_text else "No major events in next 48h"}

HIGH IMPACT = AVOID trading 30min before/after event!

═══════════════════════════════════════════════

Based on ALL this data, provide trading decision:

RULES:
1. Technical + DXY + News must ALIGN for strong signal
2. If HIGH IMPACT news coming soon → WAIT (avoid risk)
3. If DXY and technicals CONFLICT → WAIT
4. Confidence must be > 70% to give BUY/SELL
5. Minimum Risk/Reward = 1:2
6. Consider support/resistance for SL/TP placement

Respond ONLY in JSON:
{{"action": "BUY/SELL/WAIT", "confidence": 0-100, "entry": price, "sl": price, "tp": price, "rr": "1:X", "trend": "BULLISH/BEARISH/NEUTRAL", "dxy_impact": "SUPPORTS/CONFLICTS/NEUTRAL", "news_sentiment": "BULLISH/BEARISH/NEUTRAL", "event_risk": "HIGH/LOW", "reason": "max 40 words combining technical + DXY + news"}}"""

            payload = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {
                    "temperature": 0.2,
                    "maxOutputTokens": 400
                }
            }

            response = requests.post(self.gemini_url, json=payload, timeout=30)

            if response.status_code == 200:
                result = response.json()
                content = result['candidates'][0]['content']['parts'][0]['text']

                if "```" in content:
                    content = content.split("```")[1]
                    if content.startswith("json"):
                        content = content[4:]
                    content = content.split("```")[0]

                analysis = json.loads(content.strip())
                logger.info(f"✅ Signal: {analysis.get('action')} ({analysis.get('confidence')}%)")
                return analysis
            else:
                logger.error(f"Gemini error: {response.status_code}")
                return None

        except Exception as e:
            logger.error(f"Gemini error: {e}")
            return None

    # ═══════════════════════════════════════════
    # SECTION 7: TELEGRAM
    # ═══════════════════════════════════════════

    def send_telegram(self, message):
        try:
            url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
            payload = {
                "chat_id": self.chat_id,
                "text": message,
                "parse_mode": "HTML"
            }
            requests.post(url, json=payload, timeout=10)
        except Exception as e:
            logger.error(f"Telegram error: {e}")

    # ═══════════════════════════════════════════
    # SECTION 8: MAIN RUN
    # ═══════════════════════════════════════════

    def run(self):
        logger.info("=" * 60)
        logger.info(f"[{datetime.now(self.wib).strftime('%Y-%m-%d %H:%M:%S WIB')}] XAUUSD v2 ANALYSIS")
        logger.info("=" * 60)

        try:
            # FETCH ALL DATA
            logger.info("📥 Fetching all data...")

            # 1. OHLCV
            h1_candles = self.fetch_ohlcv("1h", 50)
            if not h1_candles:
                self.send_telegram("⚠️ Failed to fetch XAUUSD data")
                return
            time.sleep(0.5)

            h4_candles = self.fetch_ohlcv("4h", 10)
            time.sleep(0.5)

            # 2. INDICATORS
            ema20_data = self.fetch_indicator("ema", "1h", time_period=20)
            time.sleep(0.5)
            ema50_data = self.fetch_indicator("ema", "1h", time_period=50)
            time.sleep(0.5)
            ema200_data = self.fetch_indicator("ema", "1h", time_period=200)
            time.sleep(0.5)
            rsi_data = self.fetch_indicator("rsi", "1h", time_period=14)
            time.sleep(0.5)
            macd_data = self.fetch_indicator("macd", "1h",
                fast_period=12, slow_period=26, signal_period=9)
            time.sleep(0.5)

            # 3. DXY (NEW!)
            dxy = self.fetch_dxy()
            time.sleep(0.5)

            # 4. NEWS (NEW!)
            news = self.fetch_gold_news()
            time.sleep(0.5)

            # 5. ECONOMIC CALENDAR (NEW!)
            events = self.fetch_economic_calendar()

            # PROCESS DATA
            current_price = float(h1_candles[0]['close'])

            h1_summary = ""
            for c in h1_candles[:5]:
                direction = "🟢" if float(c['close']) > float(c['open']) else "🔴"
                change = ((float(c['close']) - float(c['open'])) / float(c['open'])) * 100
                h1_summary += f"  {direction} O:{c['open']} H:{c['high']} L:{c['low']} C:{c['close']} ({change:+.2f}%)\n"

            h4_close = float(h4_candles[0]['close']) if h4_candles else current_price
            h4_prev = float(h4_candles[1]['close']) if h4_candles and len(h4_candles) > 1 else h4_close
            h4_change = ((h4_close - h4_prev) / h4_prev) * 100

            ema20 = float(ema20_data[0]['ema']) if ema20_data else current_price
            ema50 = float(ema50_data[0]['ema']) if ema50_data else current_price
            ema200 = float(ema200_data[0]['ema']) if ema200_data else current_price
            rsi = float(rsi_data[0]['rsi']) if rsi_data else 50.0
            macd_val = float(macd_data[0]['macd']) if macd_data else 0
            macd_signal = float(macd_data[0]['macd_signal']) if macd_data else 0
            macd_hist = float(macd_data[0]['macd_hist']) if macd_data else 0

            closes_24h = [float(c['close']) for c in h1_candles[:24]]
            highs_24h = [float(c['high']) for c in h1_candles[:24]]
            lows_24h = [float(c['low']) for c in h1_candles[:24]]
            high_24h = max(highs_24h)
            low_24h = min(lows_24h)
            change_24h = ((current_price - closes_24h[-1]) / closes_24h[-1]) * 100

            sr = self.calculate_support_resistance(h1_candles)
            pattern = self.detect_pattern(h1_candles)

            market_data = {
                "current_price": current_price,
                "h1_candles": h1_summary,
                "h4_close": h4_close,
                "h4_change": h4_change,
                "ema20": ema20,
                "ema50": ema50,
                "ema200": ema200,
                "rsi": round(rsi, 1),
                "macd": round(macd_val, 3),
                "macd_signal": round(macd_signal, 3),
                "macd_hist": round(macd_hist, 3),
                "high_24h": high_24h,
                "low_24h": low_24h,
                "change_24h": change_24h,
                "resistance": sr['resistance'] if sr else high_24h,
                "support": sr['support'] if sr else low_24h,
                "mid": sr['mid'] if sr else (high_24h + low_24h) / 2,
                "pattern": pattern,
                "dxy": dxy,
                "news": news,
                "events": events
            }

            # AI ANALYSIS
            analysis = self.analyze_with_gemini(market_data)
            if not analysis:
                return

            action = analysis.get("action", "WAIT")
            confidence = analysis.get("confidence", 0)
            entry = analysis.get("entry", current_price)
            sl = analysis.get("sl", 0)
            tp = analysis.get("tp", 0)
            rr = analysis.get("rr", "1:2")
            trend = analysis.get("trend", "NEUTRAL")
            reason = analysis.get("reason", "")
            dxy_impact = analysis.get("dxy_impact", "NEUTRAL")
            news_sentiment = analysis.get("news_sentiment", "NEUTRAL")
            event_risk = analysis.get("event_risk", "LOW")

            now_wib = datetime.now(self.wib)

            # SEND SIGNAL
            if action == "WAIT":
                msg = f"""
<b>⏸️ XAUUSD - WAIT / NO TRADE</b>

Price: <b>${current_price:,.2f}</b>
Trend: {trend}
RSI: {rsi} | Pattern: {pattern}

💵 DXY: {dxy.get('current', 'N/A')} ({dxy.get('change_1h', 0):+.3f}%)
DXY Impact: {dxy_impact}
News Sentiment: {news_sentiment}
Event Risk: {event_risk}

Reason: {reason}

<i>⏰ {now_wib.strftime('%Y-%m-%d %H:%M WIB')}</i>
"""
                self.send_telegram(msg)
                logger.info("⏸️ WAIT signal sent")

            else:
                emoji = "🟢" if action == "BUY" else "🔴"
                action_text = "BUY (LONG)" if action == "BUY" else "SELL (SHORT)"
                sl_pips = abs(entry - sl)
                tp_pips = abs(tp - entry)

                # News summary (top 3)
                news_text = ""
                for n in news[:3]:
                    if n['title'] and n['title'] != "No recent news available":
                        news_text += f"\n  • {n['title'][:60]}..."

                # Events warning
                event_warning = ""
                if event_risk == "HIGH":
                    event_warning = "\n⚠️ <b>HIGH IMPACT EVENT COMING! Trade with caution!</b>"

                msg = f"""
<b>{emoji} XAUUSD SIGNAL - {action_text}</b>

💰 Entry: <b>${entry:,.2f}</b>
🛑 Stop Loss: <b>${sl:,.2f}</b> (-${sl_pips:.2f})
✅ Take Profit: <b>${tp:,.2f}</b> (+${tp_pips:.2f})
📊 Risk/Reward: <b>{rr}</b>
🎯 Confidence: <b>{confidence}%</b>

━━━━━━━━━━━━━━━━━━━
📈 TECHNICAL
━━━━━━━━━━━━━━━━━━━
Trend: {trend}
Pattern: {pattern}
RSI: {rsi} | MACD: {macd_val:+.3f}
EMA20: ${ema20:,.2f} | EMA50: ${ema50:,.2f}
Support: ${sr['support']:,.2f} | Resistance: ${sr['resistance']:,.2f}

━━━━━━━━━━━━━━━━━━━
💵 DXY (US DOLLAR)
━━━━━━━━━━━━━━━━━━━
DXY: {dxy.get('current', 'N/A')} ({dxy.get('change_1h', 0):+.3f}%)
DXY Trend: {dxy.get('trend', 'N/A')}
Impact on Gold: {dxy_impact}

━━━━━━━━━━━━━━━━━━━
📰 NEWS SENTIMENT
━━━━━━━━━━━━━━━━━━━
Sentiment: {news_sentiment}{news_text}

━━━━━━━━━━━━━━━━━━━
📅 EVENT RISK: {event_risk}
━━━━━━━━━━━━━━━━━━━{event_warning}

📝 <b>Analysis:</b> {reason}

<i>⏰ {now_wib.strftime('%Y-%m-%d %H:%M WIB')}</i>
<i>⚠️ DYOR - Not financial advice</i>
"""
                self.send_telegram(msg)
                logger.info(f"✅ Signal sent: {action} @ ${entry:,.2f}")

        except Exception as e:
            logger.error(f"Run error: {e}")
            self.send_telegram(f"❌ XAUUSD v2 Error: {str(e)[:100]}")

        logger.info("=" * 60)

    def start(self):
        schedule.every(15).minutes.do(self.run)

        now_wib = datetime.now(self.wib)
        logger.info("\n" + "=" * 60)
        logger.info("🥇 XAUUSD PRO SIGNAL BOT v2")
        logger.info("=" * 60)
        logger.info("📊 Data: Twelve Data (Realtime OHLCV)")
        logger.info("💵 NEW: DXY Monitoring")
        logger.info("📰 NEW: Gold News Realtime")
        logger.info("📅 NEW: Economic Calendar")
        logger.info("🤖 AI: Google Gemini 1.5 Flash")
        logger.info("⏱️  Interval: Every 15 minutes")
        logger.info(f"⏰ Time: {now_wib.strftime('%Y-%m-%d %H:%M:%S WIB')}")
        logger.info("=" * 60 + "\n")

        self.send_telegram(f"""
<b>🥇 XAUUSD PRO SIGNAL BOT v2 STARTED!</b>

✅ Realtime OHLCV Data
✅ EMA 20/50/200 + RSI + MACD
✅ Candlestick Pattern Detection
🆕 DXY (US Dollar) Monitoring
🆕 Gold News Realtime
🆕 Economic Calendar
🤖 Google Gemini AI Analysis

Interval: Every 15 minutes
<i>Bot aktif: {now_wib.strftime('%Y-%m-%d %H:%M WIB')}</i>
""")

        self.run()

        while True:
            try:
                schedule.run_pending()
                time.sleep(60)
            except KeyboardInterrupt:
                logger.info("\n🛑 Bot stopped")
                break
            except Exception as e:
                logger.error(f"Error: {e}")
                time.sleep(60)

def main():
    TWELVE_KEY     = "9a0122845399415ab64545e3fee3fa5b"
    GEMINI_KEY     = "AQ.Ab8RN6J5vczy5DoI9SZ_Nm8nZvBgTlu8q3f1XYxT4H1DcNVdwQ"
    TELEGRAM_TOKEN = "8681007582:AAGybLJ9vxn3C8UVyWJEcHD-qVGRq38VUgk"
    CHAT_ID        = "5280470660"

    bot = XAUUSDSignalBotV2(TWELVE_KEY, GEMINI_KEY, TELEGRAM_TOKEN, CHAT_ID)
    bot.start()

if __name__ == "__main__":
    main()
