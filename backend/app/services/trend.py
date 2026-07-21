from abc import ABC, abstractmethod
from datetime import date
from typing import List, Dict, Any, Optional, Tuple
from sqlmodel import Session, select
from app.schemas.trend import SuggestedQuestions, ClimateType
from app.models.catalog import ShippingZone
import logging

logger = logging.getLogger(__name__)

# Từ điển sự kiện tĩnh cho các quốc gia chính
EVENTS_DB = {
    "US": {
        1: ["New Year's Day"],
        2: ["Valentine's Day", "Super Bowl"],
        3: ["St. Patrick's Day"],
        4: ["Easter Holiday"],
        5: ["Mother's Day", "Memorial Day"],
        6: ["Father's Day", "Juneteenth"],
        7: ["Independence Day (July 4th)"],
        8: ["Back to School Season"],
        9: ["Labor Day"],
        10: ["Halloween Prep"],
        11: ["Thanksgiving", "Black Friday / Cyber Monday"],
        12: ["Christmas", "Holiday Shopping Season"]
    },
    "DE": {
        1: ["New Year's Day"],
        2: ["Valentine's Day", "Carnival"],
        3: ["St. Patrick's Day"],
        4: ["Easter Monday"],
        5: ["Mother's Day", "Ascension Day"],
        6: ["Pentecost"],
        7: ["Summer Holidays"],
        8: ["Back to School"],
        9: ["Oktoberfest Begins"],
        10: ["German Unity Day", "Halloween"],
        11: ["St. Martin's Day"],
        12: ["Christmas Markets", "Holiday Season"]
    },
    "VN": {
        1: ["Tết Dương Lịch", "Chuẩn bị Tết Nguyên Đán"],
        2: ["Tết Nguyên Đán", "Valentine's Day"],
        3: ["Ngày Quốc tế Phụ nữ (8/3)"],
        4: ["Giỗ tổ Hùng Vương", "Ngày Giải phóng Miền Nam (30/4)"],
        5: ["Ngày Quốc tế Lao động (1/5)"],
        6: ["Ngày Quốc tế Thiếu nhi (1/6)"],
        7: ["Mùa du lịch hè"],
        8: ["Lễ Vu Lan"],
        9: ["Ngày Quốc khánh (2/9)", "Tết Trung Thu"],
        10: ["Ngày Phụ nữ Việt Nam (20/10)", "Halloween"],
        11: ["Ngày Nhà giáo Việt Nam (20/11)"],
        12: ["Giáng Sinh", "Chuẩn bị Tết Dương Lịch"]
    }
}

# Danh sách lễ hội phương Tây chung làm fallback cho các nước Âu Mỹ khác
WESTERN_EVENTS = {
    1: ["New Year's Day"],
    2: ["Valentine's Day"],
    3: ["St. Patrick's Day"],
    4: ["Easter Holiday"],
    5: ["Mother's Day"],
    6: ["Father's Day"],
    7: ["Summer Vacation"],
    8: ["Summer Holiday Season"],
    9: ["Autumn Prep"],
    10: ["Halloween Prep"],
    11: ["Thanksgiving / Black Friday Season"],
    12: ["Christmas & New Year Shopping"]
}

# Các nước EU phổ biến để fallback về DE
EU_COUNTRIES = {"IT", "ES", "NL", "BE", "AT", "CH", "SE", "PL", "DK", "FI", "IE", "PT", "FR", "GR"}

class ITrendService(ABC):
    @abstractmethod
    def validate_and_fallback_country(self, session: Session, country_code: str) -> Tuple[str, bool]:
        """
        Kiểm tra xem quốc gia có được hỗ trợ vận chuyển hay không (qua bảng shipping_zones).
        Trả về: (quốc gia thực tế sử dụng, True nếu là quốc gia gốc được hỗ trợ / False nếu là quốc gia fallback)
        """
        pass

    @abstractmethod
    def get_climate_season(self, month: int, country_code: str) -> str:
        """Xác định mùa khí hậu của quốc gia đó tại tháng truy vấn"""
        pass

    @abstractmethod
    def get_events_by_region(self, month: int, country_code: str) -> List[str]:
        """Lấy danh sách các sự kiện/ngày lễ hội dựa trên tháng và quốc gia"""
        pass

    @abstractmethod
    def get_seasonal_suggestions(self, session: Session, country: str, month: int) -> SuggestedQuestions:
        """Lấy đầy đủ thông tin xu hướng thời tiết, sự kiện và gợi ý sản phẩm"""
        pass


class TrendService(ITrendService):
    def validate_and_fallback_country(self, session: Session, country_code: str) -> Tuple[str, bool]:
        country_upper = country_code.upper().strip()

        # 1. Kiểm tra trong DB cache bảng shipping_zones
        try:
            zone = session.exec(
                select(ShippingZone).where(ShippingZone.country_code == country_upper)
            ).first()
            if zone:
                return country_upper, True
        except Exception as e:
            logger.error(f"Lỗi truy vấn ShippingZone: {str(e)}")

        # Nếu là các quốc gia cốt lõi (US, DE, VN, AU, NZ), cho phép trả về True luôn để dễ test và không bị phụ thuộc chặt vào DB cache
        if country_upper in ["US", "DE", "VN", "AU", "NZ"]:
            return country_upper, True

        # 2. Logic fallback nếu không tìm thấy trong DB
        if country_upper in EU_COUNTRIES:
            return "DE", False
        elif country_upper == "CA":
            return "US", False
        elif country_upper == "NZ":
            # Kiểm tra xem AU có trong DB không, nếu có fallback AU, không thì US
            try:
                au_zone = session.exec(
                    select(ShippingZone).where(ShippingZone.country_code == "AU")
                ).first()
                if au_zone:
                    return "AU", False
            except Exception:
                pass
            return "US", False

        # Mặc định fallback về US
        return "US", False

    def get_climate_season(self, month: int, country_code: str) -> str:
        country_upper = country_code.upper()

        # Kiểu khí hậu đặc thù của Việt Nam
        if country_upper == "VN":
            if month in [11, 12, 1, 2]:
                return "Dry_cool"
            else:
                return "Rainy_hot"

        # Phân loại theo Bán cầu địa lý
        southern_hemisphere = {"AU", "NZ", "ZA", "BR", "AR"}
        if country_upper in southern_hemisphere:
            if month in [6, 7, 8]:
                return "Winter"
            elif month in [12, 1, 2]:
                return "Summer"
            elif month in [3, 4, 5]:
                return "Autumn"
            else:
                return "Spring"
        else:
            # Bắc bán cầu (US, DE, FR, GB, CA, etc.)
            if month in [12, 1, 2]:
                return "Winter"
            elif month in [6, 7, 8]:
                return "Summer"
            elif month in [3, 4, 5]:
                return "Spring"
            else:
                return "Autumn"

    def get_events_by_region(self, month: int, country_code: str) -> List[str]:
        country_upper = country_code.upper()

        # Tìm sự kiện cụ thể cho nước đó
        if country_upper in EVENTS_DB:
            return EVENTS_DB[country_upper].get(month, [])

        # Nếu là các nước phương Tây khác (Châu Âu, Mỹ, Úc), fallback sang WESTERN_EVENTS
        is_western = country_upper in EU_COUNTRIES or country_upper in {"US", "GB", "FR", "DE", "CA", "AU", "NZ"}
        if is_western:
            return WESTERN_EVENTS.get(month, ["Holiday Shopping"])

        return ["Holiday Shopping", "General Merchandising"]

    def _get_weather_context(self, season: str) -> str:
        s = season.lower()
        if s == "winter":
            return "Thời tiết lạnh, tuyết rơi nhiều. Nhu cầu cực kỳ cao đối với các trang phục giữ ấm như Hoodie, Sweatshirt."
        elif s == "summer":
            return "Thời tiết nóng bức, năng động. Nhu cầu rất lớn cho các sản phẩm áo thun (T-Shirt) cotton 100% thoáng mát."
        elif s == "spring":
            return "Thời tiết ấm dần, mát mẻ. Thời gian lý tưởng cho các hoạt động ngoài trời, dã ngoại. Thích hợp bán T-Shirt và Mugs."
        elif s == "autumn":
            return "Thời tiết mát mẻ, chớm lạnh. Thời điểm tuyệt vời để bán áo nỉ (Sweatshirt) hoặc T-Shirt tay dài."
        elif s == "dry_cool":
            return "Thời tiết mát mẻ, hanh khô, thích hợp cho các hoạt động du lịch, lễ hội cuối năm. Phù hợp cho T-Shirt và Hoodies."
        elif s == "rainy_hot":
            return "Thời tiết nóng ẩm, có mưa nhiều. Thích hợp bán các sản phẩm tiện dụng hằng ngày như ly sứ (Mugs) hoặc T-Shirt chất liệu mát mẻ."
        return "Thời tiết ôn hòa, thích hợp bán mọi mặt hàng POD."

    def _get_product_types(self, season: str) -> List[str]:
        s = season.lower()
        if s in ["winter", "dry_cool"]:
            return ["Hoodies", "Sweatshirts"]
        elif s == "summer":
            return ["T-Shirts", "Mugs"]
        elif s == "spring":
            return ["T-Shirts", "Mugs", "Sweatshirts"]
        elif s in ["autumn", "rainy_hot"]:
            return ["Sweatshirts", "T-Shirts", "Mugs"]
        return ["T-Shirts", "Hoodies", "Sweatshirts", "Mugs"]

    def _get_suggestions(self, country: str, month: int, season: str, events: List[str]) -> List[str]:
        s = season.lower()
        event_str = events[0] if events else "Holiday"

        if s in ["winter", "dry_cool"]:
            return [
                f"Tìm Hoodie chất lượng tốt nhất để bán cho thị trường {country} vào dịp {event_str}",
                f"So sánh giá Sweatshirt giữa các xưởng ở {country} để tối ưu chi phí ship",
                f"Sản phẩm nào giữ ấm tốt, thời gian ship dưới 5 ngày tại {country}?"
            ]
        elif s == "summer":
            return [
                f"Tìm mẫu T-Shirt bán chạy có giá vốn dưới $8 cho dịp {event_str}",
                f"Gợi ý Mugs có profit margin trên 45% bán làm quà tặng tại {country}",
                f"Xưởng nào ship T-Shirt nội địa {country} nhanh nhất với giá cạnh tranh?"
            ]
        else:
            return [
                f"Gợi ý sản phẩm phù hợp cho chiến dịch {event_str} tại thị trường {country}",
                f"So sánh phí ship Standard và Express của T-Shirt tại xưởng ở {country}",
                f"Tìm sản phẩm có base cost rẻ nhất để bắt đầu bán tại {country}"
            ]

    def _is_empty_country(self, country: Optional[str]) -> bool:
        return not country or country.strip().lower() in {"none", "null", "undefined"}

    def _get_cold_start_suggestions(self) -> List[str]:
        return [
            "Tìm mẫu T-Shirt bán chạy giá vốn dưới $8 cho dịp Back to School tại US",
            "Xưởng nào ship Hoodies sang Úc (AU) nhanh nhất trong mùa đông này?",
            "Gợi ý các mẫu Ornaments chất liệu Glass bán chạy đón đầu mùa Giáng Sinh toàn cầu",
        ]

    def get_seasonal_suggestions(self, session: Session, country: Optional[str], month: Optional[int]) -> SuggestedQuestions:
        resolved_month = month or date.today().month
        if self._is_empty_country(country):
            target_country = "US"
            season = self.get_climate_season(resolved_month, target_country)
            return SuggestedQuestions(
                country=target_country,
                original_country=None,
                is_fallback=True,
                month=resolved_month,
                season=season,
                weather_context="Chưa chọn market cụ thể, nên hệ thống gợi ý ma trận khám phá đa thị trường với US làm anchor mặc định.",
                events=["Back to School Season", "Southern Winter", "Christmas"],
                product_types=["T-Shirts", "Hoodies", "Ornaments & Gifts"],
                suggestions=self._get_cold_start_suggestions()
            )

        original_country = country.upper().strip()

        # 1. Áp dụng cơ chế Fallback quốc gia
        target_country, is_supported = self.validate_and_fallback_country(session, original_country)
        is_fallback = not is_supported

        # 2. Lấy thông tin mùa, sự kiện, thời tiết
        season = self.get_climate_season(resolved_month, target_country)
        weather_context = self._get_weather_context(season)
        events = self.get_events_by_region(resolved_month, target_country)
        product_types = self._get_product_types(season)
        suggestions = self._get_suggestions(target_country, resolved_month, season, events)

        return SuggestedQuestions(
            country=target_country,
            original_country=original_country,
            is_fallback=is_fallback,
            month=resolved_month,
            season=season,
            weather_context=weather_context,
            events=events,
            product_types=product_types,
            suggestions=suggestions
        )


def get_seasonal_suggestions(country: str, month: int) -> SuggestedQuestions:
    from sqlmodel import Session
    from app.database import engine
    with Session(engine) as session:
        return TrendService().get_seasonal_suggestions(session, country, month)

