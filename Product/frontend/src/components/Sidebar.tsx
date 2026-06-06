import React, { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { chatApi } from '../services/api';
import type { ConversationResponse } from '../services/api';
import { PreferencesModal } from './PreferencesModal';
import { Plus, MessageSquare, LogOut, Settings, User, Terminal, Calendar } from 'lucide-react';
import './Sidebar.css';

interface SidebarProps {
  activeConversationId: string | null;
  onSelectConversation: (id: string) => void;
  refreshTrigger: number;
}

export const Sidebar: React.FC<SidebarProps> = ({
  activeConversationId,
  onSelectConversation,
  refreshTrigger,
}) => {
  const { user, logout } = useAuth();
  const [conversations, setConversations] = useState<ConversationResponse[]>([]);
  const [isPrefOpen, setIsPrefOpen] = useState<boolean>(false);
  const [loading, setLoading] = useState<boolean>(false);

  const fetchConversations = async () => {
    try {
      const data = await chatApi.listConversations();
      setConversations(data);
    } catch (error) {
      console.error('Failed to fetch conversations', error);
    }
  };

  useEffect(() => {
    fetchConversations();
  }, [refreshTrigger]);

  const handleNewChat = async () => {
    if (loading) return;
    try {
      setLoading(true);
      const newConv = await chatApi.createConversation();
      setConversations((prev) => [newConv, ...prev]);
      onSelectConversation(newConv.id);
    } catch (error) {
      console.error('Failed to create new chat', error);
    } finally {
      setLoading(false);
    }
  };

  // Helper to group conversations by date
  const groupConversations = (list: ConversationResponse[]) => {
    const today: ConversationResponse[] = [];
    const yesterday: ConversationResponse[] = [];
    const thisWeek: ConversationResponse[] = [];
    const older: ConversationResponse[] = [];

    const now = new Date();
    const startOfToday = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    const startOfYesterday = new Date(startOfToday.getTime() - 24 * 60 * 60 * 1000);
    const startOfWeek = new Date(startOfToday.getTime() - 7 * 24 * 60 * 60 * 1000);

    list.forEach((conv) => {
      const updatedDate = new Date(conv.updated_at);
      if (updatedDate >= startOfToday) {
        today.push(conv);
      } else if (updatedDate >= startOfYesterday) {
        yesterday.push(conv);
      } else if (updatedDate >= startOfWeek) {
        thisWeek.push(conv);
      } else {
        older.push(conv);
      }
    });

    return { today, yesterday, thisWeek, older };
  };

  const groups = groupConversations(conversations);

  const renderConversationItem = (conv: ConversationResponse) => {
    const isActive = conv.id === activeConversationId;
    return (
      <button
        key={conv.id}
        type="button"
        className={`session-item flex-center ${isActive ? 'active' : ''}`}
        onClick={() => onSelectConversation(conv.id)}
      >
        <MessageSquare size={15} className="session-icon" />
        <span className="session-title">{conv.title}</span>
      </button>
    );
  };

  return (
    <aside className="sidebar glass flex-col">
      {/* Header logo */}
      <div className="sidebar-header flex-center">
        <Terminal className="sidebar-logo-icon" />
        <h2 className="sidebar-logo-text text-gradient-secondary">Burger Agent</h2>
      </div>

      {/* New chat button */}
      <div className="sidebar-action">
        <button
          type="button"
          className="new-chat-btn flex-center glow-secondary"
          onClick={handleNewChat}
          disabled={loading}
        >
          <Plus size={16} style={{ marginRight: '6px' }} />
          Hội Thoại Mới
        </button>
      </div>

      {/* Conversation history list */}
      <div className="sidebar-history-container">
        {conversations.length === 0 ? (
          <div className="history-empty">Chưa có cuộc hội thoại nào.</div>
        ) : (
          <div className="history-groups">
            {groups.today.length > 0 && (
              <div className="history-group">
                <div className="group-label flex-center">
                  <Calendar size={10} style={{ marginRight: '4px' }} />
                  Hôm nay
                </div>
                {groups.today.map(renderConversationItem)}
              </div>
            )}

            {groups.yesterday.length > 0 && (
              <div className="history-group">
                <div className="group-label flex-center">
                  <Calendar size={10} style={{ marginRight: '4px' }} />
                  Hôm qua
                </div>
                {groups.yesterday.map(renderConversationItem)}
              </div>
            )}

            {groups.thisWeek.length > 0 && (
              <div className="history-group">
                <div className="group-label flex-center">
                  <Calendar size={10} style={{ marginRight: '4px' }} />
                  7 ngày trước
                </div>
                {groups.thisWeek.map(renderConversationItem)}
              </div>
            )}

            {groups.older.length > 0 && (
              <div className="history-group">
                <div className="group-label flex-center">
                  <Calendar size={10} style={{ marginRight: '4px' }} />
                  Cũ hơn
                </div>
                {groups.older.map(renderConversationItem)}
              </div>
            )}
          </div>
        )}
      </div>

      {/* User profile & actions */}
      <div className="sidebar-footer">
        <div className="user-profile flex-center">
          <div className="avatar flex-center">
            <User size={16} />
          </div>
          <div className="user-info">
            <div className="store-name">{user?.store_name || 'My POD Store'}</div>
            <div className="user-email">{user?.email}</div>
          </div>
        </div>

        <div className="sidebar-footer-actions">
          <button
            type="button"
            className="footer-btn flex-center"
            onClick={() => setIsPrefOpen(true)}
            title="Cài đặt sở thích"
          >
            <Settings size={16} />
            <span>Cài Đặt</span>
          </button>
          <button
            type="button"
            className="footer-btn flex-center logout"
            onClick={logout}
            title="Đăng xuất"
          >
            <LogOut size={16} />
            <span>Đăng Xuất</span>
          </button>
        </div>
      </div>

      {/* Config preferences modal */}
      <PreferencesModal isOpen={isPrefOpen} onClose={() => setIsPrefOpen(false)} />
    </aside>
  );
};
