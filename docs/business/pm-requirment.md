# Goal

Xây dựng hệ thống BurgerAgent hoàn thiện, sẵn sàng lên product để demo chào hàng với BurgerPrint

# Những yêu cầu của PM

### Bài toán

Cần đọc kỹ bài toán trong file `@topic.md` và nắm rõ các yêu cầu trong đó. Tiến hành đánh giá và phân tích đề bài để làm rõ yêu cầu business, yêu cầu dự án.
Gợi ý:
user input (ngôn ngữ tự nhiên) -> LLM (phân tích câu input, nắm ý định, kiểm tra thông tin, nếu chưa đủ tiến hành hỏi ngược lại. Đủ thông tin thì đến bước tiếp theo) -> Call API của BurgerPrints hoặc DB để lấy thông tin -> LLM (kiểm tra đủ data, nếu chưa đủ thì kiểm tra và lấy các data còn thiếu.) -> Function calling (gọi các funct nội bộ sử dụng python engine để tính toán) -> LLM (kiểm tra và xử lý thông tin, nếu chưa đủ quay trở lại bước gọi API lấy data hoặc tính toán lại. nếu đủ thì xử lý và trả ra output).

### Data

- Nên sử dụng các gọi toàn bộ API của BurgerPrint để lấy đầy đủ data để lưu trữ (cache) nhất là data về catalog sản phẩm nhằm tránh việc gọi API liên tục. Set thời gian để sync data (ví dụ: 5h một lần).
- Phân tích xem nên lưu trữ data như thế nào để tiện cho việc query (SQLite hay Json).
- Tạo schema hay doc để LLM biết data đang ở đâu và cần lấy data nào thì lấy như thế nào (ví dụ lưu trong SQLite thì cần có schema để tạo query lấy data, lưu bằng Json thì cần doc để biết data ở file json nào,...)
- Chủ động phân tích bài toán để chọn DB, ưu tiên nhỏ nhẹ. Về lịch sử chat, long-short memory cho agent, cache, user, lịch sử order, order,... (ưu tiên những loại sau: SQLite, FAISS, ChromaDB, PostgreSQL, Supabase, MongoDB, MinIO, Redis).
- Tách tầng DB ra khỏi logic nghiệp vụ, sử dụng layer Repository để việc scale và đổi DB diễn ra thuận lợi

### Workflow (Agent workflow)

- Sử dụng LangChain hoặc ADK framework để xây dựng Agent workflow, ưu tiên tính tuỳ biến cao.
- Pattern multi-agent hoặc state-agent hoặc hybrid, có bổ sung thêm RAG nếu cần. Dù pattern nào thì cũng tập trung giải quyết bài toàn cốt lõi trước và chắc chắn sau này sẽ mở rộng thành multi-agent vì ít nhất các tính năng gen design, mockup, quản lý order, các kênh bán hàng,... sẽ không thể nào sử dụng khác được.
- Về LLM, cho phép chọn 2 cơ chế:
  1. Gọi API từ các nhà cung cấp OpenAI, Google, Claude,... ( ưu tiên trong giai đoạn phát triển sẽ sử dụng model Gemini-3.1-flash-lite từ Google)
  2. Gọi API từ model tự host. Model tự host thông quan ollama, llama.cpp, sglang, vllm và theo chuẩn API OpenAI.
     Xây dựng system prompt cho phép LLM tự suy nghĩ, thinking để đưa ra các quyết định trong khuôn khổ workflow như lấy data nào, gọi tool nào, thiếu thông tin gì, nên hỏi lại user cái gì,... để khai thác hết sức mạnh và tự nhiên nhất có thể.
- Cần lưu lịch sử chat, session, long-short memory,...
- Xây dựng các tool nội bộ bằng python engine để agent sử dụng tính toán logic, không được phép để agent (LLM) tự tính.
- Core cho các phase đầu là phải giải quyết được bài toán BurgerPrints đặt ra.
- Cần tính toán để các phase sau xây dựng tool search web hoặc web scraping,... để agent lấy các thông tin cần thiết trên internet phục vụ sau này như tìm kiếm các trend mới nhất để gợi ý cho seller,...
- Về thuế, nếu API của BurgerPrint không có sẵn thì phải search web hoặc sử dụng API public về thuế của các quốc gia để lấy thuế. Phần này cũng nên save vào DB vì thuế sẽ không thay đổi hằng ngày, có thể sync mỗi tháng.

### API

- Cần đọc và tham khảo tài liệu chi tiết API v2.0 của BurgerPrints tại `https://api.burgerprints.com/` cho quá trình xây dựng hệ thống & workflow.
- Hệ thống cần được xây dựng theo chuẩn API Design Pattern

### System

- Tách tầng riêng biệt cho dự án (ví dụ: Controller - Service - Repository).
- Hệ thống sẽ được phát triển trong một repo duy nhất chia ra Frontend - Backend - AI, sau khi hoàn thành sẽ có file docker cho toàn bộ dự án để bên BurgerPrint dễ dàng build và test. Mục đích của việc chia ra như vậy là để khi được duyệt và tích hợp vào hệ thống của Burger Prints sẽ dễ dàng scale và tích hợp. Chính vì vậy dù chung một repo và có thể nói là chạy local trước nhưng quá trình phát triển luôn thiết kế system hướng đến việc scale sau này.
- Khi phát triển áp dụng các nguyên tắc Clean code, SOLID, OOP,...
- Sử dụng các phương thức giao tiếp qua API, Websocket, Web hook,... phù hợp, sử dụng sync và async hợp lý cho từng case, chuyển qua background job cho các tác vụ nặng cần nhiều thơi gian,..

### Future feature

1. Tính năng tạo báo cáo: Từ cuộc trò chuyện hiện tại của seller với Agent về sản phẩm mới hoặc nghiên cứu thị trường từ đó tạo báo cáo để seller chia sẽ với team để cùng lên kế hoạch và chốt chiến dịch marketing/sales,...
2. Thêm tính năng tạo design cho sản phẩm (hướng multi-agent): thêm agent tạo sinh để dựa vào những mô tả của seller để giúp tạo ra các thiết kế phù hợp với sản phẩm mà seller sẽ bán (thay vì đi thiết kế thủ công và upload file). Khi này chốt sản phẩm xong seller sẽ cùng với sự hỗ trợ của Agent để chốt thiết kế, tạo mockup (cho phép download file design và mockup) để chia sẽ với team product - marketing - sale cùng làm việc cho chiến dịch.
3. Tích hợp quản lý đa sàn: Có trang dashboard để theo dõi lợi nhuận, sản phẩm, lượt bán, trend,... trên các sản như Shopify, Tiktok Shop, Shopee,... Hỗ trợ quản lý và theo dõi, tạo report bằng Agent thông qua chat với ngôn ngữ tự nhiên (tức là trong cuộc trò chuyện có thể yêu cầu tạo report nhanh với dữ liệu từ các sàn từ đó đưa ra các đề xuất,...)
