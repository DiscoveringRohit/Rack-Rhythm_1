import React, { useState } from 'react';
import axios from 'axios';
import { Mail, Smartphone, ArrowRight, ArrowLeft, ShieldCheck } from 'lucide-react';
import '../components/Login.css';

const API_BASE_URL = 'http://localhost:8000/api'; 

export default function Login({ onLoginSuccess }) {
  const [step, setStep] = useState('request'); // 'request' or 'verify'
  
  // Form States
  const [email, setEmail] = useState('');
  const [phone, setPhone] = useState('+91');
  const [otp, setOtp] = useState('');
  
  // UI States
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  const handleOTPRequest = async (e) => {
    e.preventDefault();
    setLoading(true); setError(''); setSuccess('');
    
    try {
      await axios.post(`${API_BASE_URL}/auth/login/request-otp/`, { email, phone_number: phone });
      setSuccess('OTP sent successfully! Please check your email.');
      setStep('verify');
    } catch (err) {
      setError(err.response?.data?.error || 'Failed to send OTP.');
    } finally {
      setLoading(false);
    }
  };

  const handleOTPVerify = async (e) => {
    e.preventDefault();
    setLoading(true); setError('');

    try {
      const response = await axios.post(`${API_BASE_URL}/auth/login/verify-otp/`, {
        email,
        phone_number: phone,
        otp_code: otp
      });
      if (response.data.access) {
        localStorage.setItem('access_token', response.data.access);
        if(onLoginSuccess) onLoginSuccess(response.data);
      }
    } catch (err) {
      setError(err.response?.data?.error || 'Invalid or expired OTP.');
    } finally {
      setLoading(false);
    }
  };

  const resetFlow = () => {
    setStep('request');
    setSuccess('');
    setError('');
    setOtp('');
  };

  return (
    <div className="login-container">
      <div className="login-card">
        <div className="login-header">
          <h1>Welcome Back</h1>
          <p>Sign in to your account to continue</p>
        </div>

        {error && <div className="message error">{error}</div>}
        {success && <div className="message success">{success}</div>}

        {step === 'request' && (
          <form onSubmit={handleOTPRequest}>
            <div className="form-group">
              <label><Smartphone size={14} style={{display: 'inline', marginRight: '4px', verticalAlign: 'text-bottom'}}/> Mobile Number</label>
              <input 
                type="tel" className="form-control" placeholder="+91 9876543210"
                value={phone} onChange={e => setPhone(e.target.value)} required
              />
            </div>
            <div className="form-group" style={{ marginTop: '1rem' }}>
              <label><Mail size={14} style={{display: 'inline', marginRight: '4px', verticalAlign: 'text-bottom'}}/> Email Address</label>
              <input 
                type="email" className="form-control" placeholder="you@example.com"
                value={email} onChange={e => setEmail(e.target.value)} required
              />
            </div>
            <button type="submit" className="submit-btn" disabled={loading} style={{ marginTop: '1.5rem' }}>
              {loading ? 'Sending...' : 'Send OTP via Email'} <ArrowRight size={18} />
            </button>
          </form>
        )}

        {step === 'verify' && (
          <form onSubmit={handleOTPVerify}>
            <button type="button" className="back-btn" onClick={resetFlow}>
              <ArrowLeft size={16} /> Back
            </button>
            <div className="form-group">
              <label>Enter 6-digit OTP (from Email)</label>
              <input 
                type="text" className="form-control" placeholder="000000" maxLength="6"
                value={otp} onChange={e => setOtp(e.target.value)} required
              />
            </div>
            <button type="submit" className="submit-btn" disabled={loading}>
              {loading ? 'Verifying...' : 'Verify & Login'} <ShieldCheck size={18} />
            </button>
          </form>
        )}
      </div>
    </div>
  );
}
