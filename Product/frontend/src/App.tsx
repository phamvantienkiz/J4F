import { useState } from 'react';
import { AuthProvider, useAuth } from './context/AuthContext';
import { Sidebar } from './components/Sidebar';
import { ChatArea } from './components/ChatArea';
import { RightPanel } from './components/RightPanel';
import { AuthModal } from './components/AuthModal';
import type { CandidateOption } from './services/api';
import './App.css';

function DashboardContent() {
  const { token, user, loading } = useAuth();
  const [activeConversationId, setActiveConversationId] = useState<string | null>(null);
  const [selectedOption, setSelectedOption] = useState<CandidateOption | null>(null);
  const [selectedProductName, setSelectedProductName] = useState<string | null>(null);
  const [selectedMarket, setSelectedMarket] = useState<string | null>(null);
  const [sidebarRefresh, setSidebarRefresh] = useState<number>(0);

  const handleSelectConversation = (id: string) => {
    setActiveConversationId(id);
    setSelectedOption(null);
    setSelectedProductName(null);
    setSelectedMarket(null);
  };

  const handleSelectOption = (option: CandidateOption, productName: string, market: string) => {
    setSelectedOption(option);
    setSelectedProductName(productName);
    setSelectedMarket(market);
  };

  const triggerSidebarRefresh = () => {
    setSidebarRefresh((prev) => prev + 1);
  };

  if (loading) {
    return (
      <div className="app-loading flex-center flex-col">
        <div className="spinner"></div>
        <span style={{ marginTop: '16px', color: '#94A3B8', fontSize: '14px', fontWeight: 500 }}>
          Đang khởi tạo Burger Agent...
        </span>
      </div>
    );
  }

  if (!token || !user) {
    return <AuthModal />;
  }

  return (
    <div className="dashboard-layout">
      {/* Cột 1: Left Sidebar (20% width) */}
      <div className="col-sidebar">
        <Sidebar
          activeConversationId={activeConversationId}
          onSelectConversation={handleSelectConversation}
          refreshTrigger={sidebarRefresh}
        />
      </div>

      {/* Cột 2: Center Panel (50% width) */}
      <div className="col-chat">
        <ChatArea
          conversationId={activeConversationId}
          onSelectOption={handleSelectOption}
          onNewMessageSent={triggerSidebarRefresh}
        />
      </div>

      {/* Cột 3: Right Panel (30% width) */}
      <div className="col-checkout">
        <RightPanel
          conversationId={activeConversationId}
          selectedOption={selectedOption}
          productName={selectedProductName}
          market={selectedMarket}
          onOrderCreated={triggerSidebarRefresh}
        />
      </div>
    </div>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <DashboardContent />
    </AuthProvider>
  );
}
