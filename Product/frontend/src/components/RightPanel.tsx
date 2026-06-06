import React, { useState, useEffect } from 'react';
import { orderApi } from '../services/api';
import type { CandidateOption, OrderAddress } from '../services/api';
import { ShoppingCart, CheckCircle, Package, MapPin, CreditCard, Sparkles } from 'lucide-react';
import confetti from 'canvas-confetti';
import './RightPanel.css';

interface RightPanelProps {
  conversationId: string | null;
  selectedOption: CandidateOption | null;
  productName: string | null;
  market: string | null;
  onOrderCreated: () => void;
}

export const RightPanel: React.FC<RightPanelProps> = ({
  conversationId,
  selectedOption,
  productName,
  market,
  onOrderCreated,
}) => {
  // Input fields
  const [fullName, setFullName] = useState<string>('John Doe');
  const [addressLine1, setAddressLine1] = useState<string>('123 Main St');
  const [city, setCity] = useState<string>('San Jose');
  const [stateName, setStateName] = useState<string>('CA');
  const [zipCode, setZipCode] = useState<string>('95112');
  const [country, setCountry] = useState<string>('US');
  const [quantity, setQuantity] = useState<number>(1);
  const [selectedColor, setSelectedColor] = useState<string>('Black');
  const [selectedSize, setSelectedSize] = useState<string>('L');

  // Order status
  const [loading, setLoading] = useState<boolean>(false);
  const [orderResult, setOrderResult] = useState<any | null>(null);
  const [error, setError] = useState<string>('');

  // Sync country with market
  useEffect(() => {
    if (market) {
      setCountry(market);
      // Sensible default addresses for VN, EU, US
      if (market === 'VN') {
        setFullName('Phạm Văn Tiến');
        setAddressLine1('123 Đường Lê Lợi');
        setCity('Quận 1, HCMC');
        setStateName('Hồ Chí Minh');
        setZipCode('70000');
      } else if (market === 'EU') {
        setFullName('Hans Schmidt');
        setAddressLine1('Friedrichstraße 12');
        setCity('Berlin');
        setStateName('Berlin');
        setZipCode('10117');
      } else {
        setFullName('John Doe');
        setAddressLine1('123 Main St');
        setCity('San Jose');
        setStateName('CA');
        setZipCode('95112');
      }
    }
  }, [market, selectedOption]);

  // Reset order state when product/option changes
  useEffect(() => {
    setOrderResult(null);
    setError('');
  }, [selectedOption]);

  // Determine SKU based on product and selection
  const getSKU = () => {
    if (!productName) return 'BP-UNISEX-TSHIRT-BLK-L';
    const cleanProd = productName.toLowerCase();
    
    let colorCode = selectedColor.substring(0, 3).toUpperCase();
    let sizeCode = selectedSize.toUpperCase();

    if (cleanProd.includes('hoodie')) {
      return `BP-FLEECE-HOODIE-${colorCode}-${sizeCode}`;
    } else if (cleanProd.includes('mug')) {
      return `BP-CERAMIC-MUG-WHT-STD`;
    }
    return `BP-UNISEX-TSHIRT-${colorCode}-${sizeCode}`;
  };

  const handleConfirmOrder = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!conversationId || !selectedOption || loading) return;

    setError('');
    setLoading(true);

    if (!fullName || !addressLine1 || !city || !stateName || !zipCode) {
      setError('Vui lòng nhập đầy đủ thông tin giao hàng.');
      setLoading(false);
      return;
    }

    const shippingAddress: OrderAddress = {
      full_name: fullName,
      address_line1: addressLine1,
      city,
      state: stateName,
      zip_code: zipCode,
      country,
    };

    try {
      const sku = getSKU();
      const res = await orderApi.confirmOrder(
        conversationId,
        sku,
        quantity,
        shippingAddress,
        selectedOption.option_id
      );
      
      setOrderResult(res);
      
      // Trigger canvas confetti celebration!
      confetti({
        particleCount: 120,
        spread: 70,
        origin: { y: 0.6 }
      });

      onOrderCreated(); // Trigger reload of orders if needed
    } catch (err: any) {
      console.error(err);
      if (err.response && err.response.data && err.response.data.detail) {
        setError(err.response.data.detail);
      } else {
        setError('Không thể tạo đơn hàng. Vui lòng kiểm tra kết nối.');
      }
    } finally {
      setLoading(false);
    }
  };

  // Render Premium Mockup Vector
  const renderProductMockup = () => {
    const isMug = productName?.toLowerCase().includes('mug');
    const isHoodie = productName?.toLowerCase().includes('hoodie');

    // Hex mapping based on selected color label
    const colorMap: { [key: string]: string } = {
      Black: '#0b0f19',
      White: '#f8fafc',
      Navy: '#1e293b',
      Grey: '#64748b',
      Red: '#dc2626',
    };
    
    const svgColor = colorMap[selectedColor] || '#0b0f19';

    if (isMug) {
      return (
        <svg viewBox="0 0 100 100" className="mockup-svg">
          {/* Ceramic Mug shape */}
          <rect x="30" y="25" width="40" height="50" rx="4" fill={svgColor} stroke="#475569" strokeWidth="1.5" />
          <path d="M70,35 C78,35 80,42 80,50 C80,58 78,65 70,65" fill="none" stroke={svgColor} strokeWidth="6" strokeLinecap="round" />
          <ellipse cx="50" cy="25" rx="20" ry="4" fill="#334155" />
          <text x="50" y="55" fontSize="6" fill={selectedColor === 'White' ? '#334155' : '#FFF'} textAnchor="middle" fontWeight="bold" fontFamily="monospace">
            BURGER AGENT
          </text>
        </svg>
      );
    }

    if (isHoodie) {
      return (
        <svg viewBox="0 0 100 100" className="mockup-svg">
          {/* Hoodie Body and Hood */}
          <path d="M25,20 L35,23 L40,15 L60,15 L65,23 L75,20 L80,55 L70,55 L70,80 L30,80 L30,55 L20,55 Z" fill={svgColor} stroke="#475569" strokeWidth="1.5" />
          <path d="M40,15 C40,7 60,7 60,15" fill="none" stroke="#475569" strokeWidth="1.5" />
          {/* Cords */}
          <line x1="48" y1="20" x2="48" y2="35" stroke="#94a3b8" strokeWidth="1" />
          <line x1="52" y1="20" x2="52" y2="35" stroke="#94a3b8" strokeWidth="1" />
          {/* Pocket */}
          <path d="M38,62 L62,62 L58,74 L42,74 Z" fill="none" stroke="#475569" strokeWidth="1.2" />
        </svg>
      );
    }

    // Default T-Shirt shape
    return (
      <svg viewBox="0 0 100 100" className="mockup-svg">
        <path d="M35,12 C40,14 45,15 50,15 C55,15 60,14 65,12 L82,22 L72,35 L68,33 L68,85 L32,85 L32,33 L28,35 L18,22 Z" fill={svgColor} stroke="#475569" strokeWidth="1.5" />
        <text x="50" y="50" fontSize="7" fill={selectedColor === 'White' ? '#334155' : '#FFF'} textAnchor="middle" fontWeight="bold" fontFamily="monospace">
          BURGER
        </text>
      </svg>
    );
  };

  const hasMug = productName?.toLowerCase().includes('mug');
  const availableColors = hasMug ? ['White'] : ['Black', 'White', 'Navy', 'Grey', 'Red'];
  const availableSizes = hasMug ? ['Standard'] : ['S', 'M', 'L', 'XL', '2XL'];

  if (!selectedOption) {
    return (
      <aside className="right-panel glass flex-center flex-col empty-panel">
        <ShoppingCart size={32} className="empty-cart-icon" />
        <h4>Chi Tiết Fulfillment & Checkout</h4>
        <p>Vui lòng click nút **"Chọn Xưởng"** trên bảng so sánh tại chat để bắt đầu tạo đơn hàng.</p>
      </aside>
    );
  }

  // Cost calculations
  const totalBase = selectedOption.base_cost * quantity;
  const totalPrint = selectedOption.printing_cost * quantity;
  const totalShip = selectedOption.shipping_cost * quantity;
  const totalTax = selectedOption.tax_cost * quantity;
  const totalLandedCost = selectedOption.landed_cost * quantity;

  return (
    <aside className="right-panel glass flex-col">
      {orderResult ? (
        // Successful Checkout display
        <div className="checkout-success-view flex-center flex-col">
          <CheckCircle className="success-icon pulse-indicator" />
          <h3 className="text-gradient-primary">Đặt Đơn Thành Công!</h3>
          <p className="success-sub">Đơn hàng đã được ghi nhận trên hệ thống sandbox BurgerPrints API v2.0.</p>
          
          <div className="success-details glass-card">
            <div className="detail-row">
              <span className="label">Order ID:</span>
              <span className="value code-val">{orderResult.order_id}</span>
            </div>
            <div className="detail-row">
              <span className="label">SKU:</span>
              <span className="value code-val">{orderResult.sku}</span>
            </div>
            <div className="detail-row">
              <span className="label">Số lượng:</span>
              <span className="value">{orderResult.quantity}</span>
            </div>
            <div className="detail-row">
              <span className="label">Tổng chi phí:</span>
              <span className="value margin-val">${orderResult.total_cost.toFixed(2)}</span>
            </div>
            {orderResult.tracking_number && (
              <div className="detail-row tracking-highlight">
                <span className="label">Tracking Number:</span>
                <span className="value code-val">{orderResult.tracking_number}</span>
              </div>
            )}
            <div className="detail-row">
              <span className="label">Trạng thái:</span>
              <span className="value status-badge">{orderResult.status}</span>
            </div>
          </div>
          <span className="success-footer">Xưởng in đang tiến hành xử lý phôi và vận chuyển.</span>
        </div>
      ) : (
        // Checkout Form HUD
        <div className="checkout-container flex-col">
          {/* Section 1: Product Inspector */}
          <div className="inspector-section">
            <div className="section-title flex-center">
              <Package size={14} />
              <span>Product Inspector</span>
            </div>
            
            <div className="mockup-display flex-center">
              {renderProductMockup()}
            </div>

            <div className="product-meta">
              <h4>{productName}</h4>
              <p className="sku-preview">SKU nháp: <code>{getSKU()}</code></p>
              
              <div className="specs-selectors">
                <div className="selector-group">
                  <span className="sel-label">Màu sắc:</span>
                  <div className="colors-grid">
                    {availableColors.map((color) => (
                      <button
                        key={color}
                        type="button"
                        className={`color-chip-btn ${selectedColor === color ? 'active' : ''}`}
                        onClick={() => setSelectedColor(color)}
                      >
                        {color}
                      </button>
                    ))}
                  </div>
                </div>

                <div className="selector-group">
                  <span className="sel-label">Kích thước:</span>
                  <div className="sizes-grid">
                    {availableSizes.map((size) => (
                      <button
                        key={size}
                        type="button"
                        className={`size-chip-btn ${selectedSize === size ? 'active' : ''}`}
                        onClick={() => setSelectedSize(size)}
                      >
                        {size}
                      </button>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Section 2: Order HUD Checkout form */}
          <form onSubmit={handleConfirmOrder} className="hud-section flex-col">
            <div className="section-title flex-center">
              <MapPin size={14} />
              <span>Thông Tin Nhận Hàng</span>
            </div>
            
            {error && <div className="checkout-error">{error}</div>}

            <div className="checkout-inputs">
              <div className="input-row">
                <input
                  type="text"
                  placeholder="Tên người nhận"
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  disabled={loading}
                />
              </div>
              <div className="input-row">
                <input
                  type="text"
                  placeholder="Địa chỉ dòng 1"
                  value={addressLine1}
                  onChange={(e) => setAddressLine1(e.target.value)}
                  disabled={loading}
                />
              </div>
              <div className="input-grid">
                <input
                  type="text"
                  placeholder="Thành phố"
                  value={city}
                  onChange={(e) => setCity(e.target.value)}
                  disabled={loading}
                />
                <input
                  type="text"
                  placeholder="Bang/Tỉnh"
                  value={stateName}
                  onChange={(e) => setStateName(e.target.value)}
                  disabled={loading}
                />
              </div>
              <div className="input-grid">
                <input
                  type="text"
                  placeholder="Mã Zip"
                  value={zipCode}
                  onChange={(e) => setZipCode(e.target.value)}
                  disabled={loading}
                />
                <input
                  type="text"
                  placeholder="Quốc gia"
                  value={country}
                  disabled
                  title="Tự động đồng bộ với thị trường đã chọn"
                />
              </div>
              <div className="quantity-row flex-center">
                <span>Số lượng đặt hàng:</span>
                <div className="quantity-input flex-center">
                  <button
                    type="button"
                    onClick={() => setQuantity(Math.max(1, quantity - 1))}
                    disabled={loading || quantity <= 1}
                  >
                    -
                  </button>
                  <span className="qty-val">{quantity}</span>
                  <button
                    type="button"
                    onClick={() => setQuantity(quantity + 1)}
                    disabled={loading}
                  >
                    +
                  </button>
                </div>
              </div>
            </div>

            {/* Price breakdown details */}
            <div className="billing-summary">
              <div className="section-title flex-center">
                <CreditCard size={14} />
                <span>Báo Giá Landed Cost</span>
              </div>
              
              <div className="bill-item">
                <span className="label">Base Cost ({quantity}x):</span>
                <span className="value">${totalBase.toFixed(2)}</span>
              </div>
              <div className="bill-item">
                <span className="label">Print Cost ({quantity}x):</span>
                <span className="value">${totalPrint.toFixed(2)}</span>
              </div>
              <div className="bill-item">
                <span className="label">Vận chuyển ({quantity}x):</span>
                <span className="value">${totalShip.toFixed(2)}</span>
              </div>
              <div className="bill-item">
                <span className="label">Thuế suất ({market}):</span>
                <span className="value">${totalTax.toFixed(2)}</span>
              </div>
              <div className="bill-total flex-center">
                <span className="label">Tổng Landed Cost:</span>
                <span className="value">${totalLandedCost.toFixed(2)}</span>
              </div>
            </div>

            <button type="submit" className="confirm-order-btn flex-center" disabled={loading}>
              {loading ? (
                <span className="spinner"></span>
              ) : (
                <>
                  <Sparkles size={16} style={{ marginRight: '8px' }} />
                  Confirm Fulfillment Order
                </>
              )}
            </button>
          </form>
        </div>
      )}
    </aside>
  );
};
