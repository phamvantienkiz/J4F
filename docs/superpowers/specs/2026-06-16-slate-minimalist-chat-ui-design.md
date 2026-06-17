# Đặc tả Thiết kế Slate Minimalist cho Chat UI

## 1. Bối cảnh và Mục tiêu
Nâng cấp giao diện chatbot Agent hiện tại sang phong cách tối giản cao cấp (Slate Minimalist). Giải quyết vấn đề hiển thị lộn xộn giữa tiến trình suy nghĩ (Thought Process) của AI với câu trả lời văn bản thực tế trong cùng một bong bóng chat. Đồng thời, cải thiện cấu trúc định dạng văn bản (Typography) và hiệu ứng cuộn mượt mà để mang lại trải nghiệm chuẩn sản phẩm (production-grade).

## 2. Chi tiết Thiết kế

### 2.1. Phân tách Cấu phần Thought Process (Dynamic Thought Process)
- **Cấu trúc dữ liệu**:
  - Mở rộng kiểu dữ liệu `ChatMessage` trong `App.tsx`:
    ```typescript
    type ChatMessage = {
      id: string;
      role: "user" | "assistant";
      text: string;
      response?: AgentResponse;
      steps?: Array<{ step: string; message: string }>; // Lưu trữ tiến trình suy nghĩ tách biệt
      isStreaming?: boolean; // Theo dõi trạng thái stream của tin nhắn
    };
    ```
- **Hành vi luồng dữ liệu (Data Flow)**:
  - Khi nhận được chunk sự kiện chứa `step` và `message`, chúng ta cập nhật thuộc tính `steps` của tin nhắn đó thay vì ghi đè vào `text`.
  - Khi bắt đầu nhận `token` đầu tiên, hoặc khi nhận payload cuối cùng, chúng ta đặt `isStreaming` thành `false` (hoặc ngưng trạng thái stream).
- **Giao diện hiển thị (UI Rendering)**:
  - Khối Thought Process sẽ được hiển thị ở đầu bong bóng chat của trợ lý (`assistant`), được thiết kế dưới dạng hộp gấp gọn (Collapsible/Accordion) sạch sẽ.
  - Sử dụng CSS thuần để tạo kiểu hộp tối giản:
    - Nền: `bg-slate-50` (màu `#f8fafc` hoặc `#f1f5f9`).
    - Khung viền: `border-slate-100` (`#e2e8f0` mỏng 1px).
    - Font chữ: micro-typography cỡ chữ nhỏ `11px`, màu xám dịu `text-slate-500` (`#64748b`).
    - Có một dấu chấm tròn nhấp nháy chuyển động (`.thought-pulse`) kế bên bước hiện tại đang chạy để tạo cảm giác hoạt họa tinh tế.
  - Khi tin nhắn đang stream (`isStreaming` hoạt động), hộp suy nghĩ sẽ tự động mở rộng để hiển thị các bước đang thực hiện. Khi stream xong (nhận được payload cuối cùng), hộp sẽ tự động đóng lại (collapse) để giữ giao diện gọn gàng, nhưng người dùng vẫn có thể bấm vào tiêu đề để xem lại lịch sử suy nghĩ của Agent.

### 2.2. Nâng cấp Typography & Bong bóng Chat (Typography & Chat Bubbles)
- **Typography cho Trợ lý (`.assistant-prose`)**:
  - Tự định nghĩa một bộ CSS phong cách Markdown Typography tối giản tương đương với Tailwind `@tailwindcss/typography` (`prose prose-slate`):
    - Các đoạn văn `p` có khoảng giãn cách `margin-bottom: 12px`.
    - Danh sách `ul`, `ol` có thụt lề, khoảng cách giữa các mục `li` thoáng đãng.
    - Đường phân cách `hr` nét đứt/nét liền mảnh màu nhạt.
    - Mã nguồn khối `pre`, `code` có nền xám đen nhẹ bo tròn góc để dễ đọc.
- **Tạo kiểu bong bóng chat (Chat Bubbles styling)**:
  - Bong bóng của Người dùng (`.message.user`):
    - Đổi sang tông màu tối Slate sang trọng: Nền màu xám sẫm `#0f172a`, chữ trắng, bo góc tối giản.
  - Bong bóng của Trợ lý (`.message.assistant`):
    - Loại bỏ hoàn toàn khối nền trắng cồng kềnh. Giao diện trở nên tinh khiết với nền trong suốt.
    - Có một đường phân cách mảnh bên dưới mỗi lượt hội thoại để phân định rõ ràng các tin nhắn nhưng không tạo cảm giác nặng nề.

### 2.3. Cuộn mượt mà & Chuyển động (Smooth Scrolling & Transitions)
- Áp dụng `scroll-behavior: smooth` cho container `.chat-stream`.
- Cập nhật hàm cuộn tự động trong React bằng cách dùng `requestAnimationFrame` và đo lường khoảng cách cuộn thực tế, đảm bảo việc tự động cuộn xuống dưới cùng khi có chữ mới stream ra không gây giật gián đoạn và không "cướp" chuột nếu người dùng đang chủ động cuộn lên đọc lịch sử.

## 3. Xác minh và Kiểm thử
- Chạy biên dịch TypeScript (`npm run typecheck`) để kiểm tra tính hợp lệ của kiểu dữ liệu `ChatMessage` mở rộng.
- Chạy bản build (`npm run build`) để kiểm tra toàn bộ CSS và JSX được gói gọn gàng.
- Trải nghiệm giao diện trực quan trong chatbot để đảm bảo dòng suy nghĩ và câu chữ được hiển thị độc lập, chuyển trạng thái mượt mà.
