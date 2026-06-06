import axios from 'axios';

// Get base URL for FastAPI backend
const API_BASE_URL = 'http://localhost:8000';

const api = axios.create({
  baseURL: `${API_BASE_URL}/api/v1`,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor to attach JWT token
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('burger_agent_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor to handle token expiration/unauthorized
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response && error.response.status === 401) {
      // Clear token and redirect to login if unauthorized
      localStorage.removeItem('burger_agent_token');
      // If we are in the browser, we can dispatch a custom event or trigger state change
      window.dispatchEvent(new Event('auth-unauthorized'));
    }
    return Promise.reject(error);
  }
);

export interface UserResponse {
  id: string;
  email: string;
  store_name: string | null;
  created_at: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
}

export interface PreferenceResponse {
  preferred_market: string;
  target_margin: number;
  max_shipping_days: number;
  fulfillment_priority: string;
  updated_at: string;
}

export interface PreferenceUpdate {
  preferred_market?: string;
  target_margin?: number;
  max_shipping_days?: number;
  fulfillment_priority?: string;
}

export interface ConversationResponse {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
}

export interface CandidateOption {
  option_id: string;
  factory_name: string;
  factory_location: string;
  base_cost: number;
  printing_cost: number;
  shipping_cost: number;
  tax_cost: number;
  landed_cost: number;
  margin_percentage: number;
  delivery_days_min: number;
  delivery_days_max: number;
  sla_risk_score: number;
}

export interface MessageMetadata {
  comparison_table?: CandidateOption[];
  product_name?: string;
  market?: string;
}

export interface MessageResponse {
  id: string;
  sender: 'user' | 'assistant';
  content: string;
  metadata: MessageMetadata | null;
  created_at: string;
}

export interface ChatHistoryResponse {
  conversation: ConversationResponse;
  messages: MessageResponse[];
}

export interface OrderAddress {
  full_name: string;
  address_line1: string;
  address_line2?: string;
  city: string;
  state: string;
  zip_code: string;
  country: string;
  phone?: string;
}

export interface OrderHistoryResponse {
  id: string;
  order_id: string;
  sku: string;
  quantity: number;
  total_cost: number;
  shipping_address: OrderAddress;
  tracking_number: string | null;
  status: string;
  created_at: string;
}

export const authApi = {
  register: async (email: string, password: string, storeName?: string): Promise<TokenResponse> => {
    const response = await api.post<TokenResponse>('/auth/register', {
      email,
      password,
      store_name: storeName || null,
    });
    return response.data;
  },

  login: async (email: string, password: string): Promise<TokenResponse> => {
    const response = await api.post<TokenResponse>('/auth/login', {
      email,
      password,
    });
    return response.data;
  },

  getMe: async (): Promise<UserResponse> => {
    const response = await api.get<UserResponse>('/auth/me');
    return response.data;
  },

  getPreference: async (): Promise<PreferenceResponse> => {
    const response = await api.get<PreferenceResponse>('/auth/preference');
    return response.data;
  },

  updatePreference: async (pref: PreferenceUpdate): Promise<PreferenceResponse> => {
    const response = await api.put<PreferenceResponse>('/auth/preference', pref);
    return response.data;
  },
};

export const chatApi = {
  listConversations: async (): Promise<ConversationResponse[]> => {
    const response = await api.get<ConversationResponse[]>('/chat/conversations');
    return response.data;
  },

  createConversation: async (title?: string): Promise<ConversationResponse> => {
    const response = await api.post<ConversationResponse>('/chat/conversations', null, {
      params: title ? { title } : {},
    });
    return response.data;
  },

  getHistory: async (conversationId: string): Promise<ChatHistoryResponse> => {
    const response = await api.get<ChatHistoryResponse>(`/chat/conversations/${conversationId}/history`);
    return response.data;
  },

  sendMessage: async (conversationId: string, content: string): Promise<ChatHistoryResponse> => {
    const response = await api.post<ChatHistoryResponse>(
      `/chat/conversations/${conversationId}/message`,
      { content }
    );
    return response.data;
  },
};

export const orderApi = {
  confirmOrder: async (
    threadId: string,
    sku: string,
    quantity: number,
    shippingAddress: OrderAddress,
    selectedOptionId: string
  ): Promise<OrderHistoryResponse> => {
    const response = await api.post<OrderHistoryResponse>('/order/confirm', {
      thread_id: threadId,
      sku,
      quantity,
      shipping_address: shippingAddress,
      selected_option_id: selectedOptionId,
    });
    return response.data;
  },

  listOrders: async (): Promise<OrderHistoryResponse[]> => {
    const response = await api.get<OrderHistoryResponse[]>('/order/history');
    return response.data;
  },

  getOrderTracking: async (orderId: string): Promise<any> => {
    const response = await api.get(`/order/${orderId}/tracking`);
    return response.data;
  },
};

export default api;
