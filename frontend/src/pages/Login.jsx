import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Mail, Smartphone, ArrowRight, ArrowLeft, ShieldCheck } from 'lucide-react';
import { RecaptchaVerifier, signInWithPhoneNumber } from "firebase/auth";
import { auth } from '../firebase';
import '../components/Login.css';

const API_BASE_URL = 'http://localhost:8000/api'; 

export default function Login({ onLoginSuccess }) {
  const [activeTab, setActiveTab] = useState('email'); 
  const [step, setStep] = useState('request'); // 'request' or 'verify'
  
  // Form States
  const [email, setEmail] = useState('');
  const [phone, setPhone] = useState('+91');
  const [otp, setOtp] = useState('');
  
  // Firebase State
  const [confirmationResult, setConfirmationResult] = useState(null);

  // UI States
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  // Setup reCAPTCHA
  useEffect(() => {
    if (!window.recaptchaVerifier) {
      window.recaptchaVerifier = new RecaptchaVerifier(auth, 'recaptcha-container', {
        'size': 'invisible',
        'callback': (response) => {
          // reCAPTCHA solved
        }
      });
    }
  }, []);

  // --- EMAIL FLOW ---
  const handleEmailRequest = async (e) => {
    e.preventDefault();
    setLoading(true); setError(''); setSuccess('');
    
    try {
      await axios.post(`${API_BASE_URL}/auth/login/email/request-otp/`, { email });
      setSuccess('OTP sent successfully! Please check your email.');
      setStep('verify');
    } catch (err) {
      setError(err.response?.data?.error || 'Failed to send OTP.');
    } finally {
      setLoading(false);
    }
  };

  const handleEmailVerify = async (e) => {
    e.preventDefault();
    setLoading(true); setError('');

    try {
      const response = await axios.post(`${API_BASE_URL}/auth/login/email/verify-otp/`, {
        email,
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

  // --- MOBILE FIREBASE FLOW ---
  const handlePhoneRequest = async (e) => {
    e.preventDefault();
    setLoading(true); setError(''); setSuccess('');

    try {
      const appVerifier = window.recaptchaVerifier;
      const confirmation = await signInWithPhoneNumber(auth, phone, appVerifier);
      setConfirmationResult(confirmation);
      setSuccess('OTP sent successfully! Please check your phone.');
      setStep('verify');
    } catch (err) {
      console.error("Firebase Phone Auth Error:", err);
      // Display the actual error message from Firebase so we can see what went wrong
      setError(`Error: ${err.code || err.message || 'Failed to send SMS'}`);
    } finally {
      setLoading(false);
    }
  };

  const handlePhoneVerify = async (e) => {
    e.preventDefault();
    setLoading(true); setError('');

    try {
      let idToken;
      if (confirmationResult) {
         // Real Firebase flow
         const result = await confirmationResult.confirm(otp);
         idToken = await result.user.getIdToken();
      } else {
         // Mock fallback for testing if Firebase isn't configured properly
         idToken = "test_token_success"; 
      }

      // Send to Django backend
      const response = await axios.post(`${API_BASE_URL}/auth/login/mobile/firebase-verify/`, {
        firebase_id_token: idToken
      });
      
      if (response.data.access) {
        localStorage.setItem('access_token', response.data.access);
        if(onLoginSuccess) onLoginSuccess(response.data);
      }
    } catch (err) {
      console.error(err);
      setError(err.response?.data?.error || 'Invalid OTP code.');
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

        {step === 'request' && (
          <div className="toggle-container">
            <div 
              className="toggle-indicator" 
              style={{ transform: `translateX(${activeTab === 'email' ? '0' : '100%'})`, marginLeft: activeTab === 'mobile' ? '0.5rem' : '0' }}
            />
            <button 
              className={`toggle-btn ${activeTab === 'email' ? 'active' : ''}`}
              onClick={() => { setActiveTab('email'); resetFlow(); }}
            >
              <Mail size={16} style={{display: 'inline', marginRight: '6px', verticalAlign: 'text-bottom'}}/>
              Email
            </button>
            <button 
              className={`toggle-btn ${activeTab === 'mobile' ? 'active' : ''}`}
              onClick={() => { setActiveTab('mobile'); resetFlow(); }}
            >
              <Smartphone size={16} style={{display: 'inline', marginRight: '6px', verticalAlign: 'text-bottom'}}/>
              Mobile
            </button>
          </div>
        )}

        {error && <div className="message error">{error}</div>}
        {success && <div className="message success">{success}</div>}

        {/* This invisible div is needed for Firebase Recaptcha */}
        <div id="recaptcha-container"></div>

        {activeTab === 'email' && step === 'request' && (
          <form onSubmit={handleEmailRequest}>
            <div className="form-group">
              <label>Email Address</label>
              <input 
                type="email" className="form-control" placeholder="you@example.com"
                value={email} onChange={e => setEmail(e.target.value)} required
              />
            </div>
            <button type="submit" className="submit-btn" disabled={loading}>
              {loading ? 'Sending...' : 'Send Email OTP'} <ArrowRight size={18} />
            </button>
          </form>
        )}

        {activeTab === 'mobile' && step === 'request' && (
          <form onSubmit={handlePhoneRequest}>
            <div className="form-group">
              <label>Mobile Number</label>
              <input 
                type="tel" className="form-control" placeholder="+91 9876543210"
                value={phone} onChange={e => setPhone(e.target.value)} required
              />
            </div>
            <button type="submit" className="submit-btn" disabled={loading}>
              {loading ? 'Sending...' : 'Send SMS OTP'} <ArrowRight size={18} />
            </button>
          </form>
        )}

        {step === 'verify' && (
          <form onSubmit={activeTab === 'email' ? handleEmailVerify : handlePhoneVerify}>
            <button type="button" className="back-btn" onClick={resetFlow}>
              <ArrowLeft size={16} /> Back
            </button>
            <div className="form-group">
              <label>Enter 6-digit OTP</label>
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
