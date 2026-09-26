import uuid
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
import httpx

logger = logging.getLogger("DocuMind.LiveAPIs")


class LiveAPIService:
    """
    Live API Tools for real-time external data:
    1. System Time & Date
    2. Weather Information (wttr.in)
    3. Cryptocurrency & Financial Prices (CoinGecko / Yahoo)
    4. Currency Exchange Rates (open.er-api.com)
    """

    def get_system_time(self, query: str = "") -> List[Dict[str, Any]]:
        """
        Returns accurate current system time, UTC time, date, and weekday.
        """
        now_local = datetime.now()
        now_utc = datetime.now(timezone.utc)
        
        date_str = now_local.strftime("%A, %B %d, %Y")
        time_local_str = now_local.strftime("%I:%M:%S %p")
        time_utc_str = now_utc.strftime("%H:%M:%S UTC")

        snippet = (
            f"Current Date: {date_str}. "
            f"Current Local Time: {time_local_str}. "
            f"Coordinated Universal Time (UTC): {time_utc_str}."
        )

        return [{
            "id": f"live-time-{uuid.uuid4().hex[:6]}",
            "source_type": "live_api",
            "title": "System Clock & Calendar",
            "url": None,
            "snippet": snippet,
            "retrieved_at": now_utc.isoformat(),
            "relevance": 99,
            "metadata": {
                "api": "System Clock",
                "category": "time"
            }
        }]

    async def get_weather(self, query: str) -> List[Dict[str, Any]]:
        """
        Fetches live weather from wttr.in.
        """
        import re
        # Extract city if query contains "in <city>" or "at <city>" or "for <city>"
        match = re.search(r'\b(?:in|at|for)\s+([A-Za-z\s]+?)(?:\?|$|\s+today|\s+now)', query, re.IGNORECASE)
        city = match.group(1).strip() if match else ""
        location = city if city else ""

        url = f"https://wttr.in/{location}?format=j1" if location else "https://wttr.in/?format=j1"
        now_iso = datetime.now(timezone.utc).isoformat()

        try:
            async with httpx.AsyncClient(timeout=4.0) as client:
                resp = await client.get(url, headers={"User-Agent": "curl/7.68.0"})
                if resp.status_code == 200:
                    data = resp.json()
                    curr = data.get("current_condition", [{}])[0]
                    area_info = data.get("nearest_area", [{}])[0]
                    area_name = area_info.get("areaName", [{}])[0].get("value", location or "Current Location")
                    country = area_info.get("country", [{}])[0].get("value", "")

                    temp_c = curr.get("temp_C", "N/A")
                    temp_f = curr.get("temp_F", "N/A")
                    desc = curr.get("weatherDesc", [{}])[0].get("value", "Clear")
                    humidity = curr.get("humidity", "N/A")
                    wind_km = curr.get("windspeedKmph", "N/A")

                    snippet = (
                        f"Weather for {area_name}{f', {country}' if country else ''}: "
                        f"{desc}, {temp_c}°C ({temp_f}°F). "
                        f"Humidity: {humidity}%, Wind: {wind_km} km/h. "
                        f"Reported at: {now_iso[:19]} UTC."
                    )

                    return [{
                        "id": f"live-weather-{uuid.uuid4().hex[:6]}",
                        "source_type": "live_api",
                        "title": f"Live Weather: {area_name}",
                        "url": f"https://wttr.in/{location}",
                        "snippet": snippet,
                        "retrieved_at": now_iso,
                        "relevance": 95,
                        "metadata": {
                            "api": "wttr.in",
                            "category": "weather"
                        }
                    }]
        except Exception as e:
            logger.warning(f"[LiveAPIs] Weather fetch error: {e}")

        # Fallback text format
        try:
            fallback_url = f"https://wttr.in/{location}?format=%l:+%C+%t+(feels+like+%f)+humidity:+%h+wind:+%w"
            async with httpx.AsyncClient(timeout=3.0) as client:
                resp = await client.get(fallback_url, headers={"User-Agent": "curl/7.68.0"})
                if resp.status_code == 200 and resp.text.strip():
                    return [{
                        "id": f"live-weather-{uuid.uuid4().hex[:6]}",
                        "source_type": "live_api",
                        "title": f"Live Weather Service",
                        "url": fallback_url,
                        "snippet": f"Weather report: {resp.text.strip()}",
                        "retrieved_at": now_iso,
                        "relevance": 90,
                        "metadata": {"api": "wttr.in", "category": "weather"}
                    }]
        except Exception:
            pass

        return []

    async def get_crypto_price(self, query: str) -> List[Dict[str, Any]]:
        """
        Fetches live crypto prices from CoinGecko.
        """
        q_lower = query.lower()
        coin_map = {
            "bitcoin": "bitcoin",
            "btc": "bitcoin",
            "ethereum": "ethereum",
            "eth": "ethereum",
            "solana": "solana",
            "sol": "solana",
            "dogecoin": "dogecoin",
            "doge": "dogecoin",
            "cardano": "cardano",
            "ada": "cardano",
            "ripple": "ripple",
            "xrp": "ripple"
        }

        detected_coins = set()
        for key, coin_id in coin_map.items():
            if key in q_lower:
                detected_coins.add(coin_id)

        if not detected_coins:
            detected_coins = {"bitcoin", "ethereum"}

        ids_param = ",".join(detected_coins)
        url = f"https://api.coingecko.com/api/v3/simple/price?ids={ids_param}&vs_currencies=usd,inr&include_24hr_change=true"
        now_iso = datetime.now(timezone.utc).isoformat()

        try:
            async with httpx.AsyncClient(timeout=4.0) as client:
                resp = await client.get(url)
                if resp.status_code == 200:
                    data = resp.json()
                    lines = []
                    for cid, prices in data.items():
                        usd = prices.get("usd", 0)
                        inr = prices.get("inr", 0)
                        change = prices.get("usd_24h_change")
                        change_str = f" (24h change: {change:+.2f}%)" if change is not None else ""
                        lines.append(f"{cid.capitalize()}: ${usd:,.2f} USD / ₹{inr:,.2f} INR{change_str}")

                    snippet = f"Live Market Quotes (CoinGecko): " + "; ".join(lines) + f" [as of {now_iso[:19]} UTC]"
                    return [{
                        "id": f"live-crypto-{uuid.uuid4().hex[:6]}",
                        "source_type": "live_api",
                        "title": "CoinGecko Crypto Market Rates",
                        "url": "https://www.coingecko.com",
                        "snippet": snippet,
                        "retrieved_at": now_iso,
                        "relevance": 96,
                        "metadata": {
                            "api": "CoinGecko",
                            "category": "finance"
                        }
                    }]
        except Exception as e:
            logger.warning(f"[LiveAPIs] Crypto price fetch error: {e}")

        return []

    async def get_exchange_rates(self, query: str) -> List[Dict[str, Any]]:
        """
        Fetches real-time foreign currency exchange rates.
        """
        url = "https://open.er-api.com/v6/latest/USD"
        now_iso = datetime.now(timezone.utc).isoformat()

        try:
            async with httpx.AsyncClient(timeout=4.0) as client:
                resp = await client.get(url)
                if resp.status_code == 200:
                    rates = resp.json().get("rates", {})
                    inr = rates.get("INR", 0)
                    eur = rates.get("EUR", 0)
                    gbp = rates.get("GBP", 0)
                    jpy = rates.get("JPY", 0)
                    snippet = (
                        f"Real-time Forex Rates (Base: 1 USD): "
                        f"₹{inr:.2f} INR, €{eur:.4f} EUR, £{gbp:.4f} GBP, ¥{jpy:.2f} JPY. "
                        f"Updated: {now_iso[:19]} UTC."
                    )
                    return [{
                        "id": f"live-forex-{uuid.uuid4().hex[:6]}",
                        "source_type": "live_api",
                        "title": "Foreign Exchange Market Rates",
                        "url": "https://open.er-api.com",
                        "snippet": snippet,
                        "retrieved_at": now_iso,
                        "relevance": 94,
                        "metadata": {
                            "api": "ExchangeRate-API",
                            "category": "forex"
                        }
                    }]
        except Exception as e:
            logger.warning(f"[LiveAPIs] Forex fetch error: {e}")

        return []


live_api_service = LiveAPIService()
