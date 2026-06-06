## Goal

Lên plan và break task thật chi tiết để triển khai phần Backend và AI

## Context

Đọc tất cả các file cần thiết trong:

- `@./Solution/docs/ai/`
- `@./Solution/docs/test/`
- `@./Solution/docs/architecture/`
  sau đó thinking để lên plan và break task thật chi tiết để triển khai phần Backend và AI.

- Cần có task khởi tạo Backend FastAPI, khởi tạo và sử dụng UV để quản lý. Khởi tạo môi trường ảo Python, cấu hình requirements.txt hoặc pyproject.toml (tôi nghĩ là nên sử dụng uv với pyproject.toml để quản lý nhưng vẫn cần xem xét với yêu cầu dễ cài đặt trên máy của giám khảo) với các thư viện cốt lõi ( fastapi , langgraph , chromadb ,sqlalchemy ).

- Phần Mock API Data:
  Trên `api-docs.burgerprints.com` phần Order > Create Order `https://api.burgerprints.com/#e3ca5cfc-d95a-4694-a03b-5d11bc36aa23` kịch bản 1 tạo order với catalog sku, vì Trong mẫu đó có đủ các thông tin bắt buộc và khi sử dụng với API thật thì cũng giống như vậy.
  -> Không dồn quá nhiều tài nguyên cho các task tạo Mockdata, luôn sử dụng API thực tế từ BurgerPrint. Khi thật sự không ổn mới sử dụng Mockdata.

## Request:

Thực hiện Lên plan và break task thật chi tiết để triển khai phần Backend và AI theo các yêu cầu ở trên. Lưu ý các task lần này không có Frontend. Plan chi tiết hãy tạo file markdown trong thư mục `@./Solution/docs/plan/` các task chi tiết cần được break vào trong `@todo.md`.

---

> Note:
> Có thể tham khảo thêm file `@./Solution/docs/slides/gpt-solution.md` để thêm các context sâu.
> Đề bài được đặt trong file `@./Solution/docs/topic.md`
> Có thể sử dụng hoặc tham khảo skills _fastapi-expert_ tại `@./.agents/skills/fastapi-expert.md`
