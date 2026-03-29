import httpx
from typing import List, Dict, Any, Optional
from app.config import settings
import asyncio
import hmac
import hashlib
import time


class PolymarketService:
    def __init__(
        self,
        api_url: str = None,
        api_key: str = None,
        api_secret: str = None,
        wallet_address: str = None,
    ):
        self.api_url = api_url or settings.POLYMARKET_API_URL
        self.api_key = api_key
        self.api_secret = api_secret
        self.wallet_address = wallet_address
        self.headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if api_key:
            self.headers["POLY-API-KEY"] = api_key

    def _sign_request(self, method: str, path: str, body: str = "") -> Dict[str, str]:
        if not self.api_secret:
            return {}

        timestamp = str(int(time.time()))
        message = f"{timestamp}{method}{path}{body}"
        signature = hmac.new(
            self.api_secret.encode(), message.encode(), hashlib.sha256
        ).hexdigest()

        return {
            "POLY-API-KEY": self.api_key or "",
            "POLY-API-TIMESTAMP": timestamp,
            "POLY-API-SIGNATURE": signature,
        }

    async def get_markets(self, limit: int = 50) -> List[Dict[str, Any]]:
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{self.api_url}/markets",
                    params={"limit": limit},
                    headers=self.headers,
                )
                if response.status_code == 200:
                    data = response.json()
                    return data.get("data", [])
        except Exception as e:
            print(f"Error fetching markets: {e}")
        return []

    async def get_market(self, condition_id: str) -> Optional[Dict[str, Any]]:
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{self.api_url}/markets/{condition_id}",
                    headers=self.headers,
                )
                if response.status_code == 200:
                    return response.json()
        except Exception as e:
            print(f"Error fetching market: {e}")
        return None

    async def get_order_book(self, token_id: str) -> Dict[str, Any]:
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{self.api_url}/orderbook",
                    params={"token_id": token_id},
                    headers=self.headers,
                )
                if response.status_code == 200:
                    return response.json()
        except Exception as e:
            print(f"Error fetching orderbook: {e}")
        return {"bids": [], "asks": []}

    async def get_price(self, token_id: str) -> Dict[str, float]:
        try:
            orderbook = await self.get_order_book(token_id)
            bids = orderbook.get("bids", [])
            asks = orderbook.get("asks", [])

            best_bid = float(bids[0]["price"]) if bids else 0.0
            best_ask = float(asks[0]["price"]) if asks else 1.0

            mid_price = (best_bid + best_ask) / 2

            return {
                "yes_price": round(mid_price, 2),
                "no_price": round(1 - mid_price, 2),
                "best_bid": best_bid,
                "best_ask": best_ask,
            }
        except Exception as e:
            print(f"Error getting price: {e}")
            return {"yes_price": 0.5, "no_price": 0.5, "best_bid": 0, "best_ask": 1}

    async def get_markets_with_prices(self, limit: int = 50) -> List[Dict[str, Any]]:
        markets = await self.get_markets(limit)

        for market in markets:
            tokens = market.get("tokens", [])
            yes_token = next((t for t in tokens if t.get("outcome") == "Yes"), None)
            no_token = next((t for t in tokens if t.get("outcome") == "No"), None)

            if yes_token:
                prices = await self.get_price(yes_token.get("token_id", ""))
                market["yes_price"] = prices.get("yes_price", 0.5)
                market["no_price"] = prices.get("no_price", 0.5)
                market["yes_token_id"] = yes_token.get("token_id")
                market["no_token_id"] = no_token.get("token_id") if no_token else None
                market["best_bid"] = prices.get("best_bid", 0)
                market["best_ask"] = prices.get("best_ask", 1)

            market["condition_id"] = market.get("conditionId") or market.get(
                "condition_id"
            )

        return markets

    async def place_order(
        self, token_id: str, side: str, amount: float, price: float
    ) -> Dict[str, Any]:
        try:
            order_data = {
                "token_id": token_id,
                "side": side.upper(),
                "size": amount,
                "price": price,
            }

            headers = self.headers.copy()
            if self.api_key and self.api_secret:
                auth_headers = self._sign_request("POST", "/orders", str(order_data))
                headers.update(auth_headers)

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.api_url}/orders",
                    json=order_data,
                    headers=headers,
                )
                if response.status_code in [200, 201]:
                    return {"success": True, "data": response.json()}
                else:
                    return {
                        "success": False,
                        "error": response.text,
                        "status": response.status_code,
                    }
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def cancel_order(self, order_id: str) -> Dict[str, Any]:
        try:
            headers = self.headers.copy()
            if self.api_key and self.api_secret:
                auth_headers = self._sign_request("DELETE", f"/orders/{order_id}")
                headers.update(auth_headers)

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.delete(
                    f"{self.api_url}/orders/{order_id}",
                    headers=headers,
                )
                return {"success": response.status_code in [200, 204]}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def get_positions(self) -> List[Dict[str, Any]]:
        try:
            headers = self.headers.copy()
            if self.api_key and self.api_secret:
                auth_headers = self._sign_request("GET", "/positions")
                headers.update(auth_headers)

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{self.api_url}/positions",
                    headers=headers,
                )
                if response.status_code == 200:
                    return response.json()
        except Exception as e:
            print(f"Error fetching positions: {e}")
        return []

    async def get_balance(self) -> Dict[str, Any]:
        try:
            headers = self.headers.copy()
            if self.api_key and self.api_secret:
                auth_headers = self._sign_request("GET", "/balance")
                headers.update(auth_headers)

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{self.api_url}/balance",
                    headers=headers,
                )
                if response.status_code == 200:
                    return response.json()
        except Exception as e:
            print(f"Error fetching balance: {e}")
        return {}
