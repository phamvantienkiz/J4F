# Tax Calculation Feature — BurgerPrints Agent

> **Phiên bản:** 1.0
> **Cập nhật:** Tháng 6/2026
> **Áp dụng cho:** Module `backend/app/services/tax_engine.py`

---

## 1. Tổng quan kiến trúc

Module này tính thuế ước tính cho seller POD khi bán cross-border, phục vụ hai mục đích:

1. **Margin estimation** — Seller hỏi: *"Bán $24.99 sang Đức, margin còn bao nhiêu?"*
2. **Pricing guidance** — Agent tính giá bán tối thiểu để đạt margin target sau thuế

### Chiến lược dữ liệu

```
EU (27 nước)  →  VATcomply API  (real-time, nguồn EU Commission TEDB)
US            →  Static table   (rates theo bang, top 20 bang POD)
UK            →  Static table   (VAT 20% cố định)
Canada        →  Static table   (GST/HST/PST theo tỉnh)
Australia     →  Static table   (GST 10% cố định toàn quốc)
Vietnam       →  Static table   (VAT 8% đến 31/12/2026)
```

> **Tại sao EU dùng API còn các vùng khác dùng static?**
> EU có 27 nước với rates khác nhau và thay đổi không theo lịch cố định (Hungary vừa điều chỉnh 2024, Estonia tăng từ 20% lên 24% năm 2024, Phần Lan tăng lên 25.5%). VATcomply là API miễn phí, không cần key, lấy thẳng từ EU Commission TEDB — đây là nguồn chính thống nhất. Trong khi đó UK/CA/AU/VN có rates ổn định hơn và ít biến động hơn.

---

## 2. Khái niệm cốt lõi — Hai hệ thống thuế

### 2.1 Sales Tax (Mỹ) — Thuế cộng thêm

Người mua trả thêm ngoài giá niêm yết. **Seller không bị giảm revenue.**

```
Giá niêm yết:     $24.99
+ Sales Tax 8%:   + $2.00
Khách trả:        $26.99
Seller nhận:      $24.99  ← không thay đổi

Margin = (24.99 - base_cost - shipping) / 24.99
```

### 2.2 VAT / GST (EU, UK, CA, AU, VN) — Thuế nhúng trong giá

Giá niêm yết **đã bao gồm** VAT. Seller phải trích VAT ra nộp nhà nước. **Margin bị ảnh hưởng.**

```
Giá niêm yết:     £24.99  (đã gồm VAT 20%)
VAT (20%):        - £4.17
Seller thực nhận: £20.83  ← bị giảm

Công thức tách VAT:  Net = Price ÷ (1 + VAT_rate)
                     Net = £24.99 ÷ 1.20 = £20.83

Margin = (20.83 - base_cost - shipping) / 20.83
```

---

## 3. VATcomply API — EU Real-time Rates

### Thông tin

| Thuộc tính | Giá trị |
|---|---|
| Base URL | `https://api.vatcomply.com` |
| API Key | **Không cần** |
| Rate limit | 2 requests/giây |
| Nguồn dữ liệu | EU Commission TEDB (Tax Database) + VIES |
| License | Open source — MIT |
| Phủ sóng | 27 EU member states + UK |
| Cập nhật | Real-time khi có thay đổi |

### Endpoint sử dụng

```
GET https://api.vatcomply.com/vat_rates
GET https://api.vatcomply.com/vat_rates?country_code=DE
```

### Ví dụ response

```json
{
  "DE": {
    "country_code": "DE",
    "country_name": "Germany",
    "standard_rate": 19,
    "reduced_rates": [7],
    "super_reduced_rates": [],
    "parking_rates": []
  }
}
```

### Các endpoint bổ sung có thể dùng

| Endpoint | Mục đích |
|---|---|
| `GET /vat_rates` | Tất cả EU rates |
| `GET /vat_rates?country_code=XX` | Rate của 1 nước |
| `GET /geolocate` | Tự detect nước theo IP |
| `GET /rates` | Exchange rates từ ECB |

---

## 4. Bảng thuế tĩnh (Static Table)

### 4.1 🇺🇸 Mỹ — Sales Tax theo bang

> **Lưu ý quan trọng về Clothing (áo POD):**
> Một số bang **miễn thuế** cho quần áo (clothing exemption). Seller POD bán áo thun, hoodie cần chú ý điều này.

#### Các bang KHÔNG có sales tax (0%)

| Bang | Tên | Ghi chú |
|---|---|---|
| `OR` | Oregon | Không có sales tax |
| `MT` | Montana | Không có sales tax |
| `NH` | New Hampshire | Không có sales tax |
| `DE` | Delaware | Không có sales tax |
| `AK` | Alaska | Không có sales tax cấp bang (có thể có local tax) |

#### Top 20 bang POD sellers hay bán — Sales Tax rate

| Mã bang | Tên bang | State Rate | Effective Rate (avg incl. local) | Clothing Exemption |
|---|---|---|---|---|
| `CA` | California | 7.25% | **8.68%** | ❌ Không miễn |
| `TX` | Texas | 6.25% | **8.20%** | ❌ Không miễn |
| `NY` | New York | 4.00% | **8.52%** | ✅ **Miễn** (dưới $110/item) |
| `FL` | Florida | 6.00% | **7.01%** | ❌ Không miễn |
| `IL` | Illinois | 6.25% | **8.82%** | ⚠️ Miễn 1% (chỉ essential clothing) |
| `PA` | Pennsylvania | 6.00% | **6.34%** | ✅ **Miễn hoàn toàn** |
| `OH` | Ohio | 5.75% | **7.24%** | ❌ Không miễn |
| `GA` | Georgia | 4.00% | **7.31%** | ❌ Không miễn |
| `NC` | North Carolina | 4.75% | **6.98%** | ❌ Không miễn |
| `MI` | Michigan | 6.00% | **6.00%** | ❌ Không miễn |
| `NJ` | New Jersey | 6.625% | **6.60%** | ✅ **Miễn** (dưới $110/item) |
| `VA` | Virginia | 5.30% | **5.65%** | ❌ Không miễn |
| `WA` | Washington | 6.50% | **9.23%** | ❌ Không miễn |
| `AZ` | Arizona | 5.60% | **8.40%** | ❌ Không miễn |
| `TN` | Tennessee | 7.00% | **9.55%** | ❌ Không miễn |
| `MA` | Massachusetts | 6.25% | **6.25%** | ✅ **Miễn** (dưới $175/item) |
| `IN` | Indiana | 7.00% | **7.00%** | ❌ Không miễn |
| `MO` | Missouri | 4.225% | **8.02%** | ❌ Không miễn |
| `MN` | Minnesota | 6.875% | **7.46%** | ✅ **Miễn hoàn toàn** |
| `WI` | Wisconsin | 5.00% | **5.43%** | ❌ Không miễn |
| `CO` | Colorado | 2.90% | **7.77%** | ❌ Không miễn |
| `SC` | South Carolina | 6.00% | **7.46%** | ❌ Không miễn |
| `AL` | Alabama | 4.00% | **9.22%** | ❌ Không miễn |
| `LA` | Louisiana | 4.45% | **9.55%** | ❌ Không miễn |
| `KY` | Kentucky | 6.00% | **6.00%** | ❌ Không miễn |

> **Nguồn:** Tax Foundation 2025, Sales Tax Institute 2025
> **Default fallback:** `8.0%` (US average effective rate) nếu không rõ bang

---

### 4.2 🇬🇧 UK — VAT

| Loại thuế | Rate | Áp dụng cho |
|---|---|---|
| Standard VAT | **20%** | Hầu hết hàng hóa (áo, cốc, poster, túi) |
| Reduced VAT | 5% | Năng lượng, một số thực phẩm trẻ em |
| Zero rate | 0% | Thực phẩm, sách, quần áo trẻ em |

> **Rate áp dụng cho POD products (áo, hoodie, mug, poster):** `20%`
> **Ngưỡng đăng ký VAT:** £90,000/năm (2025)
> **Nguồn:** HMRC VAT Notice 700 (2025)

---

### 4.3 🇨🇦 Canada — GST / HST / PST

> Canada không có rate thống nhất toàn quốc. Rate phụ thuộc vào **tỉnh/vùng lãnh thổ** của địa chỉ ship.

| Mã tỉnh | Tên tỉnh | Rate | Cấu thành | Ghi chú |
|---|---|---|---|---|
| `AB` | Alberta | **5%** | GST 5% | Tỉnh duy nhất không có PST |
| `BC` | British Columbia | **12%** | GST 5% + PST 7% | |
| `MB` | Manitoba | **12%** | GST 5% + PST 7% | |
| `NB` | New Brunswick | **15%** | HST 15% | |
| `NL` | Newfoundland & Labrador | **15%** | HST 15% | |
| `NS` | Nova Scotia | **15%** | HST 15% | |
| `NT` | Northwest Territories | **5%** | GST 5% | |
| `NU` | Nunavut | **5%** | GST 5% | |
| `ON` | Ontario | **13%** | HST 13% | Tỉnh đông dân nhất |
| `PE` | Prince Edward Island | **15%** | HST 15% | |
| `QC` | Quebec | **14.975%** | GST 5% + QST 9.975% | |
| `SK` | Saskatchewan | **11%** | GST 5% + PST 6% | |
| `YT` | Yukon | **5%** | GST 5% | |

> **Default (không rõ tỉnh):** `13%` (Ontario HST — tỉnh đông dân nhất, xác suất cao nhất)
> **Nguồn:** Canada Revenue Agency (CRA) 2025

---

### 4.4 🇦🇺 Australia — GST

| Thuế | Rate | Ghi chú |
|---|---|---|
| GST (Goods & Services Tax) | **10%** | Áp dụng toàn quốc, cố định |

> **Đặc điểm:**
> - Rate cố định duy nhất trên toàn quốc — không có biến động theo bang/vùng
> - Áp dụng cho mọi hàng nhập khẩu từ 1/7/2018 (đã bỏ ngưỡng miễn AUD $1,000)
> - Marketplace operators (Amazon AU, eBay AU) tự collect và remit GST
> - **Ngưỡng đăng ký:** AUD $75,000/năm
> - **Nguồn:** Australian Taxation Office (ATO) 2025

---

### 4.5 🇻🇳 Việt Nam — VAT

| Loại | Rate | Thời gian áp dụng | Căn cứ pháp lý |
|---|---|---|---|
| **Rate giảm (đang áp dụng)** | **8%** | Đến **31/12/2026** | Nghị định 174/2025/NĐ-CP |
| Rate tiêu chuẩn | 10% | Từ 01/01/2027 | Luật Thuế GTGT |
| Rate đặc biệt | 5% | Một số nhóm hàng đặc thù | |
| Không chịu thuế | 0% | Hàng xuất khẩu | |

> **Lưu ý về hàng nhập khẩu vào VN (từ 18/02/2025):**
> Chính phủ đã **bãi bỏ miễn thuế nhập khẩu** cho hàng giá trị thấp (trước đây miễn dưới 1 triệu VND). Kể từ 18/02/2025, **mọi hàng hóa nhập khẩu** đều chịu thuế nhập khẩu + VAT.
>
> **Công thức tính thuế nhập khẩu vào VN:**
> ```
> CIF         = Giá hàng + Bảo hiểm + Vận chuyển
> Import Duty = CIF × Import_Rate   (0%–30% tùy category)
> VAT Base    = CIF + Import Duty
> VAT         = VAT Base × 8%
> Total Tax   = Import Duty + VAT
> ```
>
> **POD products (áo, cốc):** Import Duty thường 12–20%
> **Nguồn:** Nghị định 174/2025/NĐ-CP, Tổng cục Hải quan Việt Nam

---

### 4.6 🇪🇺 EU — Bảng tham chiếu (backup nếu VATcomply API down)

> **Ưu tiên:** Luôn gọi VATcomply API trước. Bảng này chỉ là fallback.
> Rates theo EU Commission TEDB — cập nhật tháng 6/2026.

| Mã nước | Tên nước | Standard VAT | Reduced VAT | Ghi chú |
|---|---|---|---|---|
| `AT` | Austria | **20%** | 10%, 13% | |
| `BE` | Belgium | **21%** | 6%, 12% | |
| `BG` | Bulgaria | **20%** | 9% | |
| `CY` | Cyprus | **19%** | 5%, 9% | |
| `CZ` | Czech Republic | **21%** | 12% | Giảm từ 15% xuống 12% năm 2024 |
| `DE` | Germany | **19%** | 7% | |
| `DK` | Denmark | **25%** | 0% | |
| `EE` | Estonia | **24%** | 9% | ⚠️ Tăng từ 20% lên 24% (01/2024) |
| `ES` | Spain | **21%** | 10% | |
| `FI` | Finland | **25.5%** | 10%, 14% | ⚠️ Tăng từ 24% (09/2024) |
| `FR` | France | **20%** | 5.5%, 10% | |
| `GR` | Greece | **24%** | 6%, 13% | |
| `HR` | Croatia | **25%** | 5%, 13% | |
| `HU` | Hungary | **27%** | 5%, 18% | Cao nhất EU |
| `IE` | Ireland | **23%** | 9%, 13.5% | |
| `IT` | Italy | **22%** | 5%, 10% | |
| `LT` | Lithuania | **21%** | 5%, 9% | |
| `LU` | Luxembourg | **17%** | 8% | Thấp nhất EU |
| `LV` | Latvia | **21%** | 12% | |
| `MT` | Malta | **18%** | 5%, 7% | |
| `NL` | Netherlands | **21%** | 9% | |
| `PL` | Poland | **23%** | 5%, 8% | |
| `PT` | Portugal | **23%** | 6%, 13% | |
| `RO` | Romania | **19%** | 5%, 9% | |
| `SE` | Sweden | **25%** | 6%, 12% | |
| `SI` | Slovenia | **22%** | 5%, 9.5% | |
| `SK` | Slovakia | **20%** | 10% | |
| `GB` | United Kingdom | **20%** | 5% | Post-Brexit — hệ thống riêng |

> **Nguồn fallback:** EU Commission TEDB, 06/2026

---

## 5. Công thức tính margin theo khu vực

### US (Sales Tax — cộng ngoài)

```python
# Tax KHÔNG giảm revenue seller
tax_amount    = selling_price * tax_rate
net_revenue   = selling_price              # Seller nhận đủ
margin        = (net_revenue - base_cost - shipping_fee) / net_revenue
```

### EU / UK / CA / AU / VN (VAT/GST — nhúng trong giá)

```python
# Tax-inclusive: seller thực nhận ít hơn giá niêm yết
net_revenue   = selling_price / (1 + vat_rate)   # Tách VAT ra
tax_amount    = selling_price - net_revenue
margin        = (net_revenue - base_cost - shipping_fee) / net_revenue

# Tính giá bán tối thiểu để đạt min_margin sau thuế:
# net_revenue × (1 - min_margin) >= base_cost + shipping
# net_revenue >= (base_cost + shipping) / (1 - min_margin)
# selling_price = net_revenue × (1 + vat_rate)
min_net       = (base_cost + shipping_fee) / (1 - min_margin_target)
min_price     = min_net * (1 + vat_rate)
```

### Ví dụ thực tế

```
Seller bán áo Hoodie giá $29.99, base cost $8.50, shipping $4.00

Bán sang Đức (DE, VAT 19%):
  Net revenue  = $29.99 / 1.19 = $25.20
  Tax amount   = $4.79
  Net profit   = $25.20 - $8.50 - $4.00 = $12.70
  Margin       = $12.70 / $25.20 = 50.4% ✅

Bán sang Mỹ - California (CA, Sales Tax 8.68%):
  Net revenue  = $29.99        (seller nhận đủ)
  Tax amount   = $2.60         (buyer trả thêm)
  Net profit   = $29.99 - $8.50 - $4.00 = $17.49
  Margin       = $17.49 / $29.99 = 58.3% ✅

Bán sang New York (clothing exempt):
  Tax amount   = $0.00         (áo được miễn thuế!)
  Net profit   = $17.49
  Margin       = 58.3% ✅ (giống CA vì tax không ảnh hưởng seller)
```

---

## 6. Cấu trúc response của Tax Engine

```python
@dataclass
class TaxResult:
    region: str           # "DE", "US", "CA", "AU", "VN"
    sub_region: str       # Bang/Tỉnh/Nước cụ thể
    tax_type: str         # "VAT", "GST", "Sales Tax", "GST/HST"
    rate: float           # 0.19 = 19%
    rate_pct: str         # "19%"
    tax_amount: float     # Số tiền thuế
    net_revenue: float    # Seller thực nhận
    data_source: str      # "VATcomply API" | "Static table"
    note: str             # Giải thích thêm
    is_estimated: bool    # True nếu dùng static/average
```

---

## 7. Lịch cập nhật bảng tĩnh

| Khu vực | Tần suất cần kiểm tra | Nguồn kiểm tra |
|---|---|---|
| **EU** | Tự động (VATcomply API) | `api.vatcomply.com` |
| **UK** | Mỗi năm (thường tháng 3 Budget) | `gov.uk/vat-rates` |
| **US** | Mỗi quý (states thay đổi thường xuyên) | `taxfoundation.org` |
| **Canada** | Mỗi năm (Budget tháng 3-4) | `canada.ca/cra` |
| **Australia** | Rất hiếm (GST 10% từ năm 2000) | `ato.gov.au` |
| **Vietnam** | Theo Nghị định — hết 31/12/2026 | `chinhphu.vn` |

---

## 8. Giới hạn và disclaimer

> Module này cung cấp **ước tính thuế** phục vụ mục đích **tư vấn định giá và tính margin** cho POD sellers. Đây **không phải** tư vấn thuế pháp lý.
>
> - **US:** Effective rate theo địa chỉ thực có thể dao động ±1-2% tùy local jurisdiction. Seller bán qua Etsy/Amazon thường được marketplace collect thay.
> - **EU:** Rates từ VATcomply API là chính thống nhưng không thay thế tư vấn thuế cho business đăng ký OSS/IOSS.
> - **VN:** Rate 8% theo NĐ 174/2025, hết hiệu lực 31/12/2026. Sau đó tự động về 10%.
> - Với doanh thu lớn (>$50K/năm/quốc gia), nên tham khảo accountant địa phương.

---

*Tài liệu này được duy trì bởi BurgerPrints Agent team. Mọi thay đổi về tax rate cần cập nhật đồng thời vào file này và `tools/tax_engine.py`.*
