import React, { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { X, Settings, Target, Truck, ShieldAlert, Globe } from 'lucide-react';
import './PreferencesModal.css';

interface PreferencesModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const PreferencesModal: React.FC<PreferencesModalProps> = ({ isOpen, onClose }) => {
  const { preferences, updatePreferences } = useAuth();
  
  // Local state
  const [preferredMarket, setPreferredMarket] = useState<string>('US');
  const [targetMargin, setTargetMargin] = useState<number>(40.0);
  const [maxShippingDays, setMaxShippingDays] = useState<number>(7);
  const [fulfillmentPriority, setFulfillmentPriority] = useState<string>('margin');
  
  const [loading, setLoading] = useState<boolean>(false);
  const [success, setSuccess] = useState<boolean>(false);
  const [error, setError] = useState<string>('');

  // Sync state with global preferences when modal opens
  useEffect(() => {
    if (preferences) {
      setPreferredMarket(preferences.preferred_market);
      setTargetMargin(preferences.target_margin);
      setMaxShippingDays(preferences.max_shipping_days);
      setFulfillmentPriority(preferences.fulfillment_priority);
    }
  }, [preferences, isOpen]);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setSuccess(false);
    setLoading(true);

    if (targetMargin <= 0 || targetMargin >= 100) {
      setError('Target Margin phải nằm trong khoảng 1% - 99%.');
      setLoading(false);
      return;
    }

    if (maxShippingDays <= 0) {
      setError('Số ngày vận chuyển tối đa phải lớn hơn 0.');
      setLoading(false);
      return;
    }

    try {
      await updatePreferences({
        preferred_market: preferredMarket,
        target_margin: targetMargin,
        max_shipping_days: maxShippingDays,
        fulfillment_priority: fulfillmentPriority,
      });
      setSuccess(true);
      setTimeout(() => {
        setSuccess(false);
        onClose();
      }, 1000);
    } catch (err: any) {
      console.error(err);
      setError('Không thể cập nhật cấu hình. Vui lòng thử lại.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="pref-overlay flex-center">
      <div className="pref-container glass glow-secondary">
        <div className="pref-header">
          <div className="pref-title-area">
            <Settings className="pref-icon spin-slow" />
            <h3>Cài Đặt Cấu Hình Seller</h3>
          </div>
          <button type="button" className="close-btn flex-center" onClick={onClose}>
            <X size={18} />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="pref-form">
          {error && <div className="pref-error">{error}</div>}
          {success && <div className="pref-success">Đã cập nhật cấu hình thành công!</div>}

          <div className="pref-group">
            <label htmlFor="market-select">
              <Globe size={14} style={{ marginRight: '6px' }} />
              Thị Trường Ưu Tiên
            </label>
            <select
              id="market-select"
              value={preferredMarket}
              onChange={(e) => setPreferredMarket(e.target.value)}
              disabled={loading}
            >
              <option value="US">Mỹ (US)</option>
              <option value="EU">Châu Âu (EU)</option>
              <option value="VN">Việt Nam (VN)</option>
            </select>
            <span className="pref-desc">Thị trường mặc định được chọn khi tìm kiếm catalog và tính cước vận chuyển.</span>
          </div>

          <div className="pref-group">
            <label htmlFor="margin-input">
              <Target size={14} style={{ marginRight: '6px' }} />
              Lợi Nhuận Mục Tiêu (Target Margin %)
            </label>
            <div className="pref-input-wrapper">
              <input
                id="margin-input"
                type="number"
                step="0.1"
                min="1"
                max="99"
                value={targetMargin}
                onChange={(e) => setTargetMargin(parseFloat(e.target.value))}
                disabled={loading}
              />
              <span className="unit">%</span>
            </div>
            <span className="pref-desc">Dùng để tự động tính toán đề xuất giá bán lẻ tối ưu từ Landed Cost.</span>
          </div>

          <div className="pref-group">
            <label htmlFor="shipping-input">
              <Truck size={14} style={{ marginRight: '6px' }} />
              Thời Gian Ship Tối Đa (SLA)
            </label>
            <div className="pref-input-wrapper">
              <input
                id="shipping-input"
                type="number"
                min="1"
                value={maxShippingDays}
                onChange={(e) => setMaxShippingDays(parseInt(e.target.value))}
                disabled={loading}
              />
              <span className="unit">ngày</span>
            </div>
            <span className="pref-desc">Thời gian giao hàng tối đa chấp nhận để đánh giá SLA Risk Score.</span>
          </div>

          <div className="pref-group">
            <label htmlFor="priority-select">
              <ShieldAlert size={14} style={{ marginRight: '6px' }} />
              Tiêu Chí Ưu Tiên
            </label>
            <select
              id="priority-select"
              value={fulfillmentPriority}
              onChange={(e) => setFulfillmentPriority(e.target.value)}
              disabled={loading}
            >
              <option value="margin">Tối ưu Lợi Nhuận (Margin)</option>
              <option value="speed">Tối ưu Tốc độ ship (Speed)</option>
            </select>
            <span className="pref-desc">Thuật toán AI của Agent sẽ ưu tiên tiêu chí này khi sắp xếp xếp hạng xưởng.</span>
          </div>

          <div className="pref-actions">
            <button type="button" className="cancel-btn" onClick={onClose} disabled={loading}>
              Hủy
            </button>
            <button type="submit" className="save-btn" disabled={loading}>
              {loading ? 'Đang Lưu...' : 'Lưu Thay Đổi'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
