import React, { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { Mail, Lock, ShoppingBag, Eye, EyeOff, Sparkles, Terminal } from 'lucide-react';
import './AuthModal.css';

export const AuthModal: React.FC = () => {
  const { login, register } = useAuth();
  const [isLogin, setIsLogin] = useState<boolean>(true);
  
  // Fields
  const [email, setEmail] = useState<string>('');
  const [password, setPassword] = useState<string>('');
  const [storeName, setStoreName] = useState<string>('');
  const [showPassword, setShowPassword] = useState<boolean>(false);
  
  // States
  const [error, setError] = useState<string>('');
  const [loading, setLoading] = useState<boolean>(false);

  const validateEmail = (emailStr: string): boolean => {
    const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return re.test(emailStr);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    
    if (!email || !password) {
      setError('Vui lòng điền đầy đủ Email và Mật khẩu.');
      return;
    }
    
    if (!validateEmail(email)) {
      setError('Định dạng Email không hợp lệ.');
      return;
    }
    
    if (password.length < 6) {
      setError('Mật khẩu phải chứa ít nhất 6 ký tự.');
      return;
    }

    if (!isLogin && !storeName) {
      setError('Vui lòng cung cấp Tên Cửa Hàng POD.');
      return;
    }

    try {
      setLoading(true);
      if (isLogin) {
        await login(email, password);
      } else {
        await register(email, password, storeName);
      }
    } catch (err: any) {
      console.error(err);
      if (err.response && err.response.data && err.response.data.detail) {
        setError(err.response.data.detail);
      } else {
        setError('Đã xảy ra lỗi kết nối. Vui lòng kiểm tra lại server backend.');
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-overlay flex-center">
      <div className="auth-container glass glow-secondary">
        <div className="auth-header">
          <div className="logo-container">
            <Terminal className="logo-icon pulse-indicator" />
            <span className="logo-text text-gradient-secondary">Burger Agent</span>
          </div>
          <p className="logo-subtitle">AI-Powered POD Fulfillment Decision Engine</p>
        </div>

        <div className="auth-tabs">
          <button 
            type="button" 
            className={`auth-tab ${isLogin ? 'active' : ''}`}
            onClick={() => { setIsLogin(true); setError(''); }}
          >
            Đăng Nhập
          </button>
          <button 
            type="button" 
            className={`auth-tab ${!isLogin ? 'active' : ''}`}
            onClick={() => { setIsLogin(false); setError(''); }}
          >
            Đăng Ký
          </button>
        </div>

        <form onSubmit={handleSubmit} className="auth-form">
          {error && <div className="auth-error">{error}</div>}

          <div className="form-group glow-primary">
            <label htmlFor="email-input">Địa chỉ Email</label>
            <div className="input-wrapper">
              <Mail className="input-icon" />
              <input
                id="email-input"
                type="email"
                placeholder="seller@example.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                disabled={loading}
              />
            </div>
          </div>

          {!isLogin && (
            <div className="form-group glow-primary">
              <label htmlFor="store-input">Tên Cửa Hàng POD</label>
              <div className="input-wrapper">
                <ShoppingBag className="input-icon" />
                <input
                  id="store-input"
                  type="text"
                  placeholder="My Store LLC"
                  value={storeName}
                  onChange={(e) => setStoreName(e.target.value)}
                  disabled={loading}
                />
              </div>
            </div>
          )}

          <div className="form-group glow-primary">
            <label htmlFor="password-input">Mật khẩu</label>
            <div className="input-wrapper">
              <Lock className="input-icon" />
              <input
                id="password-input"
                type={showPassword ? 'text' : 'password'}
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                disabled={loading}
              />
              <button
                type="button"
                className="eye-toggle"
                onClick={() => setShowPassword(!showPassword)}
                disabled={loading}
              >
                {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
              </button>
            </div>
          </div>

          <button type="submit" className="auth-submit-btn flex-center" disabled={loading}>
            {loading ? (
              <span className="spinner"></span>
            ) : (
              <>
                <Sparkles size={16} style={{ marginRight: '8px' }} />
                {isLogin ? 'Vào Dashboard' : 'Tạo Tài Khoản'}
              </>
            )}
          </button>
        </form>

        <div className="auth-footer">
          {isLogin ? (
            <p>
              Chưa có tài khoản?{' '}
              <button type="button" onClick={() => setIsLogin(false)}>
                Đăng ký ngay
              </button>
            </p>
          ) : (
            <p>
              Đã có tài khoản?{' '}
              <button type="button" onClick={() => setIsLogin(true)}>
                Đăng nhập
              </button>
            </p>
          )}
        </div>
      </div>
    </div>
  );
};
