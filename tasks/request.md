## Goal

- Tiếp tục hoàn thiện solution cho MVP tạo ấn tượng với Ban giám Khảo

## Context

Okay, sau khi đã hoàn thiện các tài liệu trong `@Solution/docs/ai` và `@Solution/docs/architecture` thì tôi có trao đổi với mentor của team. Thì hướng đi về solution cho bài toán đã đúng nhưng cần hoàn thiện thêm về phần UI (frontend), tên sản phẩm (định hướng product cho mvp này).

Những trao đổi về phần UX/UI với mentor thì chúng tôi cần thêm nhiều bao gồm hoàn thiện UX/UI chat hướng đến đúng đối tượng người dùng sao cho hiện đại, chuyên nghiệp, gọn gàng, dễ sử dụng và thêm các chức năng như:

- Login/Register đơn giản
- UX/UI chat, side bar lịch sử chat, thanh baner bên phải cho một vài chức năng như xem thông tin sản phẩm, oder,..
- Cần lưu lịch sử chat -> cần database và có thể cả vectorDB nếu cần
- Core AI là LangGrap và Backend FastAPI, thêm Frontend sử dụng NextJS hoặc Vite với TypeScrpit

## Request:

1. Với những yêu cầu ở trên của mentor, hãy tiến hành suy nghĩ và hoàn thiện các giải pháp hiện tại. Cần tạo thêm các file markdow trong `@Solution/docs/ai` chứa các thông tin/solution cần thiết.
2. Với cấu trúc dự án thì tất cả code của dự án sẽ nằm trong thư mục `@Product/`. Thông thường tôi sẽ chia ra thành backend, frontend, ai. Trong backend FastAPI thường chứa đủ cấu trúc app/ trong app/ có: api/, core/, db/, models/, schemas/,... mục đích như thế để sau này dễ mở rộng và clean code. Hiện tại đối với đòi hỏi của Mentor thì chắc chắn phải xây dựng thêm frontend với NextJS hoặc Vite sử dụng TypeScript. Hãy phân tích và lên cấu trúc thư mục cho dự án. (nên tạo file hoặc viết vào file nào đó trong `@Solution/docs/ai`)

---

> Note:
> Có thể tham khảo thêm file `@./Solution/docs/slides/gpt-solution.md` để thêm các context sâu.
