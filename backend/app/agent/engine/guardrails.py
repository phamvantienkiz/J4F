import re

# Rule 1: No Code Gen / Programming Assistance Keywords
RULE_1_KEYWORDS = [
    r"viết\s*(?:mã|code|script|chương\s*trình|phần\s*mềm|hàm|lớp)",
    r"lập\s*trình",
    r"sửa\s*(?:mã|code|lỗi\s*code|bug\s*code)",
    r"tối\s*ưu\s*(?:mã|code)",
    r"refactor",
    r"giải\s*thích\s*(?:mã|code)",
    r"hướng\s*dẫn\s*viết\s*(?:code|mã)",
    r"python\s*code",
    r"javascript\s*code",
    r"html\s*code",
    r"css\s*code",
    r"viết\s*bot",
    r"generate\s*code",
    r"write\s*code",
    r"code\s*html",
    r"code\s*css",
    r"code\s*js",
    r"code\s*python",
    r"làm\s*(?:website|trang\s*web|app|ứng\s*dụng)"
]

# Rule 3: Anti-Jailbreak / Sensitive Data Patterns
RULE_3_KEYWORDS = [
    r"api[-_\s]?key",
    r"credential",
    r"password",
    r"mật[-_\s]?khẩu",
    r"architecture[-_\s]?path",
    r"hidden[-_\s]?instruction",
    r"reveal[-_\s]?instructions",
    r"reveal[-_\s]?your[-_\s]?instructions",
    r"show[-_\s]?config",
    r"tiết[-_\s]?lộ[-_\s]?prompt",
    r"cung[-_\s]?cấp[-_\s]?prompt",
]

# Rule 5: Financial / Legal Liability Keywords (Direct matches)
RULE_5_DIRECT_KEYWORDS = [
    r"investment[-_\s]?advice",
    r"legal[-_\s]?advice",
    r"financial[-_\s]?advice",
    r"stock[-_\s]?prediction",
    r"crypto[-_\s]?prediction",
    r"bitcoin[-_\s]?prediction",
    r"legal[-_\s]?consultation",
    r"tư[-_\s]?vấn[-_\s]?pháp[-_\s]?lý",
    r"tư[-_\s]?vấn[-_\s]?luật",
    r"khuyên[-_\s]?đầu[-_\s]?tư",
]

def check_guardrails(message: str) -> str | None:
    """
    Kiểm tra các quy tắc bảo mật hệ thống trên tin nhắn của người dùng.
    Trả về câu trả lời tương ứng nếu vi phạm guardrail, ngược lại trả về None.
    """
    if not message:
        return None

    message_lower = message.lower()

    # --- 0. Rule #1: No Code Gen ---
    for pattern in RULE_1_KEYWORDS:
        if re.search(pattern, message_lower):
            return "Tôi là trợ lý hỗ trợ kinh doanh và hệ thống, tôi không hỗ trợ viết hoặc xử lý mã nguồn (code)."

    # --- 1. Rule #3: Anti-Jailbreak / Credential Disclosure ---
    # Kiểm tra trực tiếp các từ khóa nhạy cảm
    for pattern in RULE_3_KEYWORDS:
        if re.search(pattern, message_lower):
            return "Tôi không được phép cung cấp thông tin cấu hình và bảo mật hệ thống."

    # Kiểm tra tổ hợp chứa "prompt" hoặc "instructions" / "rules" kèm theo "hệ thống", "ẩn", "ngầm", "bảo mật", "cấu hình"
    has_prompt_term = "prompt" in message_lower or "instructions" in message_lower or "rules" in message_lower
    has_system_term = "hệ thống" in message_lower or "system" in message_lower or "ẩn" in message_lower or "hidden" in message_lower or "bảo mật" in message_lower or "cấu hình" in message_lower or "ngầm" in message_lower
    if has_prompt_term and has_system_term:
        return "Tôi không được phép cung cấp thông tin cấu hình và bảo mật hệ thống."


    # --- 2. Rule #4: Anti-Attack Payload / Injection / Token Exhaustion ---
    # a. SQL Keywords / Pattern Injection
    sql_keywords = [
        r"union\s+select",
        r"select\s+.*\s+from",
        r"insert\s+into",
        r"drop\s+table",
        r"delete\s+from",
        r"update\s+.*\s+set",
        r"information_schema",
        r"or\s+1\s*=\s*1",
        r"or\s+['\"]1['\"]\s*=\s*['\"]1"
    ]
    for pattern in sql_keywords:
        if re.search(pattern, message_lower):
            return "Yêu cầu không hợp lệ. Hệ thống đã chặn hành vi khai thác mã độc."

    # b. Code syntax: detect programming snippets
    code_indicators = ["def ", "class ", "import ", "const ", "let ", "function", "public static void", "<html>", "javascript:", "print("]
    has_code_indicator = any(indicator in message_lower for indicator in code_indicators)
    braces_count = message_lower.count("{") + message_lower.count("}") + message_lower.count("<") + message_lower.count(">")

    # Giảm giới hạn chiều dài xuống 80 ký tự để bắt kịp code snippet ngắn trong test
    if len(message) > 80 and (has_code_indicator or braces_count > 4):
        return "Yêu cầu không hợp lệ. Hệ thống đã chặn hành vi khai thác mã độc."

    # c. Token Exhaustion / Repetitive patterns
    words = message_lower.split()
    if len(words) > 20:
        word_counts = {}
        for w in words:
            word_counts[w] = word_counts.get(w, 0) + 1
        max_repeats = max(word_counts.values()) if word_counts else 0
        # Một từ lặp lại từ 8 lần trở lên trong câu dài sẽ bị coi là Token Exhaustion
        if max_repeats >= 8:
            return "Yêu cầu không hợp lệ. Hệ thống đã chặn hành vi khai thác mã độc."


    # --- 3. Rule #5: Financial / Legal Liability ---
    # Kiểm tra trực tiếp các từ khóa
    for pattern in RULE_5_DIRECT_KEYWORDS:
        if re.search(pattern, message_lower):
            return "Tôi chỉ hỗ trợ tính toán số liệu kỹ thuật, không có thẩm quyền đưa ra lời khuyên đầu tư hoặc tư vấn pháp lý."

    # Kiểm tra tổ hợp: "đầu tư" đi kèm các tài sản tài chính
    if "đầu tư" in message_lower or "invest" in message_lower:
        financial_assets = ["cổ phiếu", "crypto", "bitcoin", "coin", "chứng khoán", "bất động sản", "đất", "vàng", "forex", "stock"]
        if any(asset in message_lower for asset in financial_assets):
            return "Tôi chỉ hỗ trợ tính toán số liệu kỹ thuật, không có thẩm quyền đưa ra lời khuyên đầu tư hoặc tư vấn pháp lý."

    # Kiểm tra tổ hợp: "lời khuyên", "khuyên", "tư vấn", "gợi ý" đi cùng với "đầu tư", "pháp lý", "luật", "tài chính"
    advice_terms = ["lời khuyên", "khuyên", "tư vấn", "gợi ý", "advice", "consult"]
    liability_sectors = ["đầu tư", "pháp lý", "luật", "tài chính", "invest", "legal", "financial"]
    has_advice = any(term in message_lower for term in advice_terms)
    has_sector = any(sec in message_lower for sec in liability_sectors)
    if has_advice and has_sector:
        return "Tôi chỉ hỗ trợ tính toán số liệu kỹ thuật, không có thẩm quyền đưa ra lời khuyên đầu tư hoặc tư vấn pháp lý."

    return None
