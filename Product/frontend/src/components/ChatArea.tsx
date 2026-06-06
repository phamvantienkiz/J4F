import React, { useState, useEffect, useRef } from 'react';
import { chatApi } from '../services/api';
import type { MessageResponse, CandidateOption } from '../services/api';
import { Send, Sparkles, AlertCircle, RefreshCw } from 'lucide-react';
import './ChatArea.css';

interface ChatAreaProps {
  conversationId: string | null;
  onSelectOption: (option: CandidateOption, productName: string, market: string) => void;
  onNewMessageSent: () => void;
}

export const ChatArea: React.FC<ChatAreaProps> = ({
  conversationId,
  onSelectOption,
  onNewMessageSent,
}) => {
  const [messages, setMessages] = useState<MessageResponse[]>([]);
  const [inputText, setInputText] = useState<string>('');
  const [loading, setLoading] = useState<boolean>(false);
  const [fetching, setFetching] = useState<boolean>(false);
  const [error, setError] = useState<string>('');
  
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, loading]);

  // Load chat history
  const loadHistory = async (id: string) => {
    try {
      setFetching(true);
      setError('');
      const data = await chatApi.getHistory(id);
      setMessages(data.messages);
    } catch (err: any) {
      console.error(err);
      setError('Không thể tải lịch sử trò chuyện. Vui lòng thử lại.');
    } finally {
      setFetching(false);
    }
  };

  useEffect(() => {
    if (conversationId) {
      loadHistory(conversationId);
    } else {
      setMessages([]);
    }
  }, [conversationId]);

  const handleSendMessage = async (textToSend: string) => {
    if (!conversationId || !textToSend.trim() || loading) return;
    
    const text = textToSend.trim();
    setInputText('');
    setError('');
    
    // Add optimistic user message to UI
    const tempUserMsg: MessageResponse = {
      id: Math.random().toString(),
      sender: 'user',
      content: text,
      metadata: null,
      created_at: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, tempUserMsg]);
    
    try {
      setLoading(true);
      const data = await chatApi.sendMessage(conversationId, text);
      setMessages(data.messages);
      onNewMessageSent(); // Notify sidebar to refresh titles
    } catch (err: any) {
      console.error(err);
      setError('Đã xảy ra lỗi khi gửi tin nhắn. Vui lòng kiểm tra lại backend.');
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    handleSendMessage(inputText);
  };

  // Suggestion chips
  const suggestionChips = [
    'Tìm T-shirt đen gửi đi US',
    'So sánh Hoodie các xưởng ship EU rẻ nhất',
    'Tìm áo thun margin tối thiểu 45%',
    'Tìm Cốc sứ ship VN nhanh nhất',
  ];

  // Helper to parse simple markdown (bold, list, bullet points, paragraph, newlines)
  const renderFormattedContent = (content: string) => {
    const lines = content.split('\n');
    return lines.map((line, idx) => {
      let trimmed = line.trim();
      
      // Headers
      if (trimmed.startsWith('### ')) {
        return <h4 key={idx} className="chat-h4">{trimmed.replace('### ', '')}</h4>;
      }
      if (trimmed.startsWith('## ')) {
        return <h3 key={idx} className="chat-h3">{trimmed.replace('## ', '')}</h3>;
      }
      if (trimmed.startsWith('# ')) {
        return <h2 key={idx} className="chat-h2">{trimmed.replace('# ', '')}</h2>;
      }
      
      // Bullets
      if (trimmed.startsWith('- ') || trimmed.startsWith('* ')) {
        return (
          <li key={idx} className="chat-bullet">
            {parseInlineMarkdown(trimmed.substring(2))}
          </li>
        );
      }

      // Order list
      if (/^\d+\.\s/.test(trimmed)) {
        const text = trimmed.replace(/^\d+\.\s/, '');
        return (
          <div key={idx} className="chat-order-list">
            <span className="order-num">{trimmed.match(/^\d+/)![0]}.</span>
            <span className="order-text">{parseInlineMarkdown(text)}</span>
          </div>
        );
      }

      // Ignore tables in text since we render them from metadata comparison_table
      if (trimmed.startsWith('|')) {
        return null;
      }

      return (
        <p key={idx} className="chat-para">
          {parseInlineMarkdown(line)}
        </p>
      );
    });
  };

  // Parse bold ** and inline code `
  const parseInlineMarkdown = (text: string) => {
    if (!text) return '';
    
    // Split by **
    const parts = text.split(/\*\*([^*]+)\*\*/g);
    return parts.map((part, i) => {
      // Bold parts are at odd indices
      if (i % 2 === 1) {
        return <strong key={i}>{parseCodeMarkdown(part)}</strong>;
      }
      return parseCodeMarkdown(part);
    });
  };

  const parseCodeMarkdown = (text: string) => {
    const parts = text.split(/`([^`]+)`/g);
    return parts.map((part, i) => {
      // Code parts are at odd indices
      if (i % 2 === 1) {
        return <code key={i} className="inline-code">{part}</code>;
      }
      return part;
    });
  };

  // Render Candidates Comparison Table
  const renderComparisonTable = (options: CandidateOption[], productName: string, market: string) => {
    return (
      <div className="comparison-table-container glass-card">
        <div className="table-header-desc flex-center">
          <Sparkles size={14} className="sparkle-icon" />
          <span>Bảng so sánh tối ưu cho {productName} ({market})</span>
        </div>
        <div className="table-wrapper">
          <table>
            <thead>
              <tr>
                <th>Nhà in / Xưởng</th>
                <th>Base Cost</th>
                <th>Print Cost</th>
                <th>Shipping</th>
                <th>Tax</th>
                <th>Landed Cost</th>
                <th>Margin</th>
                <th>Ship SLA</th>
                <th>Rủi ro SLA</th>
                <th>Hành động</th>
              </tr>
            </thead>
            <tbody>
              {options.map((opt, i) => {
                const isBest = i === 0;
                return (
                  <tr key={opt.option_id} className={isBest ? 'best-option-row' : ''}>
                    <td>
                      <div className="factory-cell">
                        <span className="factory-name">{opt.factory_name}</span>
                        <span className="factory-loc">({opt.factory_location})</span>
                        {isBest && <span className="recommended-badge pulse-indicator">RECOMMENDED</span>}
                      </div>
                    </td>
                    <td>${opt.base_cost.toFixed(2)}</td>
                    <td>${opt.printing_cost.toFixed(2)}</td>
                    <td>${opt.shipping_cost.toFixed(2)}</td>
                    <td>${opt.tax_cost.toFixed(2)}</td>
                    <td className="landed-cost-cell">${opt.landed_cost.toFixed(2)}</td>
                    <td className="margin-cell">{opt.margin_percentage.toFixed(1)}%</td>
                    <td>{opt.delivery_days_min}-{opt.delivery_days_max} ngày</td>
                    <td>
                      <span className={`risk-badge ${opt.sla_risk_score > 30 ? 'risk-high' : 'risk-low'}`}>
                        {opt.sla_risk_score.toFixed(0)} (Thấp)
                      </span>
                    </td>
                    <td>
                      <button
                        type="button"
                        className={`select-option-btn ${isBest ? 'best-btn' : ''}`}
                        onClick={() => onSelectOption(opt, productName, market)}
                      >
                        Chọn Xưởng
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    );
  };

  return (
    <div className="chat-area flex-col">
      {/* Top Header */}
      <div className="chat-header flex-center">
        <div>
          <h3>Trợ Lý Tư Vấn Fulfillment</h3>
          <p className="chat-subtitle">
            {conversationId ? 'Hội thoại đang hoạt động' : 'Chọn cuộc hội thoại hoặc tạo mới để bắt đầu'}
          </p>
        </div>
      </div>

      {/* Main chat log */}
      <div className="chat-messages">
        {fetching ? (
          <div className="chat-loading flex-center">
            <RefreshCw className="spinner-icon spin-slow" />
            <span>Đang tải lịch sử...</span>
          </div>
        ) : messages.length === 0 ? (
          <div className="chat-welcome flex-center flex-col">
            <Sparkles className="welcome-sparkle" />
            <h2>Chào mừng bạn đến với Burger Agent!</h2>
            <p>
              Tôi là trợ lý trí tuệ nhân tạo hỗ trợ bạn lọc catalog, tối ưu landed cost và SLA vận chuyển, sau đó đẩy đơn lên BurgerPrints qua API.
            </p>
            <div className="welcome-suggest-title">Bạn có thể hỏi tôi:</div>
            <div className="welcome-suggestions">
              {suggestionChips.map((chip, idx) => (
                <button
                  key={idx}
                  type="button"
                  className="welcome-suggest-btn"
                  onClick={() => {
                    if (conversationId) {
                      handleSendMessage(chip);
                    } else {
                      setError('Vui lòng tạo hoặc chọn một cuộc hội thoại ở Sidebar trước.');
                    }
                  }}
                >
                  {chip}
                </button>
              ))}
            </div>
          </div>
        ) : (
          <div className="chat-log">
            {messages.map((msg) => {
              const isAssistant = msg.sender === 'assistant';
              const hasTable = isAssistant && 
                msg.metadata && 
                msg.metadata.comparison_table && 
                msg.metadata.comparison_table.length > 0;
              return (
                <div key={msg.id} className={`chat-bubble-container ${msg.sender} ${hasTable ? 'has-table-container' : ''}`}>
                  <div className={`chat-bubble ${msg.sender} ${hasTable ? 'has-table' : ''}`}>
                    <div className="bubble-content">
                      {renderFormattedContent(msg.content)}
                    </div>
                    
                    {/* Render table if presents in metadata */}
                    {isAssistant && 
                      msg.metadata && 
                      msg.metadata.comparison_table && 
                      msg.metadata.comparison_table.length > 0 && 
                      renderComparisonTable(
                        msg.metadata.comparison_table,
                        msg.metadata.product_name || 'Sản phẩm',
                        msg.metadata.market || 'US'
                      )
                    }
                    
                    <div className="bubble-time">
                      {new Date(msg.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                    </div>
                  </div>
                </div>
              );
            })}
            
            {loading && (
              <div className="chat-bubble-container assistant">
                <div className="chat-bubble assistant typing-bubble">
                  <span className="typing-dot"></span>
                  <span className="typing-dot"></span>
                  <span className="typing-dot"></span>
                </div>
              </div>
            )}

            {error && (
              <div className="chat-error-message flex-center">
                <AlertCircle size={16} />
                <span>{error}</span>
              </div>
            )}
            
            <div ref={messagesEndRef} />
          </div>
        )}
      </div>

      {/* Suggestion Chips (sticky in active chat) */}
      {conversationId && messages.length > 0 && (
        <div className="active-suggestions flex-center">
          {suggestionChips.map((chip, idx) => (
            <button
              key={idx}
              type="button"
              className="suggestion-chip"
              onClick={() => handleSendMessage(chip)}
              disabled={loading}
            >
              {chip}
            </button>
          ))}
        </div>
      )}

      {/* Input box */}
      <div className="chat-input-container">
        <form onSubmit={handleSubmit} className="chat-form-input glass glow-secondary">
          <input
            type="text"
            placeholder={
              conversationId
                ? 'Nhập câu hỏi của bạn (ví dụ: Tìm Hoodie ship EU rẻ nhất)...'
                : 'Vui lòng chọn cuộc hội thoại ở Sidebar để bắt đầu chat...'
            }
            value={inputText}
            onChange={(e) => setInputText(e.target.value)}
            disabled={!conversationId || loading}
          />
          <button
            type="submit"
            className="send-btn flex-center"
            disabled={!conversationId || !inputText.trim() || loading}
          >
            <Send size={16} />
          </button>
        </form>
      </div>
    </div>
  );
};
