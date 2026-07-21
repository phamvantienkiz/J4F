# Slate Minimalist Chat UI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Nâng cấp cấu phần Chat UI sang Slate Minimalist, phân tách hoàn toàn Thought Process (hiển thị dạng Collapsible nhỏ) khỏi bong bóng trả lời chính, tinh chỉnh typography chuẩn và hiệu ứng cuộn mượt mà.

**Architecture:** Mở rộng kiểu dữ liệu `ChatMessage` để lưu trữ `steps` (mảng tiến trình suy nghĩ) và `isStreaming` riêng biệt. Tại tầng giao diện, render phần Thought Process thành một Accordion độc lập phía trên văn bản chính. Tạo bộ CSS tương đương `@tailwindcss/typography` trong `styles.css`.

**Tech Stack:** React, TypeScript, Pure CSS (trong `styles.css`).

---

### Task 1: Cấu hình kiểu dữ liệu ChatMessage và cập nhật CSS Thought Process

**Files:**
- Modify: `frontend/src/App.tsx:4-9`
- Modify: `frontend/src/styles/styles.css`

- [ ] **Step 1: Cập nhật kiểu ChatMessage trong App.tsx**

Mở rộng `ChatMessage` để hỗ trợ `steps` và `isStreaming`:
```typescript
type ChatMessage = {
  id: string;
  role: "user" | "assistant";
  text: string;
  response?: AgentResponse;
  steps?: Array<{ step: string; message: string }>;
  isStreaming?: boolean;
};
```

- [ ] **Step 2: Định nghĩa CSS cho khối Thought Process tối giản**

Thêm các style sau vào cuối file `frontend/src/styles/styles.css`:
```css
/* Thought Process Block (Collapsible) */
.thought-process-block {
  margin-bottom: 12px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: #f8fafc;
  overflow: hidden;
  transition: max-height 0.3s ease;
}

.thought-process-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 12px;
  background: #f1f5f9;
  cursor: pointer;
  user-select: none;
  font-size: 11px;
  font-weight: 700;
  color: var(--color-text-secondary);
}

.thought-process-header:hover {
  background: #e2e8f0;
}

.thought-process-toggle {
  font-size: 8px;
  transition: transform 0.2s ease;
}

.thought-process-toggle.open {
  transform: rotate(180deg);
}

.thought-process-content {
  padding: 10px 12px;
  display: flex;
  flex-direction: column;
  gap: 6px;
  border-top: 1px solid var(--color-border);
}

.thought-step {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 11px;
  color: var(--color-text-secondary);
  font-weight: 500;
}

.thought-step-dot {
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: #94a3b8;
}

.thought-step.active .thought-step-dot {
  background: var(--color-surface-raised);
  animation: pulse-active 1.2s infinite;
}

@keyframes pulse-active {
  0%, 100% {
    opacity: 0.4;
    transform: scale(0.8);
  }
  50% {
    opacity: 1;
    transform: scale(1.2);
  }
}
```

- [ ] **Step 3: Chạy TypeScript verification**

Chạy lệnh: `npm --prefix frontend run typecheck`
Expected: Biên dịch không có lỗi liên quan đến `ChatMessage`.

---

### Task 2: Cập nhật CSS Typography & Bong bóng Chat Slate Minimalist

**Files:**
- Modify: `frontend/src/styles/styles.css`

- [ ] **Step 1: Thêm lớp Typography `.assistant-prose` tương đương với prose**

Thêm các quy tắc CSS sau vào cuối file `frontend/src/styles/styles.css`:
```css
/* Custom Assistant Prose for Minimalist Markdown Style */
.assistant-prose {
  font-size: 14px;
  line-height: 1.6;
  color: var(--color-text-primary);
}

.assistant-prose p {
  margin: 0 0 12px 0;
}

.assistant-prose p:last-child {
  margin-bottom: 0;
}

.assistant-prose ul, .assistant-prose ol {
  margin: 0 0 12px 0;
  padding-left: 20px;
}

.assistant-prose li {
  margin-bottom: 4px;
}

.assistant-prose strong {
  font-weight: 700;
  color: #0f172a;
}

.assistant-prose hr {
  border: 0;
  border-top: 1px dashed var(--color-border);
  margin: 16px 0;
}

.assistant-prose pre {
  background: #0f172a;
  color: #f8fafc;
  padding: 12px;
  border-radius: var(--radius-md);
  font-family: Consolas, Monaco, monospace;
  font-size: 12px;
  overflow-x: auto;
  margin: 12px 0;
}

.assistant-prose code {
  background: #f1f5f9;
  color: #0f172a;
  padding: 2px 5px;
  border-radius: 4px;
  font-family: Consolas, Monaco, monospace;
  font-size: 12.5px;
}

.assistant-prose pre code {
  background: transparent;
  color: inherit;
  padding: 0;
  border-radius: 0;
  font-size: inherit;
}
```

- [ ] **Step 2: Cập nhật CSS cho Bong bóng Chat Slate Minimalist**

Sửa đổi `.message.user .message-bubble` và `.message.assistant` trong `frontend/src/styles/styles.css`:
```css
/* Replace old styles around line 678-710 */
.message {
  display: flex;
  margin-bottom: 24px;
  animation: soft-enter 240ms ease-out both;
}

.message.user {
  justify-content: flex-end;
}

.message-bubble {
  max-width: min(820px, 96%);
  min-width: 0;
  padding: 16px;
  border-radius: 16px;
}

/* User chat bubble: Dark slate solid color */
.message.user .message-bubble {
  background: #0f172a;
  color: #ffffff;
  border-bottom-right-radius: 4px;
  box-shadow: 0 4px 12px rgba(15, 23, 42, 0.08);
}

/* Assistant chat bubble: borderless, transparent style with fine divider line */
.message.assistant {
  border-bottom: 1px solid var(--color-border);
  padding-bottom: 20px;
}

.message.assistant .message-bubble {
  background: transparent;
  padding-left: 0;
  padding-right: 0;
}
```

- [ ] **Step 3: Chạy build kiểm tra CSS đóng gói**

Chạy lệnh: `npm --prefix frontend run build`
Expected: Build thành công (Exit code 0).

---

### Task 3: Triển khai Component Accordion Thought Process trong React

**Files:**
- Modify: `frontend/src/App.tsx`

- [ ] **Step 1: Tạo Component Accordion Thought Process trong React**

Thêm định nghĩa component `ThoughtProcessContainer` vào `frontend/src/App.tsx` (ví dụ ở trên component `App` hoặc dưới cùng):
```typescript
function ThoughtProcessContainer({
  steps,
  isStreaming,
}: {
  steps: Array<{ step: string; message: string }>;
  isStreaming?: boolean;
}) {
  const [isOpen, setIsOpen] = useState(isStreaming === true);

  // Tự động đồng bộ đóng mở khi đang streaming hoặc kết thúc stream
  useEffect(() => {
    if (isStreaming) {
      setIsOpen(true);
    } else {
      setIsOpen(false);
    }
  }, [isStreaming]);

  if (!steps || steps.length === 0) return null;

  return (
    <div className="thought-process-block">
      <div className="thought-process-header" onClick={() => setIsOpen(!isOpen)}>
        <span>
          {isStreaming
            ? "Đang suy nghĩ..."
            : `Đã hoàn thành suy nghĩ (${steps.length} bước)`}
        </span>
        <span className={isOpen ? "thought-process-toggle open" : "thought-process-toggle"}>
          ▼
        </span>
      </div>
      {isOpen && (
        <div className="thought-process-content">
          {steps.map((item, index) => {
            const isActive = isStreaming && index === steps.length - 1;
            return (
              <div
                key={index}
                className={isActive ? "thought-step active" : "thought-step"}
              >
                <i className="thought-step-dot" />
                <span>{item.message}</span>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Cập nhật hàm Render tin nhắn Assistant trong App.tsx**

Thay đổi phần render tin nhắn trợ lý ở trong luồng `messages.map` tại dòng ~968:
```typescript
{message.role === "assistant" ? (
  <>
    {message.steps && (
      <ThoughtProcessContainer
        steps={message.steps}
        isStreaming={message.isStreaming}
      />
    )}
    {displayMessageText(message) && (
      <div className="assistant-prose">
        <pre>{displayMessageText(message)}</pre>
      </div>
    )}
    {message.response?.data?.items?.length ? (
      <RecommendationAnswerBox
        items={message.response.data.items}
        labels={t}
        onOrder={startOrder}
        onAskPrice={submitSuggestedMessage}
      />
    ) : null}
  </>
) : (
  <pre>{displayMessageText(message)}</pre>
)}
```

- [ ] **Step 3: Chạy TypeScript verification**

Chạy lệnh: `npm --prefix frontend run typecheck`
Expected: PASS.

---

### Task 4: Sửa đổi logic luồng nhận dữ liệu SSE trong App.tsx

**Files:**
- Modify: `frontend/src/App.tsx:693-725` (hàm `submitMessage`)

- [ ] **Step 1: Khởi tạo tin nhắn trợ lý có các trường steps và isStreaming**

Thay đổi cách tạo tin nhắn assistant đầu tiên khi gửi:
```typescript
    const assistantMessageId = crypto.randomUUID();
    const initialAssistantMessage: ChatMessage = {
      id: assistantMessageId,
      role: "assistant",
      text: "",
      steps: [],
      isStreaming: true,
    };
```

- [ ] **Step 2: Cập nhật callback `onChunk` để phân tách `step` và `token`**

Thay thế hoàn toàn callback `onChunk` trong `submitMessage` để cập nhật trạng thái `steps` độc lập:
```typescript
    let currentAssistantText = "";
    let currentAssistantSteps: Array<{ step: string; message: string }> = [];
    let startedStreamingTokens = false;

    const onChunk = (chunk: any) => {
      if (chunk.step && chunk.message) {
        // Cập nhật Thought process steps
        const exists = currentAssistantSteps.some((s) => s.step === chunk.step);
        if (!exists) {
          currentAssistantSteps = [...currentAssistantSteps, { step: chunk.step, message: chunk.message }];
          setMessages((prev) =>
            prev.map((msg) =>
              msg.id === assistantMessageId
                ? { ...msg, steps: currentAssistantSteps }
                : msg
            )
          );
        }
      } else if (chunk.token) {
        if (!startedStreamingTokens) {
          startedStreamingTokens = true;
        }
        currentAssistantText += chunk.token;
        setMessages((prev) =>
          prev.map((msg) =>
            msg.id === assistantMessageId
              ? { ...msg, text: currentAssistantText }
              : msg
          )
        );
      } else if (chunk.session_id && chunk.answer) {
        // Dòng cuối cùng của Stream (kết quả đầy đủ)
        currentAssistantText = chunk.answer;
        setMessages((prev) =>
          prev.map((msg) =>

            msg.id === assistantMessageId
              ? {
                  ...msg,
                  text: currentAssistantText,
                  response: chunk,
                  isStreaming: false, // Dừng stream để Accordion đóng lại
                }

              : msg
          )
        );
        applyAgentResponse(chunk);
      }
    };
```

- [ ] **Step 3: Cập nhật khối `catch` lỗi**

Nếu lỗi, đảm bảo cập nhật trạng thái `isStreaming: false`:
```typescript
    } catch {
      const errorText = String(copy[nextLanguage].apiError);
      setMessages((prev) =>
        prev.map((msg) =>
          msg.id === assistantMessageId
            ? { ...msg, text: errorText, isStreaming: false }
            : msg
        )
      )
      setMessages((finalPrev) => {
        persistChatSession(finalPrev, sessionId, nextLanguage);
        return finalPrev;
      });
    }
```

- [ ] **Step 4: Chạy toàn bộ kiểm thử xác minh biên dịch và kiểm tra kiểu**

Chạy lệnh: `npm --prefix frontend run typecheck && npm --prefix frontend run build`
Expected: Cả hai lệnh chạy thành công không có lỗi.
