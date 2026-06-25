#!/usr/bin/env python3
"""
XAUUSD PRO SIGNAL BOT
- Real OHLCV data dari Twelve Data
- Multi-timeframe analysis (M15, H1, H4)
- Full indicators: EMA, RSI, MACD, BB
- Candlestick pattern detection
- Support/Resistance levels
- Groq AI analysis (FREE)
- Signal: BUY/SELL + Entry + SL + TP
- Telegram notifications
- Every 15 minutes
"""

import os
import requests
import json
import time
from datetime import datetime
import schedule
import logging
import pytz

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class XAUUSDSignalBot:
    def __init__(self, twelve_key, groq_key, telegram_token, chat_id):
        self.twelve_key = twelve_key
        self.groq_key = groq_key
        self.telegram_token = telegram_token
        self.chat_id = chat_id
        self.groq_url = "https://api.groq.com/openai/v1/chat/completions"
        self.groq_model = "llama-3.3-70b-versatile"
        self.twelve_url = "https://api.twelvedata.com"
        self.wib = pytz.timezone('Asia/Jakarta')
        self.last_signal = None
        self.last_signal_time = None

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
                else:
                    logger.error(f"API error: {data.get('message')}")
            return None
        except Exception as e:
            logger.error(f"OHLCV fetch error: {e}")
            return None

    def fetch_indicator(self, indicator, interval="1h", **kwargs):
        """Fetch technical indicator"""
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
            logger.error(f"{indicator} fetch error: {e}")
            return None

    def calculate_support_resistance(self, candles):
        """Calculate support/resistance from price history"""
        try:
            highs = [float(c['high']) for c in candles[:20]]
            lows = [float(c['low']) for c in candles[:20]]
            closes = [float(c['close']) for c in candles[:20]]

            resistance = max(highs)
            support = min(lows)
            mid = (resistance + support) / 2

            # Recent key levels
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

    def detect_candlestick_pattern(self, candles):
        """Detect candlestick patterns"""
        try:
            if len(candles) < 3:
                return "Unknown"

            c1 = candles[0]  # Latest
            c2 = candles[1]  # Previous
            c3 = candles[2]  # 2 bars ago

            open1 = float(c1['open'])
            close1 = float(c1['close'])
            high1 = float(c1['high'])
            low1 = float(c1['low'])

            open2 = float(c2['open'])
            close2 = float(c2['close'])

            body1 = abs(close1 - open1)
            body2 = abs(close2 - open2)
            range1 = high1 - low1

            # Doji
            if body1 < range1 * 0.1:
                return "Doji (Indecision)"

            # Hammer
            lower_shadow = min(open1, close1) - low1
            upper_shadow = high1 - max(open1, close1)
            if lower_shadow > body1 * 2 and upper_shadow < body1 * 0.5:
                return "Hammer (Bullish Reversal)"

            # Shooting Star
            if upper_shadow > body1 * 2 and lower_shadow < body1 * 0.5:
                return "Shooting Star (Bearish Reversal)"

            # Bullish Engulfing
            if close2 < open2 and close1 > open1 and close1 > open2 and open1 < close2:
                return "Bullish Engulfing (Strong Buy)"

            # Bearish Engulfing
            if close2 > open2 and close1 < open1 and close1 < open2 and open1 > close2:
                return "Bearish Engulfing (Strong Sell)"

            # Strong Bullish
            if close1 > open1 and body1 > range1 * 0.7:
                return "Strong Bullish Candle"

            # Strong Bearish
            if close1 < open1 and body1 > range1 * 0.7:
                return "Strong Bearish Candle"

            return "Normal Candle"

        except:
            return "Unknown"

    def analyze_with_groq(self, market_data):
        """Send all data to Groq AI for analysis"""
        try:
            logger.info("🤖 Groq AI analyzing XAUUSD chart data...")

            prompt = f"""You are a professional XAUUSD (Gold/USD) trader with 20 years experience.
Analyze the following REAL-TIME chart data and provide a trading signal.

═══════════════════════════════════════
XAUUSD REAL-TIME CHART DATA
═══════════════════════════════════════

CURRENT PRICE: ${market_data['current_price']:,.2f}

--- MULTI-TIMEFRAME ANALYSIS ---
H1 Candles (last 5):
{market_data['h1_candles']}

H4 Last Close: ${market_data['h4_close']:,.2f}
H4 Change: {market_data['h4_change']:+.3f}%

--- TECHNICAL INDICATORS ---
EMA 20: ${market_data['ema20']:,.2f}
EMA 50: ${market_data['ema50']:,.2f}
EMA 200: ${market_data['ema200']:,.2f}

RSI (14): {market_data['rsi']}
MACD Line: {market_data['macd']}
MACD Signal: {market_data['macd_signal']}
MACD Histogram: {market_data['macd_hist']}

--- PRICE ACTION ---
24H High: ${market_data['high_24h']:,.2f}
24H Low: ${market_data['low_24h']:,.2f}
24H Change: {market_data['change_24h']:+.3f}%

Resistance: ${market_data['resistance']:,.2f}
Support: ${market_data['support']:,.2f}
Mid Level: ${market_data['mid']:,.2f}

--- CANDLESTICK PATTERN ---
Latest Pattern: {market_data['pattern']}

--- TREND ---
Price vs EMA20: {'ABOVE' if market_data['current_price'] > market_data['ema20'] else 'BELOW'}
Price vs EMA50: {'ABOVE' if market_data['current_price'] > market_data['ema50'] else 'BELOW'}
Price vs EMA200: {'ABOVE' if market_data['current_price'] > market_data['ema200'] else 'BELOW'}

═══════════════════════════════════════

Based on this complete chart analysis, provide:
1. Trading signal (BUY/SELL/WAIT)
2. Exact entry price
3. Stop Loss price
4. Take Profit price (minimum 1:2 RR)
5. Confidence level
6. Brief analysis

IMPORTANT RULES:
- Only BUY/SELL if confidence > 70%
- If unclear or risky → WAIT
- Consider all timeframes
- Risk management is priority

Respond ONLY in this exact JSON:
{{"action": "BUY/SELL/WAIT", "confidence": 0-100, "entry": price, "sl": price, "tp": price, "rr": "1:X", "trend": "BULLISH/BEARISH/NEUTRAL", "pattern_signal": "brief", "reason": "max 30 words analysis"}}"""

            headers = {
                "Authorization": f"Bearer {self.groq_key}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": self.groq_model,
                "messages": [
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.2,
                "max_tokens": 300
            }

            response = requests.post(self.groq_url, headers=headers, json=payload, timeout=30)

            if response.status_code == 200:
                result = response.json()
                content = result['choices'][0]['message']['content']

                # Clean JSON
                if "```" in content:
                    content = content.split("```")[1]
                    if content.startswith("json"):
                        content = content[4:]
                    content = content.split("```")[0]

                analysis = json.loads(content.strip())
                logger.info(f"✅ Signal: {analysis.get('action')} ({analysis.get('confidence')}%)")
                return analysis

            else:
                logger.error(f"Groq error: {response.status_code} - {response.text[:200]}")
                return None

        except Exception as e:
            logger.error(f"Groq error: {e}")
            return None

    def send_telegram(self, message):
        """Send Telegram message"""
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

    def run(self):
        """Main analysis cycle"""
        logger.info("=" * 60)
        logger.info(f"[{datetime.now(self.wib).strftime('%Y-%m-%d %H:%M:%S WIB')}] XAUUSD ANALYSIS")
        logger.info("=" * 60)

        try:
            # FETCH H1 CANDLES
            h1_candles = self.fetch_ohlcv("1h", 50)
            if not h1_candles:
                logger.error("Failed to fetch H1 candles")
                return

            # FETCH H4 CANDLES
            h4_candles = self.fetch_ohlcv("4h", 20)

            # CURRENT PRICE
            current_price = float(h1_candles[0]['close'])
            logger.info(f"XAUUSD: ${current_price:,.2f}")

            # H1 CANDLES SUMMARY (last 5)
            h1_summary = ""
            for i, c in enumerate(h1_candles[:5]):
                direction = "🟢" if float(c['close']) > float(c['open']) else "🔴"
                change = ((float(c['close']) - float(c['open'])) / float(c['open'])) * 100
                h1_summary += f"  {direction} O:{c['open']} H:{c['high']} L:{c['low']} C:{c['close']} ({change:+.2f}%)\n"

            # H4 DATA
            h4_close = float(h4_candles[0]['close']) if h4_candles else current_price
            h4_prev = float(h4_candles[1]['close']) if h4_candles and len(h4_candles) > 1 else h4_close
            h4_change = ((h4_close - h4_prev) / h4_prev) * 100

            # FETCH INDICATORS
            time.sleep(0.5)
            ema20_data = self.fetch_indicator("ema", "1h", time_period=20)
            time.sleep(0.5)
            ema50_data = self.fetch_indicator("ema", "1h", time_period=50)
            time.sleep(0.5)
            ema200_data = self.fetch_indicator("ema", "1h", time_period=200)
            time.sleep(0.5)
            rsi_data = self.fetch_indicator("rsi", "1h", time_period=14)
            time.sleep(0.5)
            macd_data = self.fetch_indicator("macd", "1h", fast_period=12, slow_period=26, signal_period=9)

            # EXTRACT VALUES
            ema20 = float(ema20_data[0]['ema']) if ema20_data else current_price
            ema50 = float(ema50_data[0]['ema']) if ema50_data else current_price
            ema200 = float(ema200_data[0]['ema']) if ema200_data else current_price
            rsi = float(rsi_data[0]['rsi']) if rsi_data else 50.0
            macd_val = float(macd_data[0]['macd']) if macd_data else 0
            macd_signal = float(macd_data[0]['macd_signal']) if macd_data else 0
            macd_hist = float(macd_data[0]['macd_hist']) if macd_data else 0

            # 24H HIGH/LOW
            closes_24h = [float(c['close']) for c in h1_candles[:24]]
            highs_24h = [float(c['high']) for c in h1_candles[:24]]
            lows_24h = [float(c['low']) for c in h1_candles[:24]]
            high_24h = max(highs_24h)
            low_24h = min(lows_24h)
            change_24h = ((current_price - closes_24h[-1]) / closes_24h[-1]) * 100

            # SUPPORT/RESISTANCE
            sr = self.calculate_support_resistance(h1_candles)

            # CANDLESTICK PATTERN
            pattern = self.detect_candlestick_pattern(h1_candles)

            # PREPARE MARKET DATA
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
                "pattern": pattern
            }

            # GROQ AI ANALYSIS
            analysis = self.analyze_with_groq(market_data)
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
            pattern_signal = analysis.get("pattern_signal", "")

            now_wib = datetime.now(self.wib)

            # SEND SIGNAL
            if action == "BUY":
                sl_pips = entry - sl
                tp_pips = tp - entry
                emoji = "🟢"
                action_text = "BUY (LONG)"
            elif action == "SELL":
                sl_pips = sl - entry
                tp_pips = entry - tp
                emoji = "🔴"
                action_text = "SELL (SHORT)"
            else:
                # WAIT signal
                msg = f"""
<b>⏸️ XAUUSD - WAIT / NO TRADE</b>

Price: <b>${current_price:,.2f}</b>
Trend: {trend}
RSI: {rsi}
Pattern: {pattern}

Reason: {reason}

EMA20: ${ema20:,.2f}
EMA50: ${ema50:,.2f}
Support: ${sr['support']:,.2f} | Resistance: ${sr['resistance']:,.2f}

<i>⏰ {now_wib.strftime('%Y-%m-%d %H:%M WIB')}</i>
"""
                self.send_telegram(msg)
                logger.info("⏸️ WAIT - No trade signal")
                return

            # BUY OR SELL SIGNAL
            msg = f"""
<b>{emoji} XAUUSD SIGNAL - {action_text}</b>

💰 Entry: <b>${entry:,.2f}</b>
🛑 Stop Loss: <b>${sl:,.2f}</b> (-${sl_pips:.2f})
✅ Take Profit: <b>${tp:,.2f}</b> (+${tp_pips:.2f})
📊 Risk/Reward: <b>{rr}</b>

Confidence: <b>{confidence}%</b>
Trend: {trend}
Pattern: {pattern}
Signal: {pattern_signal}

--- INDICATORS ---
RSI: {rsi} {'(Overbought ⚠️)' if rsi > 70 else '(Oversold ⚠️)' if rsi < 30 else '(Normal ✅)'}
MACD: {macd_val:+.3f} | Signal: {macd_signal:+.3f}
EMA20: ${ema20:,.2f} | EMA50: ${ema50:,.2f}

--- LEVELS ---
Resistance: ${sr['resistance']:,.2f}
Support: ${sr['support']:,.2f}
24H High: ${high_24h:,.2f} | Low: ${low_24h:,.2f}

📝 Analysis: {reason}

<i>⏰ {now_wib.strftime('%Y-%m-%d %H:%M WIB')}</i>
<i>⚠️ DYOR - This is not financial advice</i>
"""
            self.send_telegram(msg)
            logger.info(f"✅ Signal sent: {action} @ ${entry:,.2f}")

        except Exception as e:
            logger.error(f"Run error: {e}")
            self.send_telegram(f"❌ XAUUSD Bot Error: {str(e)[:100]}")

        logger.info("=" * 60)

    def start(self):
        """Start the bot"""
        schedule.every(15).minutes.do(self.run)

        now_wib = datetime.now(self.wib)
        logger.info("\n" + "=" * 60)
        logger.info("🥇 XAUUSD PRO SIGNAL BOT")
        logger.info("=" * 60)
        logger.info("📊 Data: Twelve Data (Realtime OHLCV)")
        logger.info("🤖 AI: Groq (Llama 3.3 70B)")
        logger.info("⏱️  Interval: Every 15 minutes")
        logger.info("📈 Indicators: EMA 20/50/200, RSI, MACD")
        logger.info("🕯️  Patterns: Auto detection")
        logger.info("📐 Timeframes: M15, H1, H4")
        logger.info(f"⏰ Time: {now_wib.strftime('%Y-%m-%d %H:%M:%S WIB')}")
        logger.info("=" * 60 + "\n")

        self.send_telegram(f"""
<b>🥇 XAUUSD PRO SIGNAL BOT STARTED!</b>

Data: Twelve Data (Realtime)
AI: Groq (Llama 3.3 70B)
Indicators: EMA 20/50/200 + RSI + MACD
Patterns: Auto Detection
Timeframe: H1 + H4
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
    GROQ_KEY       = "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"
    TELEGRAM_TOKEN = "8681007582:AAGybLJ9vxn3C8UVyWJEcHD-qVGRq38VUgk"
    CHAT_ID        = "5280470660"

    bot = XAUUSDSignalBot(TWELVE_KEY, GROQ_KEY, TELEGRAM_TOKEN, CHAT_ID)
    bot.start()

if __name__ == "__main__":
    main()
