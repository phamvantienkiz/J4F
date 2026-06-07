import os

import requests

from src.core.config import settings


class BurgerPrintsClient:
    def __init__(self, api_key=None, base_url=None, timeout=30):
        self.api_key = api_key or os.getenv("BURGERPRINTS_API_KEY")
        if not self.api_key:
            raise RuntimeError("Missing BURGERPRINTS_API_KEY in .env")

        self.base_url = (base_url or settings.burgerprints_api_base_url).rstrip("/")
        self.timeout = timeout

    def _headers(self):
        return {
            "api-key": self.api_key,
            "Accept": "application/json",
            "User-Agent": "BurgerPrintsAgent/0.1",
        }

    def _get(self, path, params=None):
        response = requests.get(
            f"{self.base_url}{path}",
            params=params,
            headers=self._headers(),
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.json(), {
            "method": "GET",
            "path": path,
            "url": response.url,
            "params": params or {},
        }

    def _post(self, path, json_body=None):
        response = requests.post(
            f"{self.base_url}{path}",
            json=json_body or {},
            headers=self._headers(),
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.json(), {
            "method": "POST",
            "path": path,
            "url": response.url,
            "params": {},
        }

    def list_orders(self, page_size=10, sandbox=True):
        page_size = max(1, min(int(page_size), 100))
        return self._get("/order", {"sandbox": str(bool(sandbox)).lower(), "page_size": str(page_size)})

    def get_order(self, order_id):
        data, meta = self._get(f"/order/{order_id}")
        if isinstance(data, dict) and isinstance(data.get("data"), dict):
            return data["data"], meta
        return data, meta

    def get_balance(self):
        return self._get("/balance")

    def list_products(self, page=1, page_size=100):
        page = max(1, int(page))
        page_size = max(1, min(int(page_size), 200))
        return self._get("/product", {"page": str(page), "page_size": str(page_size)})

    def get_product(self, short_code):
        data, meta = self._get(f"/product/{short_code}")
        if isinstance(data, dict) and isinstance(data.get("data"), dict):
            return data["data"], meta
        return data, meta

    def list_out_of_stock(self, page=1, page_size=100):
        page = max(1, int(page))
        page_size = max(1, min(int(page_size), 200))
        return self._get("/product/outofstock", {"page": str(page), "page_size": str(page_size)})

    def create_order(self, payload):
        safe_payload = {**payload, "sandbox": True}
        data, meta = self._post("/order", safe_payload)
        meta["params"] = self._create_order_params(safe_payload)
        return data, meta

    def _create_order_params(self, payload):
        items = payload.get("items") or []
        first_item = items[0] if items else {}
        return {
            "sandbox": True,
            "items_count": len(items),
            "catalog_sku": first_item.get("catalog_sku"),
            "quantity": first_item.get("quantity"),
        }
