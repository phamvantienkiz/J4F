# BurgerPrints API Discovery

## Kết luận hiện tại

Chưa thể khẳng định đã có **toàn bộ API của BurgerPrints**, nhưng hiện tại đã có đủ API để làm core của bài thi:

- Tìm product/SKU từ catalog thật.
- Lấy supplier/xưởng fulfillment cho từng SKU.
- Lấy base cost, second-side cost, additional-side cost.
- Lấy shipping destination, delivery time, carrier, first item price, additional item price.
- Lấy processing/SLA theo supplier.
- Lấy order list, order detail, balance từ BurgerPrints API v2.

Phần chưa nên tự claim là đầy đủ:

- Exact `create_order` request schema chưa được xác minh end-to-end.
- Cancel order API có được nhắc trong docs cũ nhưng chưa test lại.
- Tracking chủ động nên dùng webhook/callback hoặc order status sau khi có create-order flow rõ ràng.

## API nhóm Order / Account

Base URL:

```http
https://api.burgerprints.com/v2
```

Auth:

```http
api-key: YOUR_API_KEY
```

### List orders

```http
GET https://api.burgerprints.com/v2/order
```

Dùng cho:

- Lấy danh sách order mới nhất.
- Fallback order-item SKU nếu catalog API không dùng được.

### Get order detail

```http
GET https://api.burgerprints.com/v2/order/{order_id}
```

Ví dụ:

```http
GET https://api.burgerprints.com/v2/order/A30558-CT-5604773
```

Dùng cho:

- Xem fulfillment items trong một order.
- Tuyệt đối không đưa PII khách hàng vào response agent.

### Get balance

```http
GET https://api.burgerprints.com/v2/balance
```

Dùng cho:

- Current balance.
- Fulfillment cost paid/pending.
- Pending deposit.

## API nhóm Product v2

Base URL:

```http
https://api.burgerprints.com/v2
```

Auth:

```http
api-key: YOUR_API_KEY
```

### List products

```http
GET https://api.burgerprints.com/v2/product?page=1&page_size=200
```

Dùng cho:

- Lấy danh sách product/base.
- Mapping short code trước khi gọi detail.

Field quan trọng:

```text
short_code
name
display_name
```

### Product detail by short code

```http
GET https://api.burgerprints.com/v2/product/{short_code}
```

Ví dụ:

```http
GET https://api.burgerprints.com/v2/product/USG5000
GET https://api.burgerprints.com/v2/product/USMG5000UL
```

Field quan trọng:

```text
short_code
name
display_name
print_area
resolution_default
variations[].sku
variations[].size
variations[].color
variations[].price
variations[].2nd_price
variations[].addition_price
variations[].partner_id
variations[].partner_name
```

Mapping trong core:

```text
variation.price -> base_cost
variation.2nd_price -> second_item_price / second_side_cost
variation.addition_price -> additional_side_cost
variation.partner_name -> supplier / xưởng
variation.partner_id -> supplier id
```

### Out-of-stock products/SKUs

```http
GET https://api.burgerprints.com/v2/product/outofstock?page=1&page_size=200
```

Dùng cho:

- Loại SKU hết hàng khỏi ranking.

## Public Catalog API

User đã xác nhận `catalog-api.burgerprints.com` được phép dùng chính thức trong bài thi.

Base URL:

```http
https://catalog-api.burgerprints.com/api/v1
```

Header thường không bắt buộc, nhưng UI có thể dùng:

```http
api-key: burgerprints
```

### Catalog list

```http
GET https://catalog-api.burgerprints.com/api/v1/catalogsV2/list
```

Dùng cho:

- Lấy catalog product list.
- Mapping `shortCode` sang `aliasName`.

Field quan trọng:

```text
data.baseNews.content[].shortCode
data.baseNews.content[].name
data.baseNews.content[].displayName
data.baseNews.content[].aliasName
data.baseNews.content[].dropshipPriceMin
data.baseNews.content[].dropshipPriceMax
data.baseNews.content[].locations

data.baseBestSellers.content[]
data.baseSuggest.content[]
```

Ví dụ item:

```json
{
  "shortCode": "EUOPBBZ02",
  "name": "Baby T-shirt | Babybugz BZ02 (EU)",
  "displayName": "Baby T-shirt | Babybugz BZ02 (EU)",
  "aliasName": "baby-t-shirt-babybugz-bz02-eu",
  "dropshipPriceMin": 10.8,
  "dropshipPriceMax": 12.3,
  "locations": "Pura,Hatta"
}
```

### Product detail by alias

```http
GET https://catalog-api.burgerprints.com/api/v1/catalogsV2/alias/{aliasName}
```

Ví dụ:

```http
GET https://catalog-api.burgerprints.com/api/v1/catalogsV2/alias/unisex-t-shirt-comfort-colors-1717-us-label
```

Dùng cho:

- Lấy product detail giàu dữ liệu hơn Product API v2.
- Lấy SKU/baseSku theo supplier.
- Lấy location/supplier id để gọi shipping API.

Field quan trọng:

```text
shortCode
name
displayName
currency
baseCost
baseSku[].sku
baseSku[].sizeName
baseSku[].colorName
baseSku[].baseCost
baseSku[].secondSidePrice
baseSku[].defaultProfit
baseSku[].location
baseSku[].locationName
baseSku[].shippingCostUs
baseSku[].shippingAddingUs
baseSku[].shippingCostWW
baseSku[].shippingAddingWW
locations[].id
locations[].name
locations[].value
shippingTimeUS
shippingTimeWW
shippingCostUs
shippingCostWW
shippingAddingUs
shippingAddingWW
```

Mapping quan trọng:

```text
baseSku[].location -> supplier/location id
baseSku[].locationName -> supplier name
locations[].id -> supplier/location id
locations[].name -> supplier name
baseSku[].baseCost -> base cost
baseSku[].secondSidePrice -> cost in mặt thứ 2
baseSku[].shippingCostUs -> phí ship item đầu tiên tới US
baseSku[].shippingAddingUs -> phí ship mỗi item tiếp theo tới US
baseSku[].shippingCostWW -> phí ship item đầu tiên tới ngoài US / worldwide
baseSku[].shippingAddingWW -> phí ship mỗi item tiếp theo tới ngoài US / worldwide
```

Mentor xác nhận các field này dùng để show thông tin shipping chung theo xưởng/SKU. Công thức theo quantity:

```text
shipping_fee = first_item_shipping + (quantity - 1) * additional_item_shipping
```

Ví dụ đơn 2 áo ship US:

```text
shipping_fee = shippingCostUs + shippingAddingUs
```

Ví dụ SKU:

```json
{
  "shortCode": "USMCC1717UL",
  "sku": "USTCC1717UL-Bay-S",
  "sizeName": "S",
  "colorName": "Bay",
  "baseCost": "9.0",
  "secondSidePrice": "3.75",
  "location": "hzxCJqcVBUcMwUSf",
  "locationName": "Matterhorn",
  "shippingCostUs": "0.5",
  "shippingAddingUs": "0"
}
```

### Shipping destination / delivery time

Đây là API quan trọng nhất đã dò từ UI.

```http
GET https://catalog-api.burgerprints.com/api/v1/catalogsV2/locations?shortCode={SHORT_CODE}&partnerId={LOCATION_ID}
```

Ví dụ:

```http
GET https://catalog-api.burgerprints.com/api/v1/catalogsV2/locations?shortCode=USMCC1717UL&partnerId=f49AxYt4Q7aR8Zov
```

Dùng cho:

- Shipping destination.
- Shipping service.
- Delivery time.
- Shipping carrier.
- First item shipping price.
- Additional item shipping price.

Response shape:

```json
{
  "code": 200,
  "message": "success",
  "data": [
    {
      "countryCode": "VN",
      "countryName": "Vietnam",
      "flag": "https://dg86kmop4ajn0.cloudfront.net/flags/VN.png",
      "details": [
        {
          "method": "standard",
          "name": "Standard",
          "description": "15-20 business days",
          "carriers": "DHL",
          "firstItemPrice": "0.5",
          "additionalItemPrice": "0",
          "position": 2
        }
      ]
    }
  ]
}
```

Mapping vào agent:

```text
countryCode -> market/destination country
countryName -> destination name
details[].name -> shipping service
details[].description -> delivery time
details[].carriers -> carrier
details[].firstItemPrice -> first item shipping fee
details[].additionalItemPrice -> additional item shipping fee
```

Ví dụ đã test cho product `USMCC1717UL`:

```text
Helia / f49AxYt4Q7aR8Zov
US: Standard, 2-7 business days, USPS, first $0.50, additional $0.00
VN: Standard, 15-20 business days, DHL, first $0.50, additional $0.00

Denali / t1ZhbRa1aDfkZgKl
US: Standard, 2-7 business days, USPS, first $1.00, additional $1.00
VN: Standard, 15-20 business days, Asendia USA, first $1.00, additional $1.00

Matterhorn / hzxCJqcVBUcMwUSf
US: Standard, 2-7 business days, USPS, first $0.50, additional $0.00
```

### Supplier processing/SLA

```http
GET https://catalog-api.burgerprints.com/api/v1/catalogsV2/location-sla?partnerId={LOCATION_ID}
```

Ví dụ:

```http
GET https://catalog-api.burgerprints.com/api/v1/catalogsV2/location-sla?partnerId=t1ZhbRa1aDfkZgKl
```

Response:

```json
{
  "code": 200,
  "message": "success",
  "data": [
    {
      "processingTime": "2.05",
      "sla": "67.24"
    }
  ]
}
```

Dùng cho:

- Processing time score.
- SLA score.
- Ranking supplier khi nhiều xưởng cùng có SKU hợp lệ.

### Supplier detail

```http
GET https://catalog-api.burgerprints.com/api/v1/catalogsV2/locations/{LOCATION_ID}
```

Ví dụ:

```http
GET https://catalog-api.burgerprints.com/api/v1/catalogsV2/locations/t1ZhbRa1aDfkZgKl
```

Dùng cho:

- Mô tả fulfillment center.
- Recommended marketplace.
- Supplier metadata.

### Product detail filtered by supplier/location

```http
GET https://catalog-api.burgerprints.com/api/v1/catalogsV2/{SHORT_CODE}/locations/{LOCATION_ID}
```

Ví dụ:

```http
GET https://catalog-api.burgerprints.com/api/v1/catalogsV2/USMCC1717UL/locations/t1ZhbRa1aDfkZgKl
```

Dùng cho:

- Lấy product detail đã filter theo supplier.
- Response lớn, nên chỉ gọi khi thật sự cần.

### Fulfillment location list

```http
GET https://catalog-api.burgerprints.com/api/v1/catalogsV2/locations/list
```

Dùng cho:

- Lấy danh sách fulfillment centers.
- Có thể cache lâu.

## Webhook callback

Webhook dùng sau khi create order có `callback_url`.

Method:

```http
POST {callback_url}
Content-Type: application/json
```

Sample body:

```json
[
  {
    "order_id": "A888888-TS-16917",
    "reference_order_id": "api_custom_doormat_1",
    "carrier": "DHL",
    "code": "WD39SGK8GC8ZZ6D0",
    "url": "https://webtrack.dhlglobalmail.com/?trackingnumber=WD39SGK8GC8ZZ6D0"
  }
]
```

Dùng cho:

- Tracking callback.
- Update carrier/tracking code/tracking URL sau khi order được fulfill.

Không cần cho core recommendation ban đầu.

## Cách agent nên dùng các API

### Query ví dụ

```text
Tôi muốn bán T-shirt cho thị trường Mỹ, giá vốn dưới $8, ship dưới 5 ngày, chọn xưởng nào, SKU nào?
```

### Flow đề xuất

1. Parser hiểu intent là `search_catalog`.
2. Parser trích filter:

```json
{
  "product_type": "T-shirt",
  "country": "US",
  "max_base_cost": 8,
  "max_delivery_days": 5
}
```

3. Gọi catalog list/search để lấy product phù hợp.
4. Với từng product candidate, lấy alias detail:

```http
GET /catalogsV2/alias/{aliasName}
```

5. Normalize `baseSku[]` thành row SKU:

```text
sku
shortCode
product name
size
color
baseCost
secondSidePrice
location
locationName
shippingCostUs
shippingAddingUs
```

6. Với mỗi `location`, gọi shipping destination API:

```http
GET /catalogsV2/locations?shortCode={shortCode}&partnerId={location}
```

7. Lọc `countryCode` theo market người dùng hỏi.
8. Lấy `details[].description` để parse delivery days.
9. Tính cost:

```text
quantity = số lượng seller muốn tính, mặc định 1
shipping_fee = firstItemPrice + (quantity - 1) * additionalItemPrice
total_fulfillment_cost = baseCost * quantity + shipping_fee
optional_second_side_total = total_fulfillment_cost + secondSidePrice * quantity
```

10. Rank theo:

```text
- Có ship tới country được hỏi
- Delivery days <= filter nếu có
- Base cost <= filter nếu có
- Total cost thấp hơn
- SLA/processing time tốt hơn
- Supplier phù hợp marketplace hơn nếu có metadata
```

11. Trả lời seller-ready:

```text
Khuyến nghị SKU: ...
Xưởng: ...
Base cost: ...
Shipping: ...
Delivery time: ...
Carrier: ...
Vì sao chọn: ...
Các lựa chọn thay thế: ...
```

## Đủ cho bài thi chưa?

Đủ cho phần chính của đề:

- Conversational AI agent.
- Natural language Vietnamese/English.
- Gọi API thật.
- Tìm SKU/xưởng phù hợp.
- So sánh cost/shipping/delivery.
- Trả recommendation cho seller.

Chưa nên mở rộng sang create order tự động cho tới khi xác minh schema chính thức và thêm bước seller confirmation.
