# Speedy Print UI Implementation Guidelines
> **Design Intent:** Create implementation-ready, token-driven UI guidance for Speedy Print that is optimized for consistency, accessibility, and fast delivery across the e-commerce storefront, matching the exact typographic identity of BurgerPrints.

---

## 1. Design Tokens & Foundations

Toàn bộ giao diện phải sử dụng nghiêm ngặt hệ thống mã token dưới đây. Tuyệt đối không sử dụng mã màu Hex hoặc thông số pixel thô trong mã nguồn.

### 1.1 Typography (Đã cập nhật theo BurgerPrints)
*   `font.family.primary`: "SVN-Gilroy", "Gilroy"
*   `font.family.stack`: "SVN-Gilroy", "Gilroy", system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif
*   `font.size.base`: 16px (Line-height: 25.6px | Weight: 500)
*   **Scale:**
    *   `font.size.xs`: 12px (Thẻ trạng thái, phụ chú)
    *   `font.size.sm`: 13.6px (Nội dung phụ trong Card)
    *   `font.size.md`: 14px
    *   `font.size.lg`: 14.5px
    *   `font.size.xl`: 15px
    *   `font.size.2xl`: 15.52px
    *   `font.size.3xl`: 16px (Kích thước chữ mặc định của Nút bấm)
    *   `font.size.4xl`: 17px (Menu điều hướng / Nhãn nút lớn)

### 1.2 Color Palette & Semantic Mapping (Đã đồng bộ mã màu Cam)
*   `color.text.primary`: `#0f172a` (Tiêu đề, văn bản chính)
*   `color.text.secondary`: `#94a3b8` (Mô tả phụ, sub-text)
*   `color.text.inverse`: `#475569` (Chữ trên nền vô hiệu hóa)
*   `color.surface.muted`: `#ffffff` (Nền Card, nền Header)
*   `color.surface.base`: `#000000` (Nền tối hoặc chữ tương phản cao)
*   `color.surface.raised`: `#f26522` (Màu cam thương hiệu chuẩn của BurgerPrints cho cả Header và Hero CTA)
*   `color.surface.strong`: `#f8fafc` (Nền phân tách phân đoạn hệ thống)

### 1.3 Spacing, Radius & Motion
*   **Spacing:** `space.1=1.86px` | `space.2=8px` | `space.3=9px` | `space.4=10px` | `space.5=12px` | `space.6=14px` | `space.7=14.4px` | `space.8=15px`
*   **Radius:** `radius.xs=4px` | `radius.sm=8px` | `radius.md=10px` | `radius.lg=12px` | `radius.xl=14px` | `radius.2xl=20px` | `radius.step7=28px` | `radius.step8=999px`
*   **Shadows:** 
    *   `shadow.1`: `rgba(15, 23, 42, 0.1) 0px 10px 30px -5px, rgba(15, 23, 42, 0.08) 0px 20px 40px -10px`
    *   `shadow.2`: `rgba(242, 101, 34, 0.28) 0px 4px 14px 0px`
    *   `shadow.3`: `rgba(0, 0, 0, 0.08) 0px 4px 12px 0px`
    *   `shadow.4`: `rgba(242, 101, 34, 0.35) 0px 20px 60px -15px`
*   **Motion:** `motion.duration.instant=200ms` | `motion.duration.fast=300ms`

---

## 2. Component-Level Rules

### 2.1 Primary Button (Ví dụ: Nút "Start Free" & "Start Free — No card needed")
*   **Anatomy:** `[Icon đầu (Tùy chọn)] + [Nhãn Chữ] + [Icon mũi tên đuôi (Tùy chọn)]`
*   **Layout:** Padding dọc `space.5`, Padding ngang `space.8`. Bo góc `radius.sm` (8px). Font sử dụng font định dạng hình học đặc trưng `font.family.primary` giúp chữ bo tròn đều, hiện đại.

#### Trạng thái bắt buộc (Component States)
*   **Default:** Nền buộc phải dùng chung một mã `color.surface.raised` (#f26522), chữ `#ffffff`. Bóng đổ `shadow.2`. (Sửa lỗi lệch màu giữa nút trên Header và Hero section).
*   **Hover:** Nền chuyển màu cam đậm hơn 10% (Tương đương `#d95316`). Bóng đổ chuyển sang `shadow.4`. `cursor: pointer`. Thời gian chuyển đổi áp dụng `motion.duration.instant`.
*   **Focus-visible:** Xuất hiện viền outline rõ ràng dày 2px, màu sắc `color.text.primary`, cách biệt với phần thân nút một khoảng trống 2px (`outline-offset: 2px`).
*   **Active:** Nền chuyển sang tông tối hẳn, triệt tiêu hiệu ứng bóng đổ (`shadow: none`).
*   **Disabled:** Nền `color.text.secondary` giảm độ mờ (opacity 30%), chữ `color.text.inverse`. Vô hiệu hóa mọi sự kiện trỏ chuột (`pointer-events: none`).
*   **Loading:** Ẩn nhãn chữ, hiển thị Spinner xoay tròn đồng tâm với kích thước cố định bằng chiều cao của chữ.
*   **Error:** Viền nút đổi sang màu cảnh báo hệ thống, hiển thị Tooltip mô tả lỗi khi người dùng rê chuột qua.

### 2.2 Secondary / Ghost Button (Ví dụ: Nút "Watch demo")
*   **Anatomy:** `[Icon Play] + [Nhãn Chữ]`
*   **Default:** Nền trong suốt (`background: transparent`), viền `border: 1px solid #e2e8f0`, chữ `color.text.primary`. Font chữ hình học Gilroy giúp nút trông thanh thoát.
*   **Hover:** Nền chuyển sang `color.surface.strong`, chữ giữ nguyên.

### 2.3 Interactive Data Card (Cụm Dashboard mô phỏng bên phải)
Thành phần hiển thị thông tin trực quan phía bên phải màn hình để tăng độ tin cậy.
*   **Anatomy:** Đầu mục trạng thái (`Live`) + Chỉ số chính + Danh sách đơn hàng (`List`).
*   **Layout:** Khung nền sử dụng `color.surface.muted`, bo góc lớn `radius.2xl` (20px), đổ bóng mềm `shadow.1`.
*   **Xử lý nội dung dài (Overflow Handling):** Đối với các dòng tên sản phẩm quá dài (e.g., "Unisex T-Shirt — Gildan 5000..."), bắt buộc phải áp dụng quy chuẩn cắt chuỗi CSS:
```css
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    ```
    Tuyệt đối không được phép tự động xuống dòng làm phá vỡ cấu trúc và chiều cao cố định của hàng dữ liệu.

---

## 3. Accessibility Requirements (WCAG 2.2 AA)

*   **Độ tương phản văn bản (Contrast Constraints):** 
    *   Tất cả văn bản có kích thước nhỏ hơn 18px (bao gồm cả chữ trên các nút bấm chính/phụ và menu) bắt buộc phải đạt tỷ lệ tương phản tối thiểu **4.5:1** so với nền phía sau.
    *   *Sửa đổi từ thiết kế hiện tại:* Nút "Start Free" trên Header (chữ trắng nền cam) kích thước nhỏ phải được tăng kích cỡ lên ít nhất `font.size.4xl` (17px) kèm định dạng Bold (`font.weight` tối thiểu 700) để đảm bảo nét chữ tròn béo của Gilroy không bị nhòe và vượt qua bài kiểm tra độ tương phản.
*   **Điều hướng Bàn phím (Keyboard-first Interactions):**
    *   Hệ thống phải cho phép sử dụng phím `Tab` để di chuyển tuần tự qua 57 liên kết, 11 nút bấm, và 16 ô nhập liệu theo luồng từ trái sang phải, từ trên xuống dưới.
    *   Phím `Enter` hoặc `Space` phải kích hoạt được các hành động mở video demo hoặc chuyển hướng trang.
*   **Trực quan hóa Focus (Focus-visible Rules):** Nghiêm cấm sử dụng thuộc tính `outline: none` trừ khi đã cấu hình một chỉ báo focus tùy chỉnh có độ tương phản rõ rệt.

### Bảng kiểm định Tiếp cận (Accessibility Acceptance Criteria)

| Ngữ cảnh (Context) | Điều kiện kiểm tra (Pass Criteria) | Điều kiện loại bỏ (Fail Criteria) |
| :--- | :--- | :--- |
| **Tương tác nút bấm** | Nhấn `Tab` đến nút, viền bo định vị xuất hiện rõ ràng. | Không có chỉ báo tiêu điểm, người dùng mất dấu con trỏ. |
| **Độ tương phản chữ** | Chữ trắng trên nền cam chính đạt tỷ lệ tương phản $\ge$ 4.5:1. | Chữ quá mờ, không thể đọc được ở khoảng cách tiêu chuẩn. |
| **Hỗ trợ Screen Reader** | Toàn bộ icon (như biểu tượng Play) có thuộc tính `aria-label="Xem video giới thiệu"`. | Icon không có nhãn, trình đọc màn hình chỉ đọc "Button". |

---

## 4. Content and Tone Standards

*   **Tone giọng:** Ngắn gọn, tự tin, tập trung hoàn toàn vào hành động kỹ thuật của người dùng.
*   **Quy tắc nhãn hành động:** Sử dụng các động từ mạnh mang tính cam kết cao ở đầu câu.
*   **Ví dụ chuẩn (DO):**
    *   `Start Free — No card needed` (Minh bạch, rõ ràng quyền lợi).
    *   `Watch demo` (Ngắn gọn, định hướng hành động trực tiếp).
*   **Ví dụ sai (DON'T):**
    *   `Bấm vào đây để đăng ký tài khoản miễn phí ngay hôm nay` (Quá dài dòng, gây loãng mật độ hiển thị giao diện).

---

## 5. Anti-Patterns & Prohibited Implementations (Nghiêm cấm)

1.  **Không đồng nhất mã màu (Color Exception):** Nghiêm cấm sử dụng hai mã màu cam khác nhau cho cùng một loại hành động chính (CTA). Sửa lại mã màu của nút trên Header giống hoàn toàn với nút chính giữa trang (`color.surface.raised` - `#f26522`).
2.  **Một góc bo tự phát (Radius Exception):** Toàn bộ các thẻ hình ảnh, nhãn đơn hàng phụ trong cụm Dashboard không được phép dùng các thông số bo góc tự do. Phải ép cấu hình về các token `radius.xs`, `radius.sm` hoặc `radius.md`.
3.  **Khoảng cách tùy tiện (Spacing Exception):** Khoảng cách giữa các thành phần văn bản và icon bên trong nút bấm hoặc danh sách phải tuân thủ nghiêm ngặt thang đo Spacing Scale (Ưu tiên dùng `space.3` hoặc `space.4`). Không dùng các giá trị chẵn chục tự tạo như `15px`, `20px` nếu không có trong bảng token.

---

## 6. QA Checklist (Bảng kiểm định trước khi bàn giao Code)

- [ ] 1. Toàn bộ mã màu Hex thô đã được thay thế hoàn toàn bằng hệ mã Semantic Tokens trong mã nguồn CSS/Tailwind chưa?
- [ ] 2. Đã nhúng font `"SVN-Gilroy"` vào dự án và kiểm tra độ tương phản (Contrast ratio) cho nút "Start Free" trên Header chưa?
- [ ] 3. Đã khai báo đầy đủ các trạng thái tương tác (`default`, `hover`, `focus-visible`, `active`, `disabled`) cho cấu phần Button chưa?
- [ ] 4. Khi ẩn chuột và thực hiện nhấn phím `Tab`, tiêu điểm di chuyển có đúng thứ tự logic của trang web không?
- [ ] 5. Các chuỗi văn bản dài trong danh sách đơn hàng đã được cấu hình thuộc tính ẩn văn bản thừa bằng dấu ba chấm (`ellipsis`) chưa?
- [ ] 6. Thời gian chuyển động của hiệu ứng hover đã được gán bằng biến token `motion.duration.instant` chưa?