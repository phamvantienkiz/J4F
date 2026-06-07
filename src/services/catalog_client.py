import requests

from src.core.config import settings


class CatalogApiClient:
    def __init__(self, base_url=None, timeout=30):
        self.base_url = (base_url or settings.burgerprints_catalog_api_base_url).rstrip("/")
        self.timeout = timeout

    def _get(self, path, params=None):
        response = requests.get(
            f"{self.base_url}{path}",
            params=params,
            headers={
                "Accept": "application/json",
                "User-Agent": "BurgerPrintsAgent/0.1",
            },
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.json(), {
            "method": "GET",
            "path": path,
            "url": response.url,
            "params": params or {},
        }

    def list_catalogs(self):
        return self._get("/catalogsV2/list")

    def get_by_alias(self, alias_name):
        data, meta = self._get(f"/catalogsV2/alias/{alias_name}")
        if isinstance(data, dict) and isinstance(data.get("data"), dict):
            return data["data"], meta
        return data, meta

    def get_shipping_locations(self, short_code, location_id):
        return self._get("/catalogsV2/locations", {"shortCode": short_code, "partnerId": location_id})

    def get_location_sla(self, location_id):
        return self._get("/catalogsV2/location-sla", {"partnerId": location_id})
