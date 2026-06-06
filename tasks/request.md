## Goal

Verify lại về solution cũng như flow của user

## Context

Ví dụ thực tế với user:

- "Tôi muốn bán T-shirt cho thị trường Mỹ, giá vốn dưới $8, ship dưới 5 ngày, chọn xưởng nào, SKU nào?"​

- "So sánh giá Hoodie giữa các xưởng đang có, xưởng nào ship EU rẻ nhất?"​

- "Tôi định bán giá $24.99, margin tối thiểu 40%, gợi ý sản phẩm phù hợp."​

Với ví dụ sử dụng trên của khách hàng tôi chốt lại một số thông tin như sau:

Phía database và vectorDB thì chỉ lưu những thông tin cần thiết, không lưu data các thông tin của xưởng, sản phẩm,... vì phần này sẽ thay đổi theo giờ/ngày nên cần sử dụng API của BurgerPrints để lấy thông tin -> Database sử dụng SQLite (nếu quá cần thiết thì sử dụng postgresql) phía vectorDB thì chọn giữa FAISS và ChromaDB (lưu lịch sử chat hay coversaion thì ưu tiên ChromaDB).

Flow thì có thể nghĩ đơn giản là AI sẽ nhận thông tin của user sau đó quyết định gọi API nào để lấy data? sau đó gọi tool (python core) nào để tính toán sau đó trả ra các kết quả, AI tổng hợp và đưa ra đề xuất cho user (có cả các bảng giá để so sánh).

## Request:

Tôi nghĩ với những gì chúng ta phát triển đến giai đoạn hiện tại thì vẫn đang đi đúng hướng cho giải pháp AI Agent và thêm các ý mà mentor gợi ý. Một lần nữa hãy verify lại để đảm bảo tất cả các tài liệu đang được thống nhất.

---

> Note:
> Có thể tham khảo thêm file `@./Solution/docs/slides/gpt-solution.md` để thêm các context sâu.
> Đề bài được đặt trong file `@./Solution/docs/topic.md`
