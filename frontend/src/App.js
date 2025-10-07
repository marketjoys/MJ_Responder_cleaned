import React, { useState, useEffect, createContext, useContext } from 'react';
import { BrowserRouter, Routes, Route, Navigate, useNavigate } from 'react-router-dom';
import axios from 'axios';
import './App.css';

// Import Calendar Components
import { CalendarEvents, MeetingDetection } from './CalendarComponents';
import OAuthCallback from './OAuthCallback';
import { RichTextEditor } from './components/ui/rich-text-editor';

// UI Components
import { Button } from './components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './components/ui/card';
import { Input } from './components/ui/input';
import { Label } from './components/ui/label';
import { Textarea } from './components/ui/textarea';
import { Badge } from './components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from './components/ui/tabs';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from './components/ui/select';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from './components/ui/dialog';
import { Alert, AlertDescription } from './components/ui/alert';
import { Separator } from './components/ui/separator';
import { Switch } from './components/ui/switch';

// Icons
import { 
  Mail, Settings, Brain, Database, Users, BarChart3, 
  Plus, Trash2, Eye, Send, RefreshCw, MessageSquare, 
  AlertCircle, CheckCircle, Clock, Zap, Bot, Play, 
  Pause, Activity, Inbox, Shield, Power, Calendar,
  PowerOff, WifiOff, Wifi, SendHorizontal, User,
  LogOut, LogIn, UserPlus, CalendarDays, CalendarPlus,
  Cloud, Smartphone, Monitor, MapPin, Users2, Timer, X, Edit3
} from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

// Email provider configurations
const EMAIL_PROVIDERS = {
  gmail: {
    name: 'Gmail',
    imap_server: 'imap.gmail.com',
    imap_port: 993,
    smtp_server: 'smtp.gmail.com',
    smtp_port: 587
  },
  outlook: {
    name: 'Outlook/Hotmail',
    imap_server: 'outlook.office365.com',
    imap_port: 993,
    smtp_server: 'smtp-mail.outlook.com',
    smtp_port: 587
  },
  yahoo: {
    name: 'Yahoo Mail',
    imap_server: 'imap.mail.yahoo.com',
    imap_port: 993,
    smtp_server: 'smtp.mail.yahoo.com',
    smtp_port: 587
  },
  custom: {
    name: 'Custom IMAP/SMTP',
    imap_server: '',
    imap_port: 993,
    smtp_server: '',
    smtp_port: 587
  }
};

// Auth Context
const AuthContext = createContext();

const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(localStorage.getItem('token'));
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (token) {
      axios.defaults.headers.common['Authorization'] = `Bearer ${token}`;
      fetchUserProfile();
    } else {
      setLoading(false);
    }
  }, [token]);

  const fetchUserProfile = async () => {
    try {
      const response = await axios.get(`${API}/auth/me`);
      setUser(response.data);
    } catch (error) {
      console.error('Error fetching user profile:', error);
      logout();
    } finally {
      setLoading(false);
    }
  };

  const login = async (email, password) => {
    try {
      const response = await axios.post(`${API}/auth/login`, {
        email: email,
        password: password
      });
      const { access_token, user: userData } = response.data;
      setToken(access_token);
      setUser(userData);
      localStorage.setItem('token', access_token);
      axios.defaults.headers.common['Authorization'] = `Bearer ${access_token}`;
      return { success: true };
    } catch (error) {
      return { 
        success: false, 
        error: error.response?.data?.detail || 'Login failed' 
      };
    }
  };

  const register = async (email, password, fullName, timezone = 'UTC') => {
    try {
      const response = await axios.post(`${API}/auth/register`, {
        email,
        password,
        full_name: fullName,
        timezone
      });
      return { success: true, data: response.data };
    } catch (error) {
      return { 
        success: false, 
        error: error.response?.data?.detail || 'Registration failed' 
      };
    }
  };

  const logout = () => {
    setToken(null);
    setUser(null);
    localStorage.removeItem('token');
    delete axios.defaults.headers.common['Authorization'];
  };

  const updateQuota = async (newQuota) => {
    try {
      const response = await axios.post(`${API}/auth/quota/upgrade`, {
        new_quota: newQuota
      });
      setUser(prev => ({ ...prev, ...response.data }));
      return { success: true };
    } catch (error) {
      return { 
        success: false, 
        error: error.response?.data?.detail || 'Quota update failed' 
      };
    }
  };

  const value = {
    user,
    token,
    loading,
    login,
    register,
    logout,
    updateQuota,
    refreshProfile: fetchUserProfile
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};

// Protected Route Component
const ProtectedRoute = ({ children }) => {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <RefreshCw className="h-8 w-8 animate-spin text-purple-600" />
      </div>
    );
  }

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  return children;
};

// Main App Component
function App() {
  return (
    <div className="App">
      <AuthProvider>
        <BrowserRouter>
          <Routes>
            <Route path="/login" element={<LoginPage />} />
            <Route path="/register" element={<RegisterPage />} />
            <Route path="/oauth/google/callback" element={<OAuthCallback provider="google" />} />
            <Route path="/oauth/microsoft/callback" element={<OAuthCallback provider="microsoft" />} />
            <Route path="/" element={<Navigate to="/dashboard" replace />} />
            <Route path="/dashboard" element={
              <ProtectedRoute>
                <Dashboard />
              </ProtectedRoute>
            } />
            <Route path="/profile" element={
              <ProtectedRoute>
                <UserProfile />
              </ProtectedRoute>
            } />
            <Route path="/calendar-providers" element={
              <ProtectedRoute>
                <CalendarProviders />
              </ProtectedRoute>
            } />
            <Route path="/calendar-events" element={
              <ProtectedRoute>
                <CalendarEventsPage />
              </ProtectedRoute>
            } />
            <Route path="/meeting-detection" element={
              <ProtectedRoute>
                <MeetingDetectionPage />
              </ProtectedRoute>
            } />
            <Route path="/intents" element={
              <ProtectedRoute>
                <IntentManagement />
              </ProtectedRoute>
            } />
            <Route path="/accounts" element={
              <ProtectedRoute>
                <EmailAccounts />
              </ProtectedRoute>
            } />
            <Route path="/knowledge" element={
              <ProtectedRoute>
                <KnowledgeBase />
              </ProtectedRoute>
            } />
            <Route path="/emails" element={
              <ProtectedRoute>
                <EmailProcessing />
              </ProtectedRoute>
            } />
            <Route path="/follow-ups" element={
              <ProtectedRoute>
                <FollowUpManagement />
              </ProtectedRoute>
            } />
            <Route path="/test" element={
              <ProtectedRoute>
                <EmailTesting />
              </ProtectedRoute>
            } />
            <Route path="/monitoring" element={
              <ProtectedRoute>
                <EmailMonitoring />
              </ProtectedRoute>
            } />
          </Routes>
        </BrowserRouter>
      </AuthProvider>
    </div>
  );
}

// Login Page Component
const LoginPage = () => {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [formData, setFormData] = useState({ email: '', password: '' });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    const result = await login(formData.email, formData.password);
    if (result.success) {
      // Redirect to dashboard on successful login
      navigate('/dashboard');
    } else {
      setError(result.error);
    }
    setLoading(false);
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-purple-50 flex items-center justify-center p-4">
      <Card className="w-full max-w-md shadow-2xl">
        <CardHeader className="text-center">
          <div className="flex justify-center mb-4">
            <div className="p-3 bg-gradient-to-r from-purple-500 to-pink-500 rounded-xl">
              <Bot className="h-8 w-8 text-white" />
            </div>
          </div>
          <CardTitle className="text-2xl font-bold bg-gradient-to-r from-purple-600 to-pink-600 bg-clip-text text-transparent">
            Welcome Back
          </CardTitle>
          <CardDescription>Sign in to your Email Assistant account</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            {error && (
              <Alert className="border-red-200 bg-red-50">
                <AlertCircle className="h-4 w-4 text-red-600" />
                <AlertDescription className="text-red-700">
                  {typeof error === 'string' ? error : error?.message || error?.detail || JSON.stringify(error, null, 2)}
                </AlertDescription>
              </Alert>
            )}
            
            <div>
              <Label htmlFor="email">Email</Label>
              <Input
                id="email"
                type="email"
                value={formData.email}
                onChange={(e) => setFormData(prev => ({ ...prev, email: e.target.value }))}
                placeholder="Enter your email"
                required
              />
            </div>
            
            <div>
              <Label htmlFor="password">Password</Label>
              <Input
                id="password"
                type="password"
                value={formData.password}
                onChange={(e) => setFormData(prev => ({ ...prev, password: e.target.value }))}
                placeholder="Enter your password"
                required
              />
            </div>
            
            <Button 
              type="submit" 
              className="w-full bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-700 hover:to-pink-700"
              disabled={loading}
            >
              {loading ? (
                <>
                  <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
                  Signing In...
                </>
              ) : (
                <>
                  <LogIn className="h-4 w-4 mr-2" />
                  Sign In
                </>
              )}
            </Button>
            
            <div className="text-center">
              <Button 
                variant="link" 
                onClick={() => navigate('/register')}
                className="text-purple-600 hover:text-purple-700"
              >
                Don't have an account? Sign up
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  );
};

// Register Page Component
const RegisterPage = () => {
  const { register } = useAuth();
  const navigate = useNavigate();
  const [formData, setFormData] = useState({
    email: '',
    password: '',
    confirmPassword: '',
    fullName: '',
    timezone: Intl.DateTimeFormat().resolvedOptions().timeZone
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    if (formData.password !== formData.confirmPassword) {
      setError('Passwords do not match');
      setLoading(false);
      return;
    }

    const result = await register(formData.email, formData.password, formData.fullName, formData.timezone);
    if (result.success) {
      setSuccess(true);
    } else {
      setError(result.error);
    }
    setLoading(false);
  };

  if (success) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-50 to-purple-50 flex items-center justify-center p-4">
        <Card className="w-full max-w-md shadow-2xl">
          <CardHeader className="text-center">
            <div className="flex justify-center mb-4">
              <div className="p-3 bg-gradient-to-r from-green-500 to-emerald-500 rounded-xl">
                <CheckCircle className="h-8 w-8 text-white" />
              </div>
            </div>
            <CardTitle className="text-2xl font-bold text-green-600">Registration Successful!</CardTitle>
            <CardDescription>Your account has been created successfully.</CardDescription>
          </CardHeader>
          <CardContent>
            <Button 
              onClick={() => navigate('/login')}
              className="w-full bg-gradient-to-r from-purple-600 to-pink-600"
            >
              <LogIn className="h-4 w-4 mr-2" />
              Go to Login
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-purple-50 flex items-center justify-center p-4">
      <Card className="w-full max-w-md shadow-2xl">
        <CardHeader className="text-center">
          <div className="flex justify-center mb-4">
            <div className="p-3 bg-gradient-to-r from-purple-500 to-pink-500 rounded-xl">
              <UserPlus className="h-8 w-8 text-white" />
            </div>
          </div>
          <CardTitle className="text-2xl font-bold bg-gradient-to-r from-purple-600 to-pink-600 bg-clip-text text-transparent">
            Create Account
          </CardTitle>
          <CardDescription>Join Email Assistant today</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            {error && (
              <Alert className="border-red-200 bg-red-50">
                <AlertCircle className="h-4 w-4 text-red-600" />
                <AlertDescription className="text-red-700">
                  {typeof error === 'string' ? error : error?.message || error?.detail || JSON.stringify(error, null, 2)}
                </AlertDescription>
              </Alert>
            )}
            
            <div>
              <Label htmlFor="fullName">Full Name</Label>
              <Input
                id="fullName"
                value={formData.fullName}
                onChange={(e) => setFormData(prev => ({ ...prev, fullName: e.target.value }))}
                placeholder="Enter your full name"
                required
              />
            </div>
            
            <div>
              <Label htmlFor="email">Email</Label>
              <Input
                id="email"
                type="email"
                value={formData.email}
                onChange={(e) => setFormData(prev => ({ ...prev, email: e.target.value }))}
                placeholder="Enter your email"
                required
              />
            </div>
            
            <div>
              <Label htmlFor="password">Password</Label>
              <Input
                id="password"
                type="password"
                value={formData.password}
                onChange={(e) => setFormData(prev => ({ ...prev, password: e.target.value }))}
                placeholder="Enter your password"
                required
              />
            </div>
            
            <div>
              <Label htmlFor="confirmPassword">Confirm Password</Label>
              <Input
                id="confirmPassword"
                type="password"
                value={formData.confirmPassword}
                onChange={(e) => setFormData(prev => ({ ...prev, confirmPassword: e.target.value }))}
                placeholder="Confirm your password"
                required
              />
            </div>
            
            <div>
              <Label htmlFor="timezone">Timezone</Label>
              <Input
                id="timezone"
                value={formData.timezone}
                onChange={(e) => setFormData(prev => ({ ...prev, timezone: e.target.value }))}
                placeholder="Your timezone"
                required
              />
            </div>
            
            <Button 
              type="submit" 
              className="w-full bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-700 hover:to-pink-700"
              disabled={loading}
            >
              {loading ? (
                <>
                  <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
                  Creating Account...
                </>
              ) : (
                <>
                  <UserPlus className="h-4 w-4 mr-2" />
                  Create Account
                </>
              )}
            </Button>
            
            <div className="text-center">
              <Button 
                variant="link" 
                onClick={() => navigate('/login')}
                className="text-purple-600 hover:text-purple-700"
              >
                Already have an account? Sign in
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  );
};

// Navigation Component
const Navigation = ({ activeTab, setActiveTab }) => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  
  const navItems = [
    { id: 'dashboard', label: 'Dashboard', icon: BarChart3, path: '/dashboard' },
    { id: 'profile', label: 'Profile', icon: User, path: '/profile' },
    { id: 'calendar-providers', label: 'Calendar Providers', icon: Cloud, path: '/calendar-providers' },
    { id: 'calendar-events', label: 'Calendar Events', icon: CalendarDays, path: '/calendar-events' },
    { id: 'meeting-detection', label: 'Meeting Detection', icon: Users2, path: '/meeting-detection' },
    { id: 'intents', label: 'Intents', icon: Brain, path: '/intents' },
    { id: 'accounts', label: 'Email Accounts', icon: Mail, path: '/accounts' },
    { id: 'knowledge', label: 'Knowledge Base', icon: Database, path: '/knowledge' },
    { id: 'emails', label: 'Email Processing', icon: MessageSquare, path: '/emails' },
    { id: 'follow-ups', label: 'Follow-ups', icon: Timer, path: '/follow-ups' },
    { id: 'monitoring', label: 'Live Monitoring', icon: Activity, path: '/monitoring' },
    { id: 'test', label: 'Test Email', icon: Zap, path: '/test' }
  ];

  return (
    <nav className="bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900 text-white p-6 min-h-screen w-64 shadow-2xl">
      <div className="flex items-center gap-3 mb-8">
        <div className="p-2 bg-gradient-to-r from-purple-500 to-pink-500 rounded-lg">
          <Bot className="h-6 w-6" />
        </div>
        <h1 className="text-xl font-bold bg-gradient-to-r from-purple-300 to-pink-300 bg-clip-text text-transparent">
          Email Assistant
        </h1>
      </div>

      {/* User Info */}
      {user && (
        <div className="bg-white/10 rounded-xl p-4 mb-6">
          <div className="flex items-center gap-3 mb-2">
            <User className="h-5 w-5 text-purple-300" />
            <span className="font-medium text-sm truncate">{user.full_name}</span>
          </div>
          <div className="text-xs text-purple-200 mb-2">{user.email}</div>
          <div className="text-xs text-green-300">
            Quota: {user.quota_info?.emails_used || 0}/{user.quota_info?.email_quota || 0}
          </div>
        </div>
      )}
      
      <ul className="space-y-2 mb-6">
        {navItems.map(item => (
          <li key={item.id}>
            <button
              onClick={() => navigate(item.path)}
              className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl transition-all duration-200 ${
                window.location.pathname === item.path
                  ? 'bg-gradient-to-r from-purple-600 to-pink-600 shadow-lg'
                  : 'hover:bg-white/10 hover:translate-x-1'
              }`}
            >
              <item.icon className="h-5 w-5" />
              <span className="font-medium text-sm">{item.label}</span>
            </button>
          </li>
        ))}
      </ul>

      {/* Logout Button */}
      <div className="border-t border-white/20 pt-4">
        <button
          onClick={logout}
          className="w-full flex items-center gap-3 px-4 py-3 rounded-xl transition-all duration-200 hover:bg-red-500/20 text-red-300 hover:text-red-200"
        >
          <LogOut className="h-5 w-5" />
          <span className="font-medium text-sm">Logout</span>
        </button>
      </div>
    </nav>
  );
};

// Layout Component
const Layout = ({ children }) => {
  return (
    <div className="flex min-h-screen bg-gradient-to-br from-slate-50 to-purple-50">
      <Navigation />
      <main className="flex-1 p-8">
        {children}
      </main>
    </div>
  );
};

// User Profile Component
const UserProfile = () => {
  const { user, updateQuota, refreshProfile } = useAuth();
  const [isEditing, setIsEditing] = useState(false);
  const [quotaUpgrade, setQuotaUpgrade] = useState('');
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');

  const handleQuotaUpgrade = async (e) => {
    e.preventDefault();
    setLoading(true);
    setMessage('');

    const result = await updateQuota(parseInt(quotaUpgrade));
    if (result.success) {
      setMessage('Quota updated successfully!');
      setQuotaUpgrade('');
      setIsEditing(false);
      refreshProfile();
    } else {
      setMessage(result.error);
    }
    setLoading(false);
  };

  if (!user) return null;

  const quotaPercentage = ((user.quota_info?.emails_used || 0) / (user.quota_info?.email_quota || 1)) * 100;

  return (
    <Layout>
      <div className="space-y-8">
        <div>
          <h1 className="text-4xl font-bold text-slate-800 mb-2">User Profile</h1>
          <p className="text-slate-600">Manage your account settings and quota</p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* Profile Information */}
          <Card className="shadow-lg">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <User className="h-5 w-5 text-blue-600" />
                Profile Information
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <Label className="text-sm font-medium text-slate-700">Full Name</Label>
                <div className="text-lg font-semibold">{user.full_name}</div>
              </div>
              <div>
                <Label className="text-sm font-medium text-slate-700">Email</Label>
                <div className="text-lg">{user.email}</div>
              </div>
              <div>
                <Label className="text-sm font-medium text-slate-700">Timezone</Label>
                <div className="text-lg">{user.timezone}</div>
              </div>
              <div>
                <Label className="text-sm font-medium text-slate-700">Account Status</Label>
                <Badge variant={user.is_active ? "default" : "secondary"}>
                  {user.is_active ? "Active" : "Inactive"}
                </Badge>
              </div>
              <div>
                <Label className="text-sm font-medium text-slate-700">Member Since</Label>
                <div className="text-lg">{new Date(user.created_at).toLocaleDateString()}</div>
              </div>
            </CardContent>
          </Card>

          {/* Quota Information */}
          <Card className="shadow-lg">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <BarChart3 className="h-5 w-5 text-green-600" />
                Email Quota
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <Label className="text-sm font-medium text-slate-700">Current Usage</Label>
                <div className="text-2xl font-bold text-green-600">
                  {user.quota_info?.emails_used || 0} / {user.quota_info?.email_quota || 0}
                </div>
                <div className="w-full bg-slate-200 rounded-full h-3 mt-2">
                  <div 
                    className={`h-3 rounded-full transition-all duration-300 ${
                      quotaPercentage > 90 ? 'bg-red-500' : 
                      quotaPercentage > 70 ? 'bg-yellow-500' : 'bg-green-500'
                    }`}
                    style={{ width: `${Math.min(quotaPercentage, 100)}%` }}
                  />
                </div>
                <div className="text-sm text-slate-600 mt-1">
                  {quotaPercentage.toFixed(1)}% used
                </div>
              </div>

              <div>
                <Label className="text-sm font-medium text-slate-700">Emails Remaining</Label>
                <div className="text-lg font-semibold">
                  {user.quota_info?.emails_remaining || 0}
                </div>
              </div>

              <div>
                <Label className="text-sm font-medium text-slate-700">Quota Reset Date</Label>
                <div className="text-lg">
                  {user.quota_info?.quota_reset_date ? 
                    new Date(user.quota_info.quota_reset_date).toLocaleDateString() : 
                    'N/A'
                  }
                </div>
                <div className="text-sm text-slate-600">
                  ({user.quota_info?.days_until_reset || 0} days remaining)
                </div>
              </div>

              {!isEditing ? (
                <Button 
                  onClick={() => setIsEditing(true)}
                  className="w-full bg-gradient-to-r from-purple-600 to-pink-600"
                >
                  <Plus className="h-4 w-4 mr-2" />
                  Upgrade Quota
                </Button>
              ) : (
                <form onSubmit={handleQuotaUpgrade} className="space-y-4">
                  <div>
                    <Label htmlFor="quota">New Quota Limit</Label>
                    <Input
                      id="quota"
                      type="number"
                      value={quotaUpgrade}
                      onChange={(e) => setQuotaUpgrade(e.target.value)}
                      placeholder="Enter new quota limit"
                      min={user.quota_info?.email_quota || 0}
                      required
                    />
                  </div>
                  <div className="flex gap-2">
                    <Button 
                      type="submit"
                      disabled={loading}
                      className="flex-1 bg-gradient-to-r from-green-600 to-emerald-600"
                    >
                      {loading ? (
                        <RefreshCw className="h-4 w-4 animate-spin" />
                      ) : (
                        'Update Quota'
                      )}
                    </Button>
                    <Button 
                      type="button"
                      variant="outline"
                      onClick={() => {
                        setIsEditing(false);
                        setQuotaUpgrade('');
                        setMessage('');
                      }}
                    >
                      Cancel
                    </Button>
                  </div>
                </form>
              )}

              {message && (
                <Alert className={(typeof message === 'string' && message.includes('success')) ? 'border-green-200 bg-green-50' : 'border-red-200 bg-red-50'}>
                  <AlertCircle className={`h-4 w-4 ${(typeof message === 'string' && message.includes('success')) ? 'text-green-600' : 'text-red-600'}`} />
                  <AlertDescription className={(typeof message === 'string' && message.includes('success')) ? 'text-green-700' : 'text-red-700'}>
                    {typeof message === 'object' ? JSON.stringify(message, null, 2) : message}
                  </AlertDescription>
                </Alert>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </Layout>
  );
};

// Calendar Providers Component with OAuth Support
const CalendarProviders = () => {
  const [providers, setProviders] = useState([]);
  const [oauthStatus, setOauthStatus] = useState(null);
  const [microsoftOauthStatus, setMicrosoftOauthStatus] = useState(null);
  const [isCreating, setIsCreating] = useState(false);
  const [accountType, setAccountType] = useState('manual'); // 'manual' or 'oauth'
  const [oauthProvider, setOauthProvider] = useState('google'); // 'google' or 'microsoft'
  const [formData, setFormData] = useState({
    provider_type: '',
    provider_name: '',
    credentials: {},
    timezone: Intl.DateTimeFormat().resolvedOptions().timeZone
  });
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');

  useEffect(() => {
    fetchProviders();
    fetchOAuthStatus();
    fetchMicrosoftOAuthStatus();
  }, []);

  const fetchProviders = async () => {
    try {
      const response = await axios.get(`${API}/calendar/providers`);
      setProviders(response.data);
    } catch (error) {
      console.error('Error fetching providers:', error);
    }
  };

  const fetchOAuthStatus = async () => {
    try {
      const response = await axios.get(`${API}/oauth/google/status`);
      setOauthStatus(response.data);
    } catch (error) {
      console.error('Error fetching OAuth status:', error);
      setOauthStatus({ is_authorized: false, authorized_services: [] });
    }
  };

  const fetchMicrosoftOAuthStatus = async () => {
    try {
      const response = await axios.get(`${API}/oauth/microsoft/status`);
      setMicrosoftOauthStatus(response.data);
    } catch (error) {
      console.error('Error fetching Microsoft OAuth status:', error);
      setMicrosoftOauthStatus({ is_authorized: false, authorized_services: [] });
    }
  };

  const initiateGoogleOAuth = async () => {
    setLoading(true);
    try {
      const response = await axios.post(`${API}/oauth/google/authorize`, ['calendar']);
      // Redirect to Google OAuth
      window.location.href = response.data.auth_url;
    } catch (error) {
      const errorDetail = error.response?.data?.detail;
      setMessage(typeof errorDetail === 'object' ? JSON.stringify(errorDetail) : (errorDetail || 'OAuth initiation failed'));
      setLoading(false);
    }
  };

  const initiateMicrosoftOAuth = async () => {
    setLoading(true);
    try {
      const response = await axios.post(`${API}/oauth/microsoft/authorize`, ['calendar']);
      // Redirect to Microsoft OAuth
      window.location.href = response.data.auth_url;
    } catch (error) {
      const errorDetail = error.response?.data?.detail;
      setMessage(typeof errorDetail === 'object' ? JSON.stringify(errorDetail) : (errorDetail || 'Microsoft OAuth initiation failed'));
      setLoading(false);
    }
  };

  const createOAuthProvider = async () => {
    setLoading(true);
    try {
      const providerData = {
        provider_type: oauthProvider,
        provider_name: formData.provider_name,
        use_oauth: true,
        timezone: formData.timezone
      };

      await axios.post(`${API}/calendar/providers/oauth`, providerData);
      setMessage('OAuth calendar provider created successfully!');
      setIsCreating(false);
      resetForm();
      fetchProviders();
      fetchOAuthStatus();
      fetchMicrosoftOAuthStatus();
    } catch (error) {
      setMessage(error.response?.data?.detail || 'Error creating OAuth provider');
    }
    setLoading(false);
  };

  const handleCreateProvider = async (e) => {
    e.preventDefault();
    
    if (accountType === 'oauth') {
      // Check OAuth status based on selected provider
      if (oauthProvider === 'google') {
        if (!oauthStatus?.is_authorized || !oauthStatus?.authorized_services?.includes('calendar')) {
          setMessage('Please authorize Google calendar access first');
          return;
        }
      } else if (oauthProvider === 'microsoft') {
        if (!microsoftOauthStatus?.is_authorized || !microsoftOauthStatus?.authorized_services?.includes('calendar')) {
          setMessage('Please authorize Microsoft calendar access first');
          return;
        }
      }
      await createOAuthProvider();
    } else {
      // Existing manual provider creation logic
      setLoading(true);
      setMessage('');

      try {
        await axios.post(`${API}/calendar/providers`, formData);
        setMessage('Provider created successfully!');
        setIsCreating(false);
        resetForm();
        fetchProviders();
      } catch (error) {
        setMessage(error.response?.data?.detail || 'Error creating provider');
      }
      setLoading(false);
    }
  };

  const handleDeleteProvider = async (providerId) => {
    try {
      await axios.delete(`${API}/calendar/providers/${providerId}`);
      fetchProviders();
    } catch (error) {
      console.error('Error deleting provider:', error);
    }
  };

  const resetForm = () => {
    setFormData({
      provider_type: '',
      provider_name: '',
      credentials: {},
      timezone: Intl.DateTimeFormat().resolvedOptions().timeZone
    });
    setAccountType('manual');
  };

  const revokeGoogleOAuth = async () => {
    setLoading(true);
    try {
      await axios.post(`${API}/oauth/google/revoke`);
      setMessage('Google OAuth access revoked successfully');
      fetchOAuthStatus();
      fetchProviders(); // Refresh providers as OAuth providers may be affected
    } catch (error) {
      setMessage(error.response?.data?.detail || 'Error revoking Google OAuth access');
    }
    setLoading(false);
  };

  const revokeMicrosoftOAuth = async () => {
    setLoading(true);
    try {
      await axios.post(`${API}/oauth/microsoft/revoke`);
      setMessage('Microsoft OAuth access revoked successfully');
      fetchMicrosoftOAuthStatus();
      fetchProviders(); // Refresh providers as OAuth providers may be affected
    } catch (error) {
      setMessage(error.response?.data?.detail || 'Error revoking Microsoft OAuth access');
    }
    setLoading(false);
  };

  const renderCredentialsFields = () => {
    switch (formData.provider_type) {
      case 'google':
        return (
          <>
            <div>
              <Label htmlFor="client_id">Google Client ID</Label>
              <Input
                id="client_id"
                value={formData.credentials.client_id || ''}
                onChange={(e) => setFormData(prev => ({
                  ...prev,
                  credentials: { ...prev.credentials, client_id: e.target.value }
                }))}
                placeholder="Enter Google Client ID"
                required
              />
            </div>
            <div>
              <Label htmlFor="client_secret">Google Client Secret</Label>
              <Input
                id="client_secret"
                type="password"
                value={formData.credentials.client_secret || ''}
                onChange={(e) => setFormData(prev => ({
                  ...prev,
                  credentials: { ...prev.credentials, client_secret: e.target.value }
                }))}
                placeholder="Enter Google Client Secret"
                required
              />
            </div>
          </>
        );
      case 'microsoft':
        return (
          <>
            <div>
              <Label htmlFor="client_id">Microsoft Client ID</Label>
              <Input
                id="client_id"
                value={formData.credentials.client_id || ''}
                onChange={(e) => setFormData(prev => ({
                  ...prev,
                  credentials: { ...prev.credentials, client_id: e.target.value }
                }))}
                placeholder="Enter Microsoft Client ID"
                required
              />
            </div>
            <div>
              <Label htmlFor="client_secret">Microsoft Client Secret</Label>
              <Input
                id="client_secret"
                type="password"
                value={formData.credentials.client_secret || ''}
                onChange={(e) => setFormData(prev => ({
                  ...prev,
                  credentials: { ...prev.credentials, client_secret: e.target.value }
                }))}
                placeholder="Enter Microsoft Client Secret"
                required
              />
            </div>
          </>
        );
      case 'apple':
        return (
          <>
            <div>
              <Label htmlFor="username">Apple ID Username</Label>
              <Input
                id="username"
                value={formData.credentials.username || ''}
                onChange={(e) => setFormData(prev => ({
                  ...prev,
                  credentials: { ...prev.credentials, username: e.target.value }
                }))}
                placeholder="Enter Apple ID Username"
                required
              />
            </div>
            <div>
              <Label htmlFor="password">Apple ID Password</Label>
              <Input
                id="password"
                type="password"
                value={formData.credentials.password || ''}
                onChange={(e) => setFormData(prev => ({
                  ...prev,
                  credentials: { ...prev.credentials, password: e.target.value }
                }))}
                placeholder="Enter Apple ID Password"
                required
              />
            </div>
          </>
        );
      case 'calcom':
        return (
          <div>
            <Label htmlFor="api_key">Cal.com API Key</Label>
            <Input
              id="api_key"
              type="password"
              value={formData.credentials.api_key || ''}
              onChange={(e) => setFormData(prev => ({
                ...prev,
                credentials: { ...prev.credentials, api_key: e.target.value }
              }))}
              placeholder="Enter Cal.com API Key"
              required
            />
          </div>
        );
      default:
        return null;
    }
  };

  const getProviderIcon = (type) => {
    switch (type) {
      case 'google': return <Cloud className="h-5 w-5 text-blue-600" />;
      case 'microsoft': return <Monitor className="h-5 w-5 text-blue-800" />;
      case 'apple': return <Smartphone className="h-5 w-5 text-slate-800" />;
      case 'calcom': return <Calendar className="h-5 w-5 text-orange-600" />;
      default: return <Calendar className="h-5 w-5 text-purple-600" />;
    }
  };

  return (
    <Layout>
      <div className="space-y-8">
        <div className="flex justify-between items-center">
          <div>
            <h1 className="text-4xl font-bold text-slate-800 mb-2">Calendar Providers</h1>
            <p className="text-slate-600">Connect your calendar services for meeting management</p>
          </div>
          <Button 
            onClick={() => setIsCreating(true)}
            className="bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-700 hover:to-pink-700"
          >
            <Plus className="h-4 w-4 mr-2" />
            Add Provider
          </Button>
        </div>

        {/* OAuth Status Card */}
        <Card className="shadow-lg border-l-4 border-l-green-500">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Shield className="h-5 w-5 text-green-600" />
              Google OAuth Status
            </CardTitle>
            <CardDescription>
              OAuth provides secure access to Google Calendar without storing credentials
            </CardDescription>
          </CardHeader>
          <CardContent>
            {oauthStatus?.is_authorized ? (
              <div className="space-y-4">
                <div className="flex items-center gap-2">
                  <CheckCircle className="h-5 w-5 text-green-600" />
                  <span className="text-green-700 font-medium">Google OAuth Authorized</span>
                </div>
                <div className="text-sm text-slate-600">
                  <p><strong>Account:</strong> {oauthStatus.user_name} ({oauthStatus.user_email})</p>
                  <p><strong>Services:</strong> {oauthStatus.authorized_services?.join(', ') || 'None'}</p>
                  <p><strong>Expires:</strong> {new Date(oauthStatus.expires_at).toLocaleString()}</p>
                </div>
                <Button
                  variant="outline"
                  size="sm" 
                  onClick={revokeOAuth}
                  disabled={loading}
                  className="text-red-600 hover:text-red-700"
                >
                  {loading ? <RefreshCw className="h-4 w-4 mr-2 animate-spin" /> : <PowerOff className="h-4 w-4 mr-2" />}
                  Revoke Access
                </Button>
              </div>
            ) : (
              <div className="space-y-4">
                <div className="flex items-center gap-2">
                  <WifiOff className="h-5 w-5 text-red-600" />
                  <span className="text-red-700 font-medium">Google OAuth Not Authorized</span>
                </div>
                <p className="text-sm text-slate-600">
                  Authorize Google OAuth to create calendar providers without storing credentials
                </p>
                <Button 
                  onClick={initiateGoogleOAuth}
                  disabled={loading}
                  className="bg-green-600 hover:bg-green-700"
                >
                  {loading ? <RefreshCw className="h-4 w-4 mr-2 animate-spin" /> : <Wifi className="h-4 w-4 mr-2" />}
                  Authorize Google
                </Button>
              </div>
            )}
          </CardContent>
        </Card>

        {message && (
          <Alert className={(typeof message === 'string' && message.includes('success')) ? 'border-green-200 bg-green-50' : 'border-red-200 bg-red-50'}>
            <AlertCircle className={`h-4 w-4 ${(typeof message === 'string' && message.includes('success')) ? 'text-green-600' : 'text-red-600'}`} />
            <AlertDescription className={(typeof message === 'string' && message.includes('success')) ? 'text-green-700' : 'text-red-700'}>
              {typeof message === 'object' ? JSON.stringify(message, null, 2) : message}
            </AlertDescription>
          </Alert>
        )}

        {/* Create Provider Dialog */}
        <Dialog open={isCreating} onOpenChange={(open) => {
          if (!open) {
            setIsCreating(false);
            resetForm();
            setMessage('');
          }
        }}>
          <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
            <DialogHeader>
              <DialogTitle>Add Calendar Provider</DialogTitle>
              <DialogDescription>
                Connect a calendar service to manage your meetings and events. Choose OAuth for enhanced security.
              </DialogDescription>
            </DialogHeader>
            
            <div className="space-y-6">
              <form onSubmit={handleCreateProvider} className="space-y-6">
                {/* Common Fields */}
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <Label htmlFor="provider_name">Provider Name</Label>
                    <Input
                      id="provider_name"
                      value={formData.provider_name}
                      onChange={(e) => setFormData(prev => ({ ...prev, provider_name: e.target.value }))}
                      placeholder="My Google Calendar"
                      required
                    />
                  </div>
                  <div>
                    <Label htmlFor="timezone">Timezone</Label>
                    <Input
                      id="timezone"
                      value={formData.timezone}
                      onChange={(e) => setFormData(prev => ({ ...prev, timezone: e.target.value }))}
                      placeholder="Your timezone"
                    />
                  </div>
                </div>

                {/* Provider Type Selection */}
                <div>
                  <Label>Provider Type</Label>
                  <Tabs value={accountType} onValueChange={setAccountType} className="mt-2">
                    <TabsList className="grid w-full grid-cols-2">
                      <TabsTrigger value="oauth" className="flex items-center gap-2">
                        <Shield className="h-4 w-4" />
                        OAuth (Recommended)
                      </TabsTrigger>
                      <TabsTrigger value="manual" className="flex items-center gap-2">
                        <Settings className="h-4 w-4" />
                        Manual Setup
                      </TabsTrigger>
                    </TabsList>

                    {/* OAuth-specific UI */}
                    <TabsContent value="oauth" className="space-y-4 mt-4">
                      <div className="bg-green-50 border border-green-200 rounded-lg p-4">
                        <div className="flex items-start gap-3">
                          <Shield className="h-5 w-5 text-green-600 mt-0.5" />
                          <div>
                            <h4 className="font-medium text-green-900">OAuth Authentication</h4>
                            <p className="text-sm text-green-700 mt-1">
                              OAuth provides secure access to Google Calendar without storing credentials. 
                              {oauthStatus?.is_authorized && oauthStatus?.authorized_services?.includes('calendar')
                                ? ' You are already authorized and can create an OAuth provider.'
                                : ' Please authorize Google access first.'
                              }
                            </p>
                          </div>
                        </div>
                      </div>

                      {oauthStatus?.is_authorized && oauthStatus?.authorized_services?.includes('calendar') ? (
                        <div className="space-y-4">
                          <div className="flex items-center gap-2 text-green-700">
                            <CheckCircle className="h-5 w-5" />
                            <span className="font-medium">Using Google account: {oauthStatus.user_email}</span>
                          </div>
                        </div>
                      ) : (
                        <div className="space-y-4">
                          <Alert className="border-yellow-200 bg-yellow-50">
                            <AlertCircle className="h-4 w-4 text-yellow-600" />
                            <AlertDescription className="text-yellow-700">
                              You need to authorize Google calendar access first. Click the "Authorize Google" button above.
                            </AlertDescription>
                          </Alert>
                        </div>
                      )}
                    </TabsContent>

                    {/* Manual setup fields */}
                    <TabsContent value="manual" className="space-y-4 mt-4">
                      <div>
                        <Label htmlFor="provider_type">Provider Type</Label>
                        <Select 
                          value={formData.provider_type} 
                          onValueChange={(value) => setFormData(prev => ({ 
                            ...prev, 
                            provider_type: value,
                            credentials: {} 
                          }))}
                          required
                        >
                          <SelectTrigger>
                            <SelectValue placeholder="Select calendar provider" />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="google">Google Calendar</SelectItem>
                            <SelectItem value="microsoft">Microsoft Outlook</SelectItem>
                            <SelectItem value="apple">Apple iCloud</SelectItem>
                            <SelectItem value="calcom">Cal.com</SelectItem>
                          </SelectContent>
                        </Select>
                      </div>

                      {/* Provider-specific credential fields */}
                      {formData.provider_type && (
                        <div className="space-y-4">
                          <h4 className="font-medium text-slate-700">Credentials</h4>
                          {renderCredentialsFields()}
                        </div>
                      )}
                    </TabsContent>
                  </Tabs>
                </div>

                <div className="flex justify-end gap-2">
                  <Button type="button" variant="outline" onClick={() => {
                    setIsCreating(false);
                    resetForm();
                    setMessage('');
                  }}>
                    Cancel
                  </Button>
                  <Button 
                    type="submit" 
                    disabled={loading || (accountType === 'oauth' && (!oauthStatus?.is_authorized || !oauthStatus?.authorized_services?.includes('calendar')))}
                    className="bg-gradient-to-r from-purple-600 to-pink-600"
                  >
                    {loading ? (
                      <>
                        <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
                        Creating...
                      </>
                    ) : (
                      <>
                        <Plus className="h-4 w-4 mr-2" />
                        Create Provider
                      </>
                    )}
                  </Button>
                </div>
              </form>
            </div>
          </DialogContent>
        </Dialog>

        {/* Providers List */}
        <div className="grid gap-6">
          {providers.map(provider => (
            <Card key={provider.id} className="shadow-lg hover:shadow-xl transition-shadow">
              <CardHeader>
                <div className="flex justify-between items-start">
                  <div>
                    <CardTitle className="flex items-center gap-2">
                      {getProviderIcon(provider.provider_type)}
                      {provider.provider_name}
                      <Badge variant={provider.is_active ? "default" : "secondary"}>
                        {provider.is_active ? "Active" : "Inactive"}
                      </Badge>
                      {provider.use_oauth && (
                        <Badge variant="outline" className="bg-green-50 text-green-700 border-green-200">
                          <Shield className="h-3 w-3 mr-1" />
                          OAuth
                        </Badge>
                      )}
                    </CardTitle>
                    <CardDescription>
                      {provider.provider_type.charAt(0).toUpperCase() + provider.provider_type.slice(1)} Calendar Provider
                    </CardDescription>
                  </div>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => handleDeleteProvider(provider.id)}
                    className="text-red-600 hover:text-red-700"
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </div>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                  <div>
                    <span className="font-medium text-slate-700">Type:</span>
                    <div className="text-slate-600 capitalize">{provider.provider_type}</div>
                  </div>
                  <div>
                    <span className="font-medium text-slate-700">Auth Type:</span>
                    <div className="text-slate-600 capitalize">
                      {provider.use_oauth ? 'OAuth' : 'Manual'}
                    </div>
                  </div>
                  <div>
                    <span className="font-medium text-slate-700">Timezone:</span>
                    <div className="text-slate-600">{provider.timezone}</div>
                  </div>
                  <div>
                    <span className="font-medium text-slate-700">Calendars:</span>
                    <div className="text-slate-600">{provider.calendar_count || 0}</div>
                  </div>
                </div>
                {provider.oauth_email && (
                  <div className="mt-4 pt-4 border-t border-slate-200">
                    <span className="font-medium text-slate-700 text-sm">OAuth Account:</span>
                    <div className="text-slate-600 text-sm mt-1">{provider.oauth_user} ({provider.oauth_email})</div>
                  </div>
                )}
              </CardContent>
            </Card>
          ))}
        </div>

        {providers.length === 0 && (
          <Card className="text-center py-12">
            <CardContent>
              <Calendar className="h-12 w-12 text-slate-400 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-slate-600 mb-2">No calendar providers configured</h3>
              <p className="text-slate-500 mb-4">Add your first calendar provider to start managing meetings</p>
              <Button 
                onClick={() => setIsCreating(true)}
                className="bg-gradient-to-r from-purple-600 to-pink-600"
              >
                <Plus className="h-4 w-4 mr-2" />
                Add First Provider
              </Button>
            </CardContent>
          </Card>
        )}
      </div>
    </Layout>
  );
};

// Calendar Events Wrapper
const CalendarEventsPage = () => {
  return <CalendarEvents Layout={Layout} />;
};

// Meeting Detection Wrapper
const MeetingDetectionPage = () => {
  return <MeetingDetection Layout={Layout} />;
};

// Dashboard Component
const Dashboard = () => {
  const navigate = useNavigate();
  const [stats, setStats] = useState({});
  const [loading, setLoading] = useState(true);
  const [pollingStatus, setPollingStatus] = useState('stopped');

  useEffect(() => {
    fetchStats();
    fetchPollingStatus();
    // Refresh stats every 30 seconds
    const interval = setInterval(() => {
      fetchStats();
      fetchPollingStatus();
    }, 30000);
    return () => clearInterval(interval);
  }, []);

  const fetchStats = async () => {
    try {
      const response = await axios.get(`${API}/dashboard/stats`);
      setStats(response.data);
    } catch (error) {
      console.error('Error fetching stats:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchPollingStatus = async () => {
    try {
      const response = await axios.get(`${API}/polling/status`);
      setPollingStatus(response.data.status);
    } catch (error) {
      console.error('Error fetching polling status:', error);
    }
  };

  const controlPolling = async (action) => {
    try {
      await axios.post(`${API}/polling/control`, { action });
      fetchPollingStatus();
      fetchStats();
    } catch (error) {
      console.error('Error controlling polling:', error);
    }
  };

  if (loading) {
    return (
      <Layout>
        <div className="flex items-center justify-center h-64">
          <RefreshCw className="h-8 w-8 animate-spin text-purple-600" />
        </div>
      </Layout>
    );
  }

  return (
    <Layout>
      <div className="space-y-8">
        <div className="flex justify-between items-center">
          <div>
            <h1 className="text-4xl font-bold text-slate-800 mb-2">Dashboard</h1>
            <p className="text-slate-600">Monitor your automated email assistant performance</p>
          </div>
          
          {/* Polling Control */}
          <div className="flex items-center gap-4">
            <Badge 
              variant={pollingStatus === 'running' ? 'default' : 'secondary'}
              className="px-3 py-1"
            >
              {pollingStatus === 'running' ? (
                <>
                  <Wifi className="h-4 w-4 mr-1" />
                  Live Polling
                </>
              ) : (
                <>
                  <WifiOff className="h-4 w-4 mr-1" />
                  Offline
                </>
              )}
            </Badge>
            <Button
              onClick={() => controlPolling(pollingStatus === 'running' ? 'stop' : 'start')}
              variant={pollingStatus === 'running' ? 'destructive' : 'default'}
              className="flex items-center gap-2"
            >
              {pollingStatus === 'running' ? (
                <>
                  <PowerOff className="h-4 w-4" />
                  Stop Polling
                </>
              ) : (
                <>
                  <Power className="h-4 w-4" />
                  Start Polling
                </>
              )}
            </Button>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          <Card className="bg-gradient-to-br from-blue-50 to-blue-100 border-blue-200">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium text-blue-800">Total Emails</CardTitle>
              <Mail className="h-4 w-4 text-blue-600" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-blue-900">{stats.total_emails || 0}</div>
            </CardContent>
          </Card>

          <Card className="bg-gradient-to-br from-green-50 to-green-100 border-green-200">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium text-green-800">Sent Emails</CardTitle>
              <SendHorizontal className="h-4 w-4 text-green-600" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-green-900">{stats.sent_emails || 0}</div>
              <p className="text-xs text-green-600 mt-1">
                {stats.processing_rate ? `${stats.processing_rate.toFixed(1)}% success rate` : ''}
              </p>
            </CardContent>
          </Card>

          <Card className="bg-gradient-to-br from-amber-50 to-amber-100 border-amber-200">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium text-amber-800">Escalated</CardTitle>
              <AlertCircle className="h-4 w-4 text-amber-600" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-amber-900">{stats.escalated_emails || 0}</div>
            </CardContent>
          </Card>

          <Card className="bg-gradient-to-br from-purple-50 to-purple-100 border-purple-200">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium text-purple-800">Active Accounts</CardTitle>
              <Shield className="h-4 w-4 text-purple-600" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-purple-900">
                {stats.active_accounts || 0}/{stats.total_accounts || 0}
              </div>
            </CardContent>
          </Card>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          <Card className="shadow-lg">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Settings className="h-5 w-5 text-purple-600" />
                Quick Actions
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <Button 
                onClick={() => navigate('/monitoring')} 
                className="w-full bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-700 hover:to-pink-700"
              >
                <Activity className="h-4 w-4 mr-2" />
                Live Email Monitoring
              </Button>
              <Button 
                onClick={() => navigate('/test')} 
                variant="outline" 
                className="w-full"
              >
                <Zap className="h-4 w-4 mr-2" />
                Test Email Processing
              </Button>
              <Button 
                onClick={() => navigate('/intents')} 
                variant="outline" 
                className="w-full"
              >
                <Brain className="h-4 w-4 mr-2" />
                Manage Intents
              </Button>
              <Button 
                onClick={() => navigate('/accounts')} 
                variant="outline" 
                className="w-full"
              >
                <Mail className="h-4 w-4 mr-2" />
                Setup Email Accounts
              </Button>
            </CardContent>
          </Card>

          <Card className="shadow-lg">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <BarChart3 className="h-5 w-5 text-blue-600" />
                System Status
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center justify-between">
                <span>Email Polling</span>
                <Badge variant={pollingStatus === 'running' ? "default" : "secondary"}>
                  {pollingStatus === 'running' ? 'Active' : 'Stopped'}
                </Badge>
              </div>
              <div className="flex items-center justify-between">
                <span>Email Accounts</span>
                <Badge variant={stats.active_accounts > 0 ? "default" : "secondary"}>
                  {stats.active_accounts || 0} active
                </Badge>
              </div>
              <div className="flex items-center justify-between">
                <span>Intent Detection</span>
                <Badge variant={stats.total_intents > 0 ? "default" : "secondary"}>
                  {stats.total_intents > 0 ? "Ready" : "Setup needed"}
                </Badge>
              </div>
              <div className="flex items-center justify-between">
                <span>AI Processing</span>
                <Badge variant="default">Online</Badge>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </Layout>
  );
};

// Email Monitoring Component
const EmailMonitoring = () => {
  const navigate = useNavigate();
  const [emails, setEmails] = useState([]);
  const [pollingStatus, setPollingStatus] = useState('stopped');
  const [autoRefresh, setAutoRefresh] = useState(true);

  useEffect(() => {
    fetchEmails();
    fetchPollingStatus();
    
    let interval;
    if (autoRefresh) {
      interval = setInterval(() => {
        fetchEmails();
        fetchPollingStatus();
      }, 10000); // Refresh every 10 seconds
    }
    
    return () => {
      if (interval) clearInterval(interval);
    };
  }, [autoRefresh]);

  const fetchEmails = async () => {
    try {
      const response = await axios.get(`${API}/emails`);
      setEmails(response.data);
    } catch (error) {
      console.error('Error fetching emails:', error);
    }
  };

  const fetchPollingStatus = async () => {
    try {
      const response = await axios.get(`${API}/polling/status`);
      setPollingStatus(response.data.status);
    } catch (error) {
      console.error('Error fetching polling status:', error);
    }
  };

  const sendEmail = async (emailId) => {
    try {
      await axios.post(`${API}/emails/${emailId}/send`, { manual_override: false });
      fetchEmails();
    } catch (error) {
      console.error('Error sending email:', error);
    }
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'sent': return 'bg-green-100 text-green-800 border-green-200';
      case 'ready_to_send': return 'bg-blue-100 text-blue-800 border-blue-200';
      case 'processing': return 'bg-yellow-100 text-yellow-800 border-yellow-200';
      case 'needs_redraft': return 'bg-amber-100 text-amber-800 border-amber-200';
      case 'escalate': return 'bg-red-100 text-red-800 border-red-200';
      case 'error': return 'bg-red-100 text-red-800 border-red-200';
      case 'new': return 'bg-purple-100 text-purple-800 border-purple-200';
      default: return 'bg-slate-100 text-slate-800 border-slate-200';
    }
  };

  const getStatusIcon = (status) => {
    switch (status) {
      case 'sent': return <CheckCircle className="h-4 w-4" />;
      case 'ready_to_send': return <Send className="h-4 w-4" />;
      case 'processing': return <RefreshCw className="h-4 w-4 animate-spin" />;
      case 'needs_redraft': return <AlertCircle className="h-4 w-4" />;
      case 'escalate': return <AlertCircle className="h-4 w-4" />;
      case 'error': return <AlertCircle className="h-4 w-4" />;
      case 'new': return <Inbox className="h-4 w-4" />;
      default: return <Clock className="h-4 w-4" />;
    }
  };

  return (
    <Layout>
      <div className="space-y-8">
        <div className="flex justify-between items-center">
          <div>
            <h1 className="text-4xl font-bold text-slate-800 mb-2">Live Email Monitoring</h1>
            <p className="text-slate-600">Real-time monitoring of email processing and responses</p>
          </div>
          
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2">
              <Label htmlFor="auto-refresh">Auto Refresh</Label>
              <Switch
                id="auto-refresh"
                checked={autoRefresh}
                onCheckedChange={setAutoRefresh}
              />
            </div>
            <Badge 
              variant={pollingStatus === 'running' ? 'default' : 'secondary'}
              className="px-3 py-1"
            >
              {pollingStatus === 'running' ? (
                <>
                  <Activity className="h-4 w-4 mr-1 animate-pulse" />
                  Live
                </>
              ) : (
                <>
                  <WifiOff className="h-4 w-4 mr-1" />
                  Offline
                </>
              )}
            </Badge>
          </div>
        </div>

        {pollingStatus !== 'running' && (
          <Alert>
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>
              Email polling is currently stopped. Go to Dashboard to start live email monitoring.
            </AlertDescription>
          </Alert>
        )}

        <div className="grid gap-4">
          {emails.slice(0, 20).map(email => (
            <Card key={email.id} className="shadow-md hover:shadow-lg transition-shadow">
              <CardHeader className="pb-3">
                <div className="flex justify-between items-start">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-2">
                      <Badge className={getStatusColor(email.status)} variant="outline">
                        {getStatusIcon(email.status)}
                        <span className="ml-1">{email.status ? email.status.replace('_', ' ') : 'unknown'}</span>
                      </Badge>
                      <span className="text-sm text-slate-500">
                        {new Date(email.received_at).toLocaleString()}
                      </span>
                    </div>
                    <CardTitle className="text-lg mb-1">{email.subject}</CardTitle>
                    <CardDescription>
                      From: {email.sender}
                    </CardDescription>
                  </div>
                  
                  <div className="flex gap-2">
                    {email.status === 'ready_to_send' && (
                      <Button
                        size="sm"
                        onClick={() => sendEmail(email.id)}
                        className="bg-green-600 hover:bg-green-700"
                      >
                        <Send className="h-4 w-4 mr-1" />
                        Send
                      </Button>
                    )}
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => navigate('/emails')}
                    >
                      <Eye className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
                
                {/* Quick Preview */}
                {email.intents && email.intents.length > 0 && (
                  <div className="mt-3 pt-3 border-t">
                    <div className="flex flex-wrap gap-2">
                      {email.intents && email.intents.map((intent, index) => (
                        <Badge key={index} variant="secondary" className="text-xs">
                          {intent.name} ({(intent.confidence * 100).toFixed(1)}%)
                        </Badge>
                      ))}
                    </div>
                  </div>
                )}
                
                {email.draft && (
                  <div className="mt-2 p-3 bg-slate-50 rounded-lg">
                    <p className="text-sm text-slate-700 line-clamp-2">
                      {email.draft.substring(0, 150)}...
                    </p>
                  </div>
                )}
              </CardHeader>
            </Card>
          ))}
          
          {emails.length === 0 && (
            <Card className="text-center py-12">
              <CardContent>
                <Inbox className="h-12 w-12 text-slate-400 mx-auto mb-4" />
                <h3 className="text-lg font-medium text-slate-600 mb-2">No emails yet</h3>
                <p className="text-slate-500">
                  {pollingStatus === 'running' 
                    ? 'Waiting for incoming emails...' 
                    : 'Start email polling to begin monitoring'}
                </p>
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </Layout>
  );
};

// Intent Management Component
const IntentManagement = () => {
  const [intents, setIntents] = useState([]);
  const [isCreating, setIsCreating] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [editingIntent, setEditingIntent] = useState(null);
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    examples: [''],
    system_prompt: '',
    confidence_threshold: 0.7,
    follow_up_hours: 24,
    is_meeting_related: false
  });

  useEffect(() => {
    fetchIntents();
  }, []);

  const fetchIntents = async () => {
    try {
      const response = await axios.get(`${API}/intents`);
      setIntents(response.data);
    } catch (error) {
      console.error('Error fetching intents:', error);
    }
  };

  const handleCreateIntent = async (e) => {
    e.preventDefault();
    try {
      const intentData = {
        ...formData,
        examples: formData.examples.filter(ex => ex.trim() !== '')
      };
      await axios.post(`${API}/intents`, intentData);
      setIsCreating(false);
      resetForm();
      fetchIntents();
    } catch (error) {
      console.error('Error creating intent:', error);
    }
  };

  const handleEditIntent = (intent) => {
    setEditingIntent(intent);
    setFormData({
      name: intent.name,
      description: intent.description,
      examples: intent.examples && intent.examples.length > 0 ? intent.examples : [''],
      system_prompt: intent.system_prompt || '',
      confidence_threshold: intent.confidence_threshold,
      follow_up_hours: intent.follow_up_hours,
      is_meeting_related: intent.is_meeting_related || false
    });
    setIsEditing(true);
  };

  const handleUpdateIntent = async (e) => {
    e.preventDefault();
    try {
      const intentData = {
        ...formData,
        examples: formData.examples.filter(ex => ex.trim() !== '')
      };
      await axios.put(`${API}/intents/${editingIntent.id}`, intentData);
      setIsEditing(false);
      setEditingIntent(null);
      resetForm();
      fetchIntents();
    } catch (error) {
      console.error('Error updating intent:', error);
    }
  };

  const resetForm = () => {
    setFormData({
      name: '',
      description: '',
      examples: [''],
      system_prompt: '',
      confidence_threshold: 0.7,
      follow_up_hours: 24,
      is_meeting_related: false
    });
  };

  const handleDeleteIntent = async (intentId) => {
    try {
      await axios.delete(`${API}/intents/${intentId}`);
      fetchIntents();
    } catch (error) {
      console.error('Error deleting intent:', error);
    }
  };

  const addExample = () => {
    setFormData(prev => ({
      ...prev,
      examples: [...prev.examples, '']
    }));
  };

  const updateExample = (index, value) => {
    setFormData(prev => ({
      ...prev,
      examples: prev.examples.map((ex, i) => i === index ? value : ex)
    }));
  };

  return (
    <Layout>
      <div className="space-y-8">
        <div className="flex justify-between items-center">
          <div>
            <h1 className="text-4xl font-bold text-slate-800 mb-2">Intent Management</h1>
            <p className="text-slate-600">Define how your AI assistant should classify and respond to emails</p>
          </div>
          <Button 
            onClick={() => setIsCreating(true)}
            className="bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-700 hover:to-pink-700"
          >
            <Plus className="h-4 w-4 mr-2" />
            Create Intent
          </Button>
        </div>

        {/* Create/Edit Intent Dialog */}
        <Dialog open={isCreating || isEditing} onOpenChange={(open) => {
          if (!open) {
            setIsCreating(false);
            setIsEditing(false);
            setEditingIntent(null);
            resetForm();
          }
        }}>
          <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
            <DialogHeader>
              <DialogTitle>{isEditing ? 'Edit Intent' : 'Create New Intent'}</DialogTitle>
              <DialogDescription>
                {isEditing ? 'Update the intent configuration.' : 'Define a new intent that your AI assistant can recognize and respond to.'}
              </DialogDescription>
            </DialogHeader>
            <form onSubmit={isEditing ? handleUpdateIntent : handleCreateIntent} className="space-y-6">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label htmlFor="name">Intent Name</Label>
                  <Input
                    id="name"
                    value={formData.name}
                    onChange={(e) => setFormData(prev => ({ ...prev, name: e.target.value }))}
                    placeholder="e.g., Product Inquiry"
                    required
                  />
                </div>
                <div>
                  <Label htmlFor="confidence">Confidence Threshold</Label>
                  <Input
                    id="confidence"
                    type="number"
                    min="0"
                    max="1"
                    step="0.1"
                    value={formData.confidence_threshold}
                    onChange={(e) => setFormData(prev => ({ ...prev, confidence_threshold: parseFloat(e.target.value) }))}
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label htmlFor="follow_up_hours">Follow-up Duration (hours)</Label>
                  <Input
                    id="follow_up_hours"
                    type="number"
                    min="1"
                    max="168"
                    value={formData.follow_up_hours}
                    onChange={(e) => setFormData(prev => ({ ...prev, follow_up_hours: parseInt(e.target.value) }))}
                  />
                  <p className="text-xs text-slate-500 mt-1">
                    Time to wait before sending first follow-up
                  </p>
                </div>
                <div className="flex items-center space-x-2 pt-6">
                  <Switch
                    id="is_meeting_related"
                    checked={formData.is_meeting_related}
                    onCheckedChange={(checked) => setFormData(prev => ({ ...prev, is_meeting_related: checked }))}
                  />
                  <Label htmlFor="is_meeting_related" className="text-sm">
                    Meeting related intent
                  </Label>
                </div>
              </div>

              <div>
                <Label htmlFor="description">Description</Label>
                <Textarea
                  id="description"
                  value={formData.description}
                  onChange={(e) => setFormData(prev => ({ ...prev, description: e.target.value }))}
                  placeholder="Describe what this intent represents..."
                  required
                />
              </div>

              <div>
                <Label>Example Phrases</Label>
                {formData.examples.map((example, index) => (
                  <div key={index} className="flex gap-2 mt-2">
                    <Input
                      value={example}
                      onChange={(e) => updateExample(index, e.target.value)}
                      placeholder="Example email phrase..."
                    />
                    {formData.examples.length > 1 && (
                      <Button
                        type="button"
                        variant="outline"
                        size="sm"
                        onClick={() => setFormData(prev => ({
                          ...prev,
                          examples: prev.examples.filter((_, i) => i !== index)
                        }))}
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    )}
                  </div>
                ))}
                <Button type="button" variant="outline" onClick={addExample} className="mt-2">
                  <Plus className="h-4 w-4 mr-2" />
                  Add Example
                </Button>
              </div>

              <div>
                <Label htmlFor="system_prompt">System Prompt (Optional)</Label>
                <Textarea
                  id="system_prompt"
                  value={formData.system_prompt}
                  onChange={(e) => setFormData(prev => ({ ...prev, system_prompt: e.target.value }))}
                  placeholder="Additional instructions for AI when this intent is detected..."
                />
              </div>

              <div className="flex justify-end gap-2">
                <Button type="button" variant="outline" onClick={() => {
                  setIsCreating(false);
                  setIsEditing(false);
                  setEditingIntent(null);
                  resetForm();
                }}>
                  Cancel
                </Button>
                <Button type="submit" className="bg-gradient-to-r from-purple-600 to-pink-600">
                  {isEditing ? 'Update Intent' : 'Create Intent'}
                </Button>
              </div>
            </form>
          </DialogContent>
        </Dialog>

        {/* Intents List */}
        <div className="grid gap-6">
          {intents.map(intent => (
            <Card key={intent.id} className="shadow-lg hover:shadow-xl transition-shadow">
              <CardHeader>
                <div className="flex justify-between items-start">
                  <div>
                    <CardTitle className="flex items-center gap-2">
                      <Brain className="h-5 w-5 text-purple-600" />
                      {intent.name}
                      {intent.is_meeting_related && (
                        <Badge variant="secondary">Meeting Related</Badge>
                      )}
                    </CardTitle>
                    <CardDescription>{intent.description}</CardDescription>
                  </div>
                  <div className="flex gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleEditIntent(intent)}
                      className="text-blue-600 hover:text-blue-700"
                    >
                      <Settings className="h-4 w-4" />
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleDeleteIntent(intent.id)}
                      className="text-red-600 hover:text-red-700"
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
                  <div>
                    <span className="font-medium text-slate-700">Confidence Threshold:</span>
                    <div className="text-slate-600">{(intent.confidence_threshold * 100).toFixed(0)}%</div>
                  </div>
                  <div>
                    <span className="font-medium text-slate-700">Follow-up Time:</span>
                    <div className="text-slate-600">{intent.follow_up_hours}h</div>
                  </div>
                  <div>
                    <span className="font-medium text-slate-700">Examples:</span>
                    <div className="text-slate-600">{intent.examples?.length || 0} defined</div>
                  </div>
                </div>
                {intent.examples && intent.examples.length > 0 && (
                  <div className="mt-4">
                    <span className="font-medium text-slate-700 text-sm">Example Phrases:</span>
                    <div className="flex flex-wrap gap-2 mt-2">
                      {intent.examples && intent.examples.slice(0, 3).map((example, index) => (
                        <Badge key={index} variant="outline" className="text-xs">
                          {example.substring(0, 50)}{example.length > 50 ? '...' : ''}
                        </Badge>
                      ))}
                      {intent.examples.length > 3 && (
                        <Badge variant="outline" className="text-xs">
                          +{intent.examples.length - 3} more
                        </Badge>
                      )}
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>
          ))}
          
          {intents.length === 0 && (
            <Card className="text-center py-12">
              <CardContent>
                <Brain className="h-12 w-12 text-slate-400 mx-auto mb-4" />
                <h3 className="text-lg font-medium text-slate-600 mb-2">No intents defined yet</h3>
                <p className="text-slate-500 mb-4">Create your first intent to start classifying emails</p>
                <Button 
                  onClick={() => setIsCreating(true)}
                  className="bg-gradient-to-r from-purple-600 to-pink-600"
                >
                  <Plus className="h-4 w-4 mr-2" />
                  Create First Intent
                </Button>
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </Layout>
  );
};

// Email Accounts Component with OAuth Support
const EmailAccounts = () => {
  const [accounts, setAccounts] = useState([]);
  const [oauthStatus, setOauthStatus] = useState(null);
  const [microsoftOauthStatus, setMicrosoftOauthStatus] = useState(null);
  const [isCreating, setIsCreating] = useState(false);
  const [accountType, setAccountType] = useState('manual'); // 'manual' or 'oauth'
  const [oauthProvider, setOauthProvider] = useState('google'); // 'google' or 'microsoft'
  const [formData, setFormData] = useState({
    name: '',
    email: '',
    provider: 'gmail',
    username: '',
    password: '',
    imap_server: '',
    imap_port: 993,
    smtp_server: '',
    smtp_port: 587,
    signature: 'Best regards,<br>[Your Name]<br>[Your Title]<br>[Company Name]',
    persona: 'I am a professional and helpful assistant representing this organization. I respond courteously to all inquiries and provide accurate, relevant information.',
    is_active: true,
    // Follow-up settings
    enable_follow_ups: true,
    follow_up_hours_override: null,
    max_follow_ups_override: null,
    custom_follow_up_template: ''
  });
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');

  useEffect(() => {
    fetchAccounts();
    fetchOAuthStatus();
    fetchMicrosoftOAuthStatus();
  }, []);

  const fetchAccounts = async () => {
    try {
      const response = await axios.get(`${API}/email-accounts`);
      setAccounts(response.data);
    } catch (error) {
      console.error('Error fetching accounts:', error);
    }
  };

  const fetchOAuthStatus = async () => {
    try {
      const response = await axios.get(`${API}/oauth/google/status`);
      setOauthStatus(response.data);
    } catch (error) {
      console.error('Error fetching OAuth status:', error);
      setOauthStatus({ is_authorized: false, authorized_services: [] });
    }
  };

  const fetchMicrosoftOAuthStatus = async () => {
    try {
      const response = await axios.get(`${API}/oauth/microsoft/status`);
      setMicrosoftOauthStatus(response.data);
    } catch (error) {
      console.error('Error fetching Microsoft OAuth status:', error);
      setMicrosoftOauthStatus({ is_authorized: false, authorized_services: [] });
    }
  };

  const initiateGoogleOAuth = async () => {
    setLoading(true);
    try {
      const response = await axios.post(`${API}/oauth/google/authorize`, ['email', 'calendar']);
      // Redirect to Google OAuth
      window.location.href = response.data.auth_url;
    } catch (error) {
      const errorDetail = error.response?.data?.detail;
      setMessage(typeof errorDetail === 'object' ? JSON.stringify(errorDetail) : (errorDetail || 'OAuth initiation failed'));
      setLoading(false);
    }
  };

  const initiateMicrosoftOAuth = async () => {
    setLoading(true);
    try {
      const response = await axios.post(`${API}/oauth/microsoft/authorize`, ['email', 'calendar']);
      // Redirect to Microsoft OAuth
      window.location.href = response.data.auth_url;
    } catch (error) {
      setMessage(error.response?.data?.detail || 'Microsoft OAuth initiation failed');
      setLoading(false);
    }
  };

  const createOAuthAccount = async () => {
    setLoading(true);
    try {
      const provider = oauthProvider === 'google' ? 'gmail' : 'outlook';
      const oauthEmail = oauthProvider === 'google' 
        ? oauthStatus?.user_email 
        : microsoftOauthStatus?.user_email;
        
      const accountData = {
        name: formData.name,
        email: oauthEmail || formData.email,
        provider: provider,
        auth_type: 'oauth',
        use_oauth: true,
        signature: formData.signature,
        persona: formData.persona,
        is_active: formData.is_active,
        enable_follow_ups: formData.enable_follow_ups,
        follow_up_hours_override: formData.follow_up_hours_override,
        max_follow_ups_override: formData.max_follow_ups_override,
        custom_follow_up_template: formData.custom_follow_up_template
      };

      await axios.post(`${API}/email-accounts/oauth`, accountData);
      setMessage('✅ Email account and calendar successfully connected!');
      setIsCreating(false);
      resetForm();
      fetchAccounts();
      fetchOAuthStatus();
      fetchMicrosoftOAuthStatus();
    } catch (error) {
      setMessage(error.response?.data?.detail || 'Error creating OAuth account');
    }
    setLoading(false);
  };

  const handleCreateAccount = async (e) => {
    e.preventDefault();
    
    if (accountType === 'oauth') {
      // Check OAuth status based on selected provider
      if (oauthProvider === 'google') {
        if (!oauthStatus?.is_authorized || !oauthStatus?.authorized_services?.includes('email')) {
          // Initiate OAuth flow if not authorized
          await initiateGoogleOAuth();
          return;
        }
      } else if (oauthProvider === 'microsoft') {
        if (!microsoftOauthStatus?.is_authorized || !microsoftOauthStatus?.authorized_services?.includes('email')) {
          // Initiate OAuth flow if not authorized
          await initiateMicrosoftOAuth();
          return;
        }
      }
      await createOAuthAccount();
    } else {
      // Existing manual account creation logic
      setLoading(true);
      setMessage('');

      try {
        const provider_config = EMAIL_PROVIDERS[formData.provider];
        const accountData = {
          ...formData,
          imap_server: formData.imap_server || provider_config.imap_server,
          imap_port: formData.imap_port || provider_config.imap_port,
          smtp_server: formData.smtp_server || provider_config.smtp_server,
          smtp_port: formData.smtp_port || provider_config.smtp_port,
          auth_type: 'manual',
          use_oauth: false
        };

        await axios.post(`${API}/email-accounts`, accountData);
        setMessage('Email account created successfully!');
        setIsCreating(false);
        resetForm();
        fetchAccounts();
      } catch (error) {
        setMessage(error.response?.data?.detail || 'Error creating account');
      }
      setLoading(false);
    }
  };

  const handleDeleteAccount = async (accountId) => {
    try {
      await axios.delete(`${API}/email-accounts/${accountId}`);
      fetchAccounts();
    } catch (error) {
      console.error('Error deleting account:', error);
    }
  };

  const toggleAccount = async (accountId, isActive) => {
    try {
      await axios.patch(`${API}/email-accounts/${accountId}/toggle`, {
        is_active: !isActive
      });
      fetchAccounts();
    } catch (error) {
      console.error('Error toggling account:', error);
    }
  };

  const resetForm = () => {
    setFormData({
      name: '',
      email: '',
      provider: 'gmail',
      username: '',
      password: '',
      imap_server: '',
      imap_port: 993,
      smtp_server: '',
      smtp_port: 587,
      signature: '',
      persona: '',
      is_active: true
    });
    setAccountType('manual');
  };

  const revokeGoogleOAuth = async () => {
    setLoading(true);
    try {
      await axios.post(`${API}/oauth/google/revoke`);
      setMessage('Google OAuth access revoked successfully');
      fetchOAuthStatus();
      fetchAccounts(); // Refresh accounts as OAuth accounts may be affected
    } catch (error) {
      setMessage(error.response?.data?.detail || 'Error revoking Google OAuth access');
    }
    setLoading(false);
  };

  const revokeMicrosoftOAuth = async () => {
    setLoading(true);
    try {
      await axios.post(`${API}/oauth/microsoft/revoke`);
      setMessage('Microsoft OAuth access revoked successfully');
      fetchMicrosoftOAuthStatus();
      fetchAccounts(); // Refresh accounts as OAuth accounts may be affected
    } catch (error) {
      setMessage(error.response?.data?.detail || 'Error revoking Microsoft OAuth access');
    }
    setLoading(false);
  };

  return (
    <Layout>
      <div className="space-y-8">
        <div className="flex justify-between items-center">
          <div>
            <h1 className="text-4xl font-bold text-slate-800 mb-2">Email Accounts</h1>
            <p className="text-slate-600">Manage your email accounts for automated processing</p>
          </div>
          <Button 
            onClick={() => setIsCreating(true)}
            className="bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-700 hover:to-pink-700"
          >
            <Plus className="h-4 w-4 mr-2" />
            Add Account
          </Button>
        </div>

        {message && (
          <Alert className={(typeof message === 'string' && message.includes('success')) ? 'border-green-200 bg-green-50' : 'border-red-200 bg-red-50'}>
            <AlertCircle className={`h-4 w-4 ${(typeof message === 'string' && message.includes('success')) ? 'text-green-600' : 'text-red-600'}`} />
            <AlertDescription className={(typeof message === 'string' && message.includes('success')) ? 'text-green-700' : 'text-red-700'}>
              {typeof message === 'object' ? JSON.stringify(message, null, 2) : message}
            </AlertDescription>
          </Alert>
        )}

        {/* Create Account Dialog */}
        <Dialog open={isCreating} onOpenChange={(open) => {
          if (!open) {
            setIsCreating(false);
            resetForm();
            setMessage('');
          }
        }}>
          <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
            <DialogHeader>
              <DialogTitle>Add Email Account</DialogTitle>
              <DialogDescription>
                Connect your email account for automated processing
              </DialogDescription>
            </DialogHeader>
            
            <div className="space-y-6">
              <form onSubmit={handleCreateAccount} className="space-y-6">
                {/* Account Name Field */}
                <div>
                  <Label htmlFor="name">Account Name</Label>
                  <Input
                    id="name"
                    value={formData.name}
                    onChange={(e) => setFormData(prev => ({ ...prev, name: e.target.value }))}
                    placeholder="My Gmail Account"
                    required
                  />
                </div>

                {/* Account Type Selection */}
                <div>
                  <Label>Account Type</Label>
                  <Tabs value={accountType} onValueChange={setAccountType} className="mt-2">
                    <TabsList className="grid w-full grid-cols-2">
                      <TabsTrigger value="oauth" className="flex items-center gap-2">
                        <Shield className="h-4 w-4" />
                        OAuth (Recommended)
                      </TabsTrigger>
                      <TabsTrigger value="manual" className="flex items-center gap-2">
                        <Settings className="h-4 w-4" />
                        Manual Setup
                      </TabsTrigger>
                    </TabsList>

                    {/* OAuth-specific UI - Simplified Icon-Based */}
                    <TabsContent value="oauth" className="space-y-4 mt-4">
                      <div className="bg-gradient-to-r from-blue-50 to-purple-50 border border-blue-200 rounded-lg p-4">
                        <div className="flex items-start gap-3">
                          <Shield className="h-5 w-5 text-blue-600 mt-0.5" />
                          <div>
                            <h4 className="font-medium text-blue-900">Connect with OAuth</h4>
                            <p className="text-sm text-blue-700 mt-1">
                              Secure authentication without storing passwords. Calendar access will be automatically configured.
                            </p>
                          </div>
                        </div>
                      </div>

                      {/* Provider Icons - Simplified */}
                      <div>
                        <Label className="mb-3 block">Choose Provider</Label>
                        <div className="flex justify-center gap-6 py-4">
                          {/* Google Icon */}
                          <button
                            type="button"
                            onClick={() => {
                              setOauthProvider('google');
                              if (!oauthStatus?.is_authorized || !oauthStatus?.authorized_services?.includes('email')) {
                                initiateGoogleOAuth();
                              }
                            }}
                            disabled={loading}
                            className="relative group"
                          >
                            <div className={`p-6 border-2 rounded-2xl transition-all hover:shadow-lg ${
                              oauthProvider === 'google'
                                ? 'border-blue-500 bg-blue-50 shadow-md'
                                : 'border-gray-200 hover:border-blue-300 bg-white'
                            }`}>
                              <img src="/google-logo.svg" alt="Google" className="h-12 w-12" />
                              {oauthStatus?.is_authorized && oauthStatus?.authorized_services?.includes('email') && (
                                <div className="absolute -top-2 -right-2 bg-green-500 rounded-full p-1">
                                  <CheckCircle className="h-5 w-5 text-white" />
                                </div>
                              )}
                            </div>
                            <p className="text-sm font-medium text-center mt-2 text-slate-700">Google</p>
                            {oauthStatus?.is_authorized && oauthStatus?.authorized_services?.includes('email') && (
                              <p className="text-xs text-green-600 text-center">Authorized</p>
                            )}
                          </button>

                          {/* Microsoft Icon */}
                          <button
                            type="button"
                            onClick={() => {
                              setOauthProvider('microsoft');
                              if (!microsoftOauthStatus?.is_authorized || !microsoftOauthStatus?.authorized_services?.includes('email')) {
                                initiateMicrosoftOAuth();
                              }
                            }}
                            disabled={loading}
                            className="relative group"
                          >
                            <div className={`p-6 border-2 rounded-2xl transition-all hover:shadow-lg ${
                              oauthProvider === 'microsoft'
                                ? 'border-orange-500 bg-orange-50 shadow-md'
                                : 'border-gray-200 hover:border-orange-300 bg-white'
                            }`}>
                              <img src="/microsoft-logo.svg" alt="Microsoft" className="h-12 w-12" />
                              {microsoftOauthStatus?.is_authorized && microsoftOauthStatus?.authorized_services?.includes('email') && (
                                <div className="absolute -top-2 -right-2 bg-green-500 rounded-full p-1">
                                  <CheckCircle className="h-5 w-5 text-white" />
                                </div>
                              )}
                            </div>
                            <p className="text-sm font-medium text-center mt-2 text-slate-700">Microsoft</p>
                            {microsoftOauthStatus?.is_authorized && microsoftOauthStatus?.authorized_services?.includes('email') && (
                              <p className="text-xs text-green-600 text-center">Authorized</p>
                            )}
                          </button>
                        </div>
                      </div>

                      {/* Show current authorization status */}
                      {oauthProvider === 'google' && oauthStatus?.is_authorized && oauthStatus?.authorized_services?.includes('email') && (
                        <Alert className="border-green-200 bg-green-50">
                          <CheckCircle className="h-4 w-4 text-green-600" />
                          <AlertDescription className="text-green-700">
                            Connected: {oauthStatus.user_email}
                          </AlertDescription>
                        </Alert>
                      )}

                      {oauthProvider === 'microsoft' && microsoftOauthStatus?.is_authorized && microsoftOauthStatus?.authorized_services?.includes('email') && (
                        <Alert className="border-green-200 bg-green-50">
                          <CheckCircle className="h-4 w-4 text-green-600" />
                          <AlertDescription className="text-green-700">
                            Connected: {microsoftOauthStatus.user_email}
                          </AlertDescription>
                        </Alert>
                      )}
                    </TabsContent>

                    {/* Manual setup fields */}
                    <TabsContent value="manual" className="space-y-4 mt-4">
                      <div className="grid grid-cols-2 gap-4">
                        <div>
                          <Label htmlFor="email">Email Address</Label>
                          <Input
                            id="email"
                            type="email"
                            value={formData.email}
                            onChange={(e) => setFormData(prev => ({ ...prev, email: e.target.value }))}
                            placeholder="your@email.com"
                            required
                          />
                        </div>
                        <div>
                          <Label htmlFor="provider">Provider</Label>
                          <Select value={formData.provider} onValueChange={(value) => setFormData(prev => ({ ...prev, provider: value }))}>
                            <SelectTrigger>
                              <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                              <SelectItem value="gmail">Gmail</SelectItem>
                              <SelectItem value="outlook">Outlook/Hotmail</SelectItem>
                              <SelectItem value="yahoo">Yahoo Mail</SelectItem>
                              <SelectItem value="custom">Custom IMAP/SMTP</SelectItem>
                            </SelectContent>
                          </Select>
                        </div>
                      </div>

                      <div className="grid grid-cols-2 gap-4">
                        <div>
                          <Label htmlFor="username">Username/Email</Label>
                          <Input
                            id="username"
                            value={formData.username}
                            onChange={(e) => setFormData(prev => ({ ...prev, username: e.target.value }))}
                            placeholder="your@email.com"
                            required
                          />
                        </div>
                        <div>
                          <Label htmlFor="password">Password</Label>
                          <Input
                            id="password"
                            type="password"
                            value={formData.password}
                            onChange={(e) => setFormData(prev => ({ ...prev, password: e.target.value }))}
                            placeholder="Your email password"
                            required
                          />
                        </div>
                      </div>

                      <div className="grid grid-cols-2 gap-4">
                        <div>
                          <Label htmlFor="imap_server">IMAP Server</Label>
                          <Input
                            id="imap_server"
                            value={formData.imap_server}
                            onChange={(e) => setFormData(prev => ({ ...prev, imap_server: e.target.value }))}
                            placeholder="imap.gmail.com"
                          />
                        </div>
                        <div>
                          <Label htmlFor="imap_port">IMAP Port</Label>
                          <Input
                            id="imap_port"
                            type="number"
                            value={formData.imap_port}
                            onChange={(e) => setFormData(prev => ({ ...prev, imap_port: parseInt(e.target.value) }))}
                            placeholder="993"
                          />
                        </div>
                      </div>

                      <div className="grid grid-cols-2 gap-4">
                        <div>
                          <Label htmlFor="smtp_server">SMTP Server</Label>
                          <Input
                            id="smtp_server"
                            value={formData.smtp_server}
                            onChange={(e) => setFormData(prev => ({ ...prev, smtp_server: e.target.value }))}
                            placeholder="smtp.gmail.com"
                          />
                        </div>
                        <div>
                          <Label htmlFor="smtp_port">SMTP Port</Label>
                          <Input
                            id="smtp_port"
                            type="number"
                            value={formData.smtp_port}
                            onChange={(e) => setFormData(prev => ({ ...prev, smtp_port: parseInt(e.target.value) }))}
                            placeholder="587"
                          />
                        </div>
                      </div>
                    </TabsContent>
                  </Tabs>
                </div>

                {/* Email Persona Section */}
                <div className="space-y-4">
                  <div className="flex items-center gap-2 mb-4">
                    <User className="h-5 w-5 text-purple-600" />
                    <h3 className="text-lg font-semibold text-slate-800">AI Persona</h3>
                  </div>
                  
                  <div className="bg-purple-50 rounded-lg p-4">
                    <div>
                      <Label htmlFor="persona" className="text-sm font-medium mb-2">
                        Persona Description
                      </Label>
                      <textarea
                        id="persona"
                        name="persona"
                        value={formData.persona}
                        onChange={(e) => setFormData(prev => ({ ...prev, persona: e.target.value }))}
                        placeholder="I am a professional and helpful assistant representing this organization. I respond courteously to all inquiries and provide accurate, relevant information with a friendly and knowledgeable tone."
                        className="mt-2 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-purple-500 focus:ring-purple-500 min-h-[100px]"
                        rows={4}
                      />
                      <p className="text-xs text-slate-500 mt-2">
                        This persona defines how the AI will respond to emails - the tone, style, and approach it will use.
                      </p>
                    </div>
                  </div>
                </div>

                {/* Email Signature Section */}
                <div className="space-y-4">
                  <div className="flex items-center gap-2 mb-4">
                    <Edit3 className="h-5 w-5 text-blue-600" />
                    <h3 className="text-lg font-semibold text-slate-800">Email Signature</h3>
                  </div>
                  
                  <div className="bg-slate-50 rounded-lg p-4">
                    <div>
                      <Label htmlFor="signature" className="text-sm font-medium mb-2">
                        Signature Content
                      </Label>
                      <RichTextEditor
                        value={formData.signature}
                        onChange={(value) => setFormData(prev => ({ ...prev, signature: value }))}
                        placeholder="Best regards,<br>Your Name<br>Your Title<br>Company Name"
                        className="mt-2"
                      />
                      <p className="text-xs text-slate-500 mt-2">
                        This signature will be automatically added to all outgoing emails from this account.
                      </p>
                    </div>
                  </div>
                </div>

                {/* Follow-up Settings Section */}
                <div className="space-y-4">
                  <div className="flex items-center gap-2 mb-4">
                    <Timer className="h-5 w-5 text-purple-600" />
                    <h3 className="text-lg font-semibold text-slate-800">Follow-up Settings</h3>
                  </div>
                  
                  <div className="bg-slate-50 rounded-lg p-4 space-y-4">
                    <div className="flex items-center space-x-2">
                      <Switch
                        id="enable_follow_ups"
                        checked={formData.enable_follow_ups}
                        onCheckedChange={(checked) => setFormData(prev => ({ ...prev, enable_follow_ups: checked }))}
                      />
                      <Label htmlFor="enable_follow_ups" className="text-sm font-medium">
                        Enable automatic follow-ups for this account
                      </Label>
                    </div>

                    {formData.enable_follow_ups && (
                      <>
                        <div className="grid grid-cols-2 gap-4">
                          <div>
                            <Label htmlFor="follow_up_hours_override" className="text-sm">
                              Follow-up Duration Override (hours)
                            </Label>
                            <Input
                              id="follow_up_hours_override"
                              type="number"
                              min="1"
                              max="168"
                              value={formData.follow_up_hours_override || ''}
                              onChange={(e) => setFormData(prev => ({ 
                                ...prev, 
                                follow_up_hours_override: e.target.value ? parseInt(e.target.value) : null 
                              }))}
                              placeholder="Leave empty to use global setting"
                            />
                            <p className="text-xs text-slate-500 mt-1">
                              Override global follow-up timing for this account
                            </p>
                          </div>
                          
                          <div>
                            <Label htmlFor="max_follow_ups_override" className="text-sm">
                              Max Follow-ups Override
                            </Label>
                            <Input
                              id="max_follow_ups_override"
                              type="number"
                              min="1"
                              max="10"
                              value={formData.max_follow_ups_override || ''}
                              onChange={(e) => setFormData(prev => ({ 
                                ...prev, 
                                max_follow_ups_override: e.target.value ? parseInt(e.target.value) : null 
                              }))}
                              placeholder="Leave empty to use global setting"
                            />
                            <p className="text-xs text-slate-500 mt-1">
                              Override global max follow-ups for this account
                            </p>
                          </div>
                        </div>

                        <div>
                          <Label htmlFor="custom_follow_up_template" className="text-sm">
                            Custom Follow-up Template (Optional)
                          </Label>
                          <Textarea
                            id="custom_follow_up_template"
                            value={formData.custom_follow_up_template}
                            onChange={(e) => setFormData(prev => ({ ...prev, custom_follow_up_template: e.target.value }))}
                            placeholder="Enter a custom template for follow-up emails. Use {original_subject}, {original_sender}, {follow_up_number} as placeholders."
                            rows={3}
                          />
                          <p className="text-xs text-slate-500 mt-1">
                            Leave empty to use AI-generated follow-up content
                          </p>
                        </div>
                      </>
                    )}
                  </div>
                </div>

                <div className="flex justify-end gap-2">
                  <Button type="button" variant="outline" onClick={() => {
                    setIsCreating(false);
                    resetForm();
                    setMessage('');
                  }}>
                    Cancel
                  </Button>
                  <Button 
                    type="submit" 
                    disabled={loading}
                    className="bg-gradient-to-r from-purple-600 to-pink-600"
                  >
                    {loading ? (
                      <>
                        <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
                        Creating...
                      </>
                    ) : (
                      <>
                        <Plus className="h-4 w-4 mr-2" />
                        {accountType === 'oauth' && (oauthProvider === 'google' ? oauthStatus?.is_authorized : microsoftOauthStatus?.is_authorized) ? 'Add Account' : 'Create Account'}
                      </>
                    )}
                  </Button>
                </div>
              </form>
            </div>
          </DialogContent>
        </Dialog>

        {/* Accounts List */}
        <div className="grid gap-6">
          {accounts.map(account => (
            <Card key={account.id} className="shadow-lg hover:shadow-xl transition-shadow">
              <CardHeader>
                <div className="flex justify-between items-start">
                  <div>
                    <CardTitle className="flex items-center gap-2">
                      <Mail className="h-5 w-5 text-blue-600" />
                      {account.name}
                      <Badge variant={account.is_active ? "default" : "secondary"}>
                        {account.is_active ? "Active" : "Inactive"}
                      </Badge>
                      {account.use_oauth && (
                        <Badge variant="outline" className="bg-blue-50 text-blue-700 border-blue-200">
                          <Shield className="h-3 w-3 mr-1" />
                          OAuth
                        </Badge>
                      )}
                    </CardTitle>
                    <CardDescription>{account.email}</CardDescription>
                  </div>
                  <div className="flex gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => toggleAccount(account.id, account.is_active)}
                      className={account.is_active ? "text-orange-600 hover:text-orange-700" : "text-green-600 hover:text-green-700"}
                    >
                      {account.is_active ? <Pause className="h-4 w-4" /> : <Play className="h-4 w-4" />}
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleDeleteAccount(account.id)}
                      className="text-red-600 hover:text-red-700"
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                  <div>
                    <span className="font-medium text-slate-700">Provider:</span>
                    <div className="text-slate-600 capitalize">{account.provider}</div>
                  </div>
                  <div>
                    <span className="font-medium text-slate-700">Auth Type:</span>
                    <div className="text-slate-600 capitalize">
                      {account.use_oauth ? 'OAuth' : 'Manual'}
                    </div>
                  </div>
                  <div>
                    <span className="font-medium text-slate-700">Last Polled:</span>
                    <div className="text-slate-600">
                      {account.last_polled ? new Date(account.last_polled).toLocaleString() : 'Never'}
                    </div>
                  </div>
                  <div>
                    <span className="font-medium text-slate-700">Status:</span>
                    <div className={`${account.is_active ? 'text-green-600' : 'text-slate-600'}`}>
                      {account.is_active ? 'Polling Active' : 'Paused'}
                    </div>
                  </div>
                </div>
                
                {/* Follow-up Settings Display */}
                <div className="mt-4 pt-4 border-t border-slate-200">
                  <div className="flex items-center gap-2 mb-2">
                    <Timer className="h-4 w-4 text-purple-600" />
                    <span className="font-medium text-slate-700 text-sm">Follow-up Settings:</span>
                  </div>
                  <div className="grid grid-cols-2 md:grid-cols-3 gap-4 text-sm">
                    <div>
                      <span className="text-slate-600">Status:</span>
                      <div className={`font-medium ${account.enable_follow_ups ? 'text-green-600' : 'text-slate-500'}`}>
                        {account.enable_follow_ups ? 'Enabled' : 'Disabled'}
                      </div>
                    </div>
                    {account.enable_follow_ups && (
                      <>
                        <div>
                          <span className="text-slate-600">Duration Override:</span>
                          <div className="font-medium text-slate-700">
                            {account.follow_up_hours_override ? `${account.follow_up_hours_override}h` : 'Global'}
                          </div>
                        </div>
                        <div>
                          <span className="text-slate-600">Max Follow-ups:</span>
                          <div className="font-medium text-slate-700">
                            {account.max_follow_ups_override || 'Global'}
                          </div>
                        </div>
                      </>
                    )}
                  </div>
                  {account.custom_follow_up_template && (
                    <div className="mt-2">
                      <span className="text-slate-600 text-sm">Custom Template:</span>
                      <div className="text-slate-600 text-sm mt-1 bg-slate-50 rounded p-2">
                        {account.custom_follow_up_template.length > 100 
                          ? account.custom_follow_up_template.substring(0, 100) + '...'
                          : account.custom_follow_up_template
                        }
                      </div>
                    </div>
                  )}
                </div>
                
                {account.persona && (
                  <div className="mt-4 pt-4 border-t border-slate-200">
                    <span className="font-medium text-slate-700 text-sm">AI Persona:</span>
                    <div className="text-slate-600 text-sm mt-1 bg-purple-50 rounded p-2">
                      {account.persona.length > 150 
                        ? account.persona.substring(0, 150) + '...'
                        : account.persona
                      }
                    </div>
                  </div>
                )}
                
                {account.signature && (
                  <div className="mt-4 pt-4 border-t border-slate-200">
                    <span className="font-medium text-slate-700 text-sm">Signature:</span>
                    <div 
                      className="text-slate-600 text-sm mt-1 signature-display" 
                      dangerouslySetInnerHTML={{ __html: account.signature }}
                    />
                  </div>
                )}
              </CardContent>
            </Card>
          ))}
        </div>

        {accounts.length === 0 && (
          <Card className="text-center py-12">
            <CardContent>
              <Mail className="h-12 w-12 text-slate-400 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-slate-600 mb-2">No email accounts configured</h3>
              <p className="text-slate-500 mb-4">Add your first email account to start automated processing</p>
              <Button 
                onClick={() => setIsCreating(true)}
                className="bg-gradient-to-r from-purple-600 to-pink-600"
              >
                <Plus className="h-4 w-4 mr-2" />
                Add First Account
              </Button>
            </CardContent>
          </Card>
        )}
      </div>
    </Layout>
  );
};

// Knowledge Base Component
const KnowledgeBase = () => {
  const [knowledgeItems, setKnowledgeItems] = useState([]);
  const [isCreating, setIsCreating] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [editingKnowledge, setEditingKnowledge] = useState(null);
  const [formData, setFormData] = useState({
    title: '',
    content: '',
    tags: []
  });

  useEffect(() => {
    fetchKnowledgeBase();
  }, []);

  const fetchKnowledgeBase = async () => {
    try {
      const response = await axios.get(`${API}/knowledge-base`);
      setKnowledgeItems(response.data);
    } catch (error) {
      console.error('Error fetching knowledge base:', error);
    }
  };

  const handleCreateKnowledge = async (e) => {
    e.preventDefault();
    try {
      await axios.post(`${API}/knowledge-base`, formData);
      setIsCreating(false);
      resetKnowledgeForm();
      fetchKnowledgeBase();
    } catch (error) {
      console.error('Error creating knowledge item:', error);
    }
  };

  const handleEditKnowledge = (item) => {
    setEditingKnowledge(item);
    setFormData({
      title: item.title,
      content: item.content,
      tags: item.tags || []
    });
    setIsEditing(true);
  };

  const handleUpdateKnowledge = async (e) => {
    e.preventDefault();
    try {
      await axios.put(`${API}/knowledge-base/${editingKnowledge.id}`, formData);
      setIsEditing(false);
      setEditingKnowledge(null);
      resetKnowledgeForm();
      fetchKnowledgeBase();
    } catch (error) {
      console.error('Error updating knowledge item:', error);
    }
  };

  const resetKnowledgeForm = () => {
    setFormData({ title: '', content: '', tags: [] });
  };

  const handleDeleteKnowledge = async (kbId) => {
    try {
      await axios.delete(`${API}/knowledge-base/${kbId}`);
      fetchKnowledgeBase();
    } catch (error) {
      console.error('Error deleting knowledge item:', error);
    }
  };

  return (
    <Layout>
      <div className="space-y-8">
        <div className="flex justify-between items-center">
          <div>
            <h1 className="text-4xl font-bold text-slate-800 mb-2">Knowledge Base</h1>
            <p className="text-slate-600">Manage information that your AI assistant can reference in responses</p>
          </div>
          <Button 
            onClick={() => setIsCreating(true)}
            className="bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-700 hover:to-pink-700"
          >
            <Plus className="h-4 w-4 mr-2" />
            Add Knowledge
          </Button>
        </div>

        {/* Create/Edit Knowledge Dialog */}
        <Dialog open={isCreating || isEditing} onOpenChange={(open) => {
          if (!open) {
            setIsCreating(false);
            setIsEditing(false);
            setEditingKnowledge(null);
            resetKnowledgeForm();
          }
        }}>
          <DialogContent className="max-w-2xl">
            <DialogHeader>
              <DialogTitle>{isEditing ? 'Edit Knowledge Item' : 'Add Knowledge Item'}</DialogTitle>
              <DialogDescription>
                {isEditing ? 'Update knowledge information.' : 'Add information that your AI assistant can reference when generating responses.'}
              </DialogDescription>
            </DialogHeader>
            <form onSubmit={isEditing ? handleUpdateKnowledge : handleCreateKnowledge} className="space-y-6">
              <div>
                <Label htmlFor="title">Title</Label>
                <Input
                  id="title"
                  value={formData.title}
                  onChange={(e) => setFormData(prev => ({ ...prev, title: e.target.value }))}
                  placeholder="e.g., Product Pricing, Company Policy"
                  required
                />
              </div>

              <div>
                <Label htmlFor="content">Content</Label>
                <Textarea
                  id="content"
                  value={formData.content}
                  onChange={(e) => setFormData(prev => ({ ...prev, content: e.target.value }))}
                  placeholder="Enter the knowledge content that AI can reference..."
                  rows={8}
                  required
                />
              </div>

              <div>
                <Label htmlFor="tags">Tags (comma-separated)</Label>
                <Input
                  id="tags"
                  value={formData.tags.join(', ')}
                  onChange={(e) => setFormData(prev => ({ 
                    ...prev, 
                    tags: e.target.value.split(',').map(tag => tag.trim()).filter(tag => tag)
                  }))}
                  placeholder="pricing, policy, support, product"
                />
              </div>

              <div className="flex justify-end gap-2">
                <Button type="button" variant="outline" onClick={() => {
                  setIsCreating(false);
                  setIsEditing(false);
                  setEditingKnowledge(null);
                  resetKnowledgeForm();
                }}>
                  Cancel
                </Button>
                <Button type="submit" className="bg-gradient-to-r from-purple-600 to-pink-600">
                  {isEditing ? 'Update Knowledge' : 'Add Knowledge'}
                </Button>
              </div>
            </form>
          </DialogContent>
        </Dialog>

        {/* Knowledge Items List */}
        <div className="grid gap-6">
          {knowledgeItems.map(item => (
            <Card key={item.id} className="shadow-lg hover:shadow-xl transition-shadow">
              <CardHeader>
                <div className="flex justify-between items-start">
                  <div>
                    <CardTitle className="flex items-center gap-2">
                      <Database className="h-5 w-5 text-green-600" />
                      {item.title}
                    </CardTitle>
                    <CardDescription className="mt-2 line-clamp-2">
                      {item.content.substring(0, 200)}...
                    </CardDescription>
                  </div>
                  <div className="flex gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleEditKnowledge(item)}
                      className="text-blue-600 hover:text-blue-700"
                    >
                      <Settings className="h-4 w-4" />
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleDeleteKnowledge(item.id)}
                      className="text-red-600 hover:text-red-700"
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                {item.tags && item.tags.length > 0 && (
                  <div className="flex flex-wrap gap-2">
                    {item.tags.map((tag, index) => (
                      <Badge key={index} variant="outline" className="text-xs">
                        {tag}
                      </Badge>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          ))}
          
          {knowledgeItems.length === 0 && (
            <Card className="text-center py-12">
              <CardContent>
                <Database className="h-12 w-12 text-slate-400 mx-auto mb-4" />
                <h3 className="text-lg font-medium text-slate-600 mb-2">No knowledge items yet</h3>
                <p className="text-slate-500 mb-4">Add knowledge items to help your AI assistant provide better responses</p>
                <Button 
                  onClick={() => setIsCreating(true)}
                  className="bg-gradient-to-r from-purple-600 to-pink-600"
                >
                  <Plus className="h-4 w-4 mr-2" />
                  Add First Knowledge Item
                </Button>
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </Layout>
  );
};

// Email Processing Component
const EmailProcessing = () => {
  const [emailThreads, setEmailThreads] = useState([]);
  const [selectedEmail, setSelectedEmail] = useState(null);
  const [viewMode, setViewMode] = useState('threads'); // 'threads' or 'individual'

  useEffect(() => {
    fetchEmailThreads();
  }, []);

  const fetchEmailThreads = async () => {
    try {
      if (viewMode === 'threads') {
        const response = await axios.get(`${API}/emails/threads`);
        // Ensure each thread has proper structure
        const validThreads = response.data.filter(thread => 
          thread && thread.thread_id && thread.original_email
        );
        setEmailThreads(validThreads);
      } else {
        const response = await axios.get(`${API}/emails`);
        // For individual view, ensure each email has required properties
        const validEmails = response.data.filter(email => 
          email && email.id && email.hasOwnProperty('status')
        );
        setEmailThreads(validEmails);
      }
    } catch (error) {
      console.error('Error fetching email threads:', error);
      setEmailThreads([]); // Set empty array on error to prevent undefined errors
    }
  };

  // Update when view mode changes
  useEffect(() => {
    fetchEmailThreads();
  }, [viewMode]);

  const handleRedraft = async (emailId) => {
    try {
      await axios.post(`${API}/emails/${emailId}/redraft`);
      fetchEmailThreads();
    } catch (error) {
      console.error('Error redrafting email:', error);
    }
  };

  const handleSendEmail = async (emailId) => {
    try {
      await axios.post(`${API}/emails/${emailId}/send`, { manual_override: false });
      fetchEmailThreads();
    } catch (error) {
      console.error('Error sending email:', error);
    }
  };

  const handleSendFollowUp = async (followUpId) => {
    try {
      await axios.post(`${API}/follow-ups/${followUpId}/send`);
      fetchEmailThreads();
    } catch (error) {
      console.error('Error sending follow-up:', error);
    }
  };

  const handleCancelFollowUp = async (followUpId) => {
    try {
      await axios.delete(`${API}/follow-ups/${followUpId}`);
      fetchEmailThreads();
    } catch (error) {
      console.error('Error cancelling follow-up:', error);
    }
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'sent': return 'bg-green-100 text-green-800 border-green-200';
      case 'ready_to_send': return 'bg-blue-100 text-blue-800 border-blue-200';
      case 'processing': return 'bg-yellow-100 text-yellow-800 border-yellow-200';
      case 'needs_redraft': return 'bg-amber-100 text-amber-800 border-amber-200';
      case 'escalate': return 'bg-red-100 text-red-800 border-red-200';
      case 'error': return 'bg-red-100 text-red-800 border-red-200';
      case 'new': return 'bg-purple-100 text-purple-800 border-purple-200';
      default: return 'bg-slate-100 text-slate-800 border-slate-200';
    }
  };

  return (
    <Layout>
      <div className="space-y-8">
        <div className="flex justify-between items-center">
          <div>
            <h1 className="text-4xl font-bold text-slate-800 mb-2">Email Conversations</h1>
            <p className="text-slate-600">View threaded email conversations and manage follow-ups</p>
          </div>
          <div className="flex gap-2">
            <Button
              variant={viewMode === 'threads' ? 'default' : 'outline'}
              onClick={() => setViewMode('threads')}
            >
              <MessageSquare className="h-4 w-4 mr-2" />
              Threaded View
            </Button>
            <Button
              variant={viewMode === 'individual' ? 'default' : 'outline'}
              onClick={() => setViewMode('individual')}
            >
              <Mail className="h-4 w-4 mr-2" />
              Individual Emails
            </Button>
          </div>
        </div>

        <div className="grid gap-6">
          {viewMode === 'threads' ? (
            // Threaded Conversation View
            (emailThreads && Array.isArray(emailThreads) ? emailThreads : []).map(thread => (
              <Card key={thread.thread_id} className="shadow-lg hover:shadow-xl transition-shadow">
                <CardHeader>
                  <div className="flex justify-between items-start">
                    <div className="flex-1">
                      <CardTitle className="flex items-center gap-2 mb-2">
                        <MessageSquare className="h-5 w-5 text-blue-600" />
                        {thread.subject}
                        <Badge className={getStatusColor(thread.original_email?.status || 'unknown')}>
                          {thread.original_email?.status ? thread.original_email.status.replace('_', ' ') : 'unknown'}
                        </Badge>
                        {thread.has_response && (
                          <Badge variant="outline" className="bg-green-50 text-green-700 border-green-200">
                            <CheckCircle className="h-3 w-3 mr-1" />
                            Responded
                          </Badge>
                        )}
                        {thread.follow_ups && Array.isArray(thread.follow_ups) && thread.follow_ups.length > 0 && (
                          <Badge variant="outline" className="bg-purple-50 text-purple-700 border-purple-200">
                            <Timer className="h-3 w-3 mr-1" />
                            {thread.follow_ups.length} Follow-ups
                          </Badge>
                        )}
                      </CardTitle>
                      <CardDescription>
                        Original: {thread.original_email?.sender || 'Unknown'} • {thread.original_email?.received_at ? new Date(thread.original_email.received_at).toLocaleString() : 'Unknown time'}
                        {thread.participants && Array.isArray(thread.participants) && thread.participants.length > 2 && (
                          <span className="ml-2">• {thread.participants.length} participants</span>
                        )}
                      </CardDescription>
                    </div>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setSelectedEmail(selectedEmail?.thread_id === thread.thread_id ? null : thread)}
                    >
                      <Eye className="h-4 w-4" />
                    </Button>
                  </div>
                </CardHeader>

                {selectedEmail?.thread_id === thread.thread_id && thread.original_email && (
                  <CardContent className="border-t space-y-6">
                    {/* Original Email */}
                    <div className="bg-slate-50 rounded-lg p-4">
                      <div className="flex justify-between items-center mb-3">
                        <h4 className="font-semibold text-slate-800">Original Email</h4>
                        <div className="flex gap-2">
                          {thread.original_email?.status === 'ready_to_send' && (
                            <Button size="sm" onClick={() => handleSendEmail(thread.original_email.id)} className="bg-green-600 hover:bg-green-700">
                              <Send className="h-4 w-4 mr-1" />
                              Send
                            </Button>
                          )}
                          {(thread.original_email?.status === 'needs_redraft' || thread.original_email?.status === 'escalate') && (
                            <Button variant="outline" size="sm" onClick={() => handleRedraft(thread.original_email.id)}>
                              <RefreshCw className="h-4 w-4 mr-1" />
                              Redraft
                            </Button>
                          )}
                        </div>
                      </div>
                      <div className="text-sm text-slate-600 mb-2">
                        From: {thread.original_email?.sender || 'Unknown'} | To: {thread.original_email?.recipient || 'Unknown'}
                      </div>
                      <div className="bg-white p-3 rounded border text-sm">
                        {thread.original_email?.body || 'No content'}
                      </div>
                      {thread.original_email?.draft && (
                        <div className="mt-3">
                          <h5 className="font-medium text-slate-700 mb-2">Generated Response:</h5>
                          <div className="bg-green-50 p-3 rounded border text-sm">
                            {thread.original_email.draft}
                          </div>
                        </div>
                      )}
                    </div>

                    {/* Responses */}
                    {thread.responses && Array.isArray(thread.responses) && thread.responses.length > 0 && (
                      <div>
                        <h4 className="font-semibold text-slate-800 mb-3">Responses ({thread.responses.length})</h4>
                        <div className="space-y-3">
                          {thread.responses.map((response, index) => (
                            <div key={response.id} className="bg-blue-50 rounded-lg p-4 border-l-4 border-blue-400">
                              <div className="flex justify-between items-center mb-2">
                                <div className="font-medium text-blue-800">Response #{index + 1}</div>
                                <div className="text-sm text-blue-600">
                                  {new Date(response.received_at).toLocaleString()}
                                </div>
                              </div>
                              <div className="text-sm text-blue-700 mb-2">
                                From: {response.sender}
                              </div>
                              <div className="bg-white p-3 rounded text-sm">
                                {response.body}
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Follow-ups */}
                    {thread.follow_ups && Array.isArray(thread.follow_ups) && thread.follow_ups.length > 0 && (
                      <div>
                        <h4 className="font-semibold text-slate-800 mb-3">Follow-ups ({thread.follow_ups.length})</h4>
                        <div className="space-y-3">
                          {thread.follow_ups.map((followUp) => (
                            <div key={followUp.id} className={`rounded-lg p-4 border-l-4 ${
                              followUp.status === 'pending' ? 'bg-yellow-50 border-yellow-400' :
                              followUp.status === 'sent' ? 'bg-green-50 border-green-400' :
                              followUp.status === 'cancelled' ? 'bg-slate-50 border-slate-400' :
                              'bg-red-50 border-red-400'
                            }`}>
                              <div className="flex justify-between items-start mb-2">
                                <div>
                                  <div className="flex items-center gap-2 mb-1">
                                    <span className="font-medium">Follow-up #{followUp.follow_up_number}</span>
                                    <Badge className={`text-xs ${
                                      followUp.status === 'pending' ? 'bg-yellow-100 text-yellow-800' :
                                      followUp.status === 'sent' ? 'bg-green-100 text-green-800' :
                                      followUp.status === 'cancelled' ? 'bg-slate-100 text-slate-800' :
                                      'bg-red-100 text-red-800'
                                    }`}>
                                      {followUp.status}
                                    </Badge>
                                  </div>
                                  <div className="text-sm text-slate-600">
                                    Scheduled: {new Date(followUp.scheduled_time).toLocaleString()}
                                    {followUp.sent_time && (
                                      <span className="ml-2">| Sent: {new Date(followUp.sent_time).toLocaleString()}</span>
                                    )}
                                  </div>
                                </div>
                                <div className="flex gap-2">
                                  {followUp.status === 'pending' && (
                                    <>
                                      <Button size="sm" onClick={() => handleSendFollowUp(followUp.id)} className="bg-green-600 hover:bg-green-700">
                                        <Send className="h-4 w-4 mr-1" />
                                        Send Now
                                      </Button>
                                      <Button size="sm" variant="outline" onClick={() => handleCancelFollowUp(followUp.id)}>
                                        <X className="h-4 w-4 mr-1" />
                                        Cancel
                                      </Button>
                                    </>
                                  )}
                                </div>
                              </div>
                              <div className="text-sm">
                                <strong>Subject:</strong> {followUp.subject}
                              </div>
                              {followUp.draft_content && (
                                <div className="mt-2 bg-white p-3 rounded text-sm">
                                  {followUp.draft_content}
                                </div>
                              )}
                              {followUp.error_message && (
                                <div className="mt-2 text-sm text-red-600">
                                  <strong>Error:</strong> {followUp.error_message}
                                </div>
                              )}
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </CardContent>
                )}
              </Card>
            ))
          ) : (
            // Individual Email View - Fixed to handle thread structure properly with null checks
            (emailThreads && Array.isArray(emailThreads) ? emailThreads : []).map((thread, index) => {
              // Defensive programming: ensure we have valid data
              if (!thread) return null;
              
              const email = thread.original_email || thread; // Handle both thread and email objects
              
              // Ensure email object has required properties
              if (!email || !email.id) return null;
              
              // Provide default values for missing properties
              const safeEmail = {
                id: email.id,
                subject: email.subject || thread?.subject || 'No Subject',
                status: email.status || 'unknown',
                sender: email.sender || 'Unknown Sender',
                recipient: email.recipient || 'Unknown Recipient',
                received_at: email.received_at || new Date().toISOString(),
                processed_at: email.processed_at || null,
                body: email.body || '',
                intents: email.intents || [],
                draft: email.draft || '',
                validation_result: email.validation_result || null,
                error: email.error || null
              };
              
              return (
                <Card key={safeEmail.id || `email-${index}`} className="shadow-lg hover:shadow-xl transition-shadow">
                  <CardHeader>
                    <div className="flex justify-between items-start">
                      <div className="flex-1">
                        <CardTitle className="flex items-center gap-2 mb-2">
                          <MessageSquare className="h-5 w-5 text-blue-600" />
                          {safeEmail.subject}
                          <Badge className={getStatusColor(safeEmail.status)}>
                            {safeEmail.status ? safeEmail.status.replace('_', ' ') : 'unknown'}
                          </Badge>
                          
                          {/* AI Agent Status Indicators */}
                          <div className="flex gap-1 ml-2">
                            {safeEmail.intents && safeEmail.intents.length > 0 && (
                              <Badge variant="outline" className="bg-blue-50 text-blue-700 border-blue-200 text-xs">
                                <Brain className="h-3 w-3 mr-1" />
                                Intent: {safeEmail.intents.length} identified
                              </Badge>
                            )}
                            {safeEmail.draft && (
                              <Badge variant="outline" className="bg-green-50 text-green-700 border-green-200 text-xs">
                                <Bot className="h-3 w-3 mr-1" />
                                Draft: Generated
                              </Badge>
                            )}
                            {safeEmail.validation_result && (
                              <Badge variant="outline" className={`text-xs ${
                                safeEmail.validation_result.status === 'PASS' 
                                  ? 'bg-green-50 text-green-700 border-green-200'
                                  : 'bg-red-50 text-red-700 border-red-200'
                              }`}>
                                <Shield className="h-3 w-3 mr-1" />
                                Validation: {safeEmail.validation_result.status}
                              </Badge>
                            )}
                          </div>
                        </CardTitle>
                        <CardDescription>
                          From: {safeEmail.sender} • {new Date(safeEmail.received_at).toLocaleString()}
                          {safeEmail.processed_at && (
                            <span className="ml-2">• Processed: {new Date(safeEmail.processed_at).toLocaleString()}</span>
                          )}
                        </CardDescription>
                      </div>
                      <div className="flex gap-2">
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => setSelectedEmail(selectedEmail?.id === safeEmail.id ? null : { ...thread, email: safeEmail })}
                        >
                          <Eye className="h-4 w-4" />
                        </Button>
                        {safeEmail.status === 'ready_to_send' && (
                          <Button size="sm" onClick={() => handleSendEmail(safeEmail.id)} className="bg-green-600 hover:bg-green-700">
                            <Send className="h-4 w-4" />
                          </Button>
                        )}
                        {(safeEmail.status === 'needs_redraft' || safeEmail.status === 'escalate') && (
                          <Button variant="outline" size="sm" onClick={() => handleRedraft(safeEmail.id)}>
                            <RefreshCw className="h-4 w-4" />
                          </Button>
                        )}
                      </div>
                    </div>
                  </CardHeader>
                  
                  {selectedEmail?.email?.id === safeEmail.id && (
                    <CardContent className="border-t space-y-4">
                      {/* Original Email Content */}
                      <div className="bg-slate-50 p-4 rounded-lg">
                        <h4 className="font-medium text-slate-700 mb-2">Original Email:</h4>
                        <p className="whitespace-pre-wrap text-sm">{safeEmail.body}</p>
                      </div>
                      
                      {/* AI Processing Status */}
                      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                        {/* Intent Classification Status */}
                        <div className="bg-blue-50 p-3 rounded-lg border-l-4 border-blue-400">
                          <div className="flex items-center gap-2 mb-2">
                            <Brain className="h-4 w-4 text-blue-600" />
                            <span className="font-medium text-blue-800">Intent Classification</span>
                          </div>
                          {safeEmail.intents && safeEmail.intents.length > 0 ? (
                            <div className="space-y-1">
                              {safeEmail.intents.map((intent, idx) => (
                                <div key={idx} className="text-xs text-blue-700">
                                  • {intent.name} ({intent.confidence ? Math.round(intent.confidence * 100) : 0}%)
                                </div>
                              ))}
                            </div>
                          ) : (
                            <div className="text-xs text-blue-600">No intents identified</div>
                          )}
                        </div>
                        
                        {/* Draft Generation Status */}
                        <div className="bg-green-50 p-3 rounded-lg border-l-4 border-green-400">
                          <div className="flex items-center gap-2 mb-2">
                            <Bot className="h-4 w-4 text-green-600" />
                            <span className="font-medium text-green-800">Draft Agent</span>
                          </div>
                          <div className="text-xs text-green-700">
                            {safeEmail.draft ? (
                              <span>✓ Draft generated ({safeEmail.draft.length} chars)</span>
                            ) : (
                              <span>⏳ No draft available</span>
                            )}
                          </div>
                        </div>
                        
                        {/* Validation Status */}
                        <div className={`p-3 rounded-lg border-l-4 ${
                          safeEmail.validation_result?.status === 'PASS' 
                            ? 'bg-green-50 border-green-400' 
                            : safeEmail.validation_result?.status === 'FAIL'
                            ? 'bg-red-50 border-red-400'
                            : 'bg-gray-50 border-gray-400'
                        }`}>
                          <div className="flex items-center gap-2 mb-2">
                            <Shield className={`h-4 w-4 ${
                              safeEmail.validation_result?.status === 'PASS' ? 'text-green-600' :
                              safeEmail.validation_result?.status === 'FAIL' ? 'text-red-600' : 'text-gray-600'
                            }`} />
                            <span className={`font-medium ${
                              safeEmail.validation_result?.status === 'PASS' ? 'text-green-800' :
                              safeEmail.validation_result?.status === 'FAIL' ? 'text-red-800' : 'text-gray-800'
                            }`}>
                              Validation Agent
                            </span>
                          </div>
                          <div className={`text-xs ${
                            safeEmail.validation_result?.status === 'PASS' ? 'text-green-700' :
                            safeEmail.validation_result?.status === 'FAIL' ? 'text-red-700' : 'text-gray-700'
                          }`}>
                            {safeEmail.validation_result ? (
                              <span>
                                {safeEmail.validation_result.status === 'PASS' ? '✓' : '✗'} {safeEmail.validation_result.status}
                                {safeEmail.validation_result.feedback && (
                                  <div className="mt-1 text-xs opacity-75">
                                    {safeEmail.validation_result.feedback.substring(0, 100)}...
                                  </div>
                                )}
                              </span>
                            ) : (
                              <span>⏳ Not validated yet</span>
                            )}
                          </div>
                        </div>
                      </div>
                      
                      {/* Generated Draft */}
                      {safeEmail.draft && (
                        <div className="bg-green-50 p-4 rounded-lg">
                          <div className="flex justify-between items-center mb-2">
                            <h4 className="font-medium text-green-800">Generated Response:</h4>
                            {/* Placeholder Detection Warning */}
                            {(/\[.*\]/g.test(safeEmail.draft) || /{{.*}}/g.test(safeEmail.draft)) && (
                              <Badge variant="outline" className="bg-orange-50 text-orange-700 border-orange-200">
                                <AlertCircle className="h-3 w-3 mr-1" />
                                Contains placeholders
                              </Badge>
                            )}
                          </div>
                          <div className="bg-white p-3 rounded border text-sm">
                            <p className="whitespace-pre-wrap">{safeEmail.draft}</p>
                          </div>
                        </div>
                      )}
                      
                      {/* Validation Result Details */}
                      {safeEmail.validation_result && safeEmail.validation_result.feedback && (
                        <div className={`p-4 rounded-lg ${
                          safeEmail.validation_result.status === 'PASS' 
                            ? 'bg-green-50' 
                            : 'bg-red-50'
                        }`}>
                          <h4 className={`font-medium mb-2 ${
                            safeEmail.validation_result.status === 'PASS' 
                              ? 'text-green-800' 
                              : 'text-red-800'
                          }`}>
                            Validation Feedback:
                          </h4>
                          <div className={`text-sm ${
                            safeEmail.validation_result.status === 'PASS' 
                              ? 'text-green-700' 
                              : 'text-red-700'
                          }`}>
                            <p className="whitespace-pre-wrap">{safeEmail.validation_result.feedback}</p>
                          </div>
                        </div>
                      )}
                      
                      {/* Error Information */}
                      {safeEmail.error && (
                        <div className="bg-red-50 p-4 rounded-lg border-l-4 border-red-400">
                          <div className="flex items-center gap-2 mb-2">
                            <AlertCircle className="h-4 w-4 text-red-600" />
                            <span className="font-medium text-red-800">Processing Error</span>
                          </div>
                          <div className="text-sm text-red-700">
                            <p className="whitespace-pre-wrap">
                              {typeof safeEmail.error === 'object' 
                                ? JSON.stringify(safeEmail.error, null, 2)
                                : safeEmail.error}
                            </p>
                          </div>
                        </div>
                      )}
                    </CardContent>
                  )}
                </Card>
              );
            }).filter(Boolean) // Remove any null entries
          )}
          
          {emailThreads.length === 0 && (
            <Card className="text-center py-12">
              <CardContent>
                <MessageSquare className="h-12 w-12 text-slate-400 mx-auto mb-4" />
                <h3 className="text-lg font-medium text-slate-600 mb-2">No email conversations yet</h3>
                <p className="text-slate-500">Email conversations will appear here</p>
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </Layout>
  );
};

// Email Testing Component
const EmailTesting = () => {
  const [accounts, setAccounts] = useState([]);
  const [formData, setFormData] = useState({
    subject: '',
    body: '',
    sender: '',
    account_id: ''
  });
  const [isLoading, setIsLoading] = useState(false);
  const [result, setResult] = useState(null);

  useEffect(() => {
    fetchAccounts();
  }, []);

  const fetchAccounts = async () => {
    try {
      const response = await axios.get(`${API}/email-accounts`);
      setAccounts(response.data);
    } catch (error) {
      console.error('Error fetching accounts:', error);
    }
  };

  const handleTest = async (e) => {
    e.preventDefault();
    setIsLoading(true);
    setResult(null);
    
    try {
      const response = await axios.post(`${API}/emails/test`, formData);
      setResult(response.data);
    } catch (error) {
      console.error('Error testing email:', error);
      setResult({ error: 'Failed to process email' });
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <Layout>
      <div className="space-y-8">
        <div>
          <h1 className="text-4xl font-bold text-slate-800 mb-2">Test Email Processing</h1>
          <p className="text-slate-600">Test your AI assistant with sample emails</p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* Test Form */}
          <Card className="shadow-lg">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Zap className="h-5 w-5 text-purple-600" />
                Test Email Input
              </CardTitle>
            </CardHeader>
            <CardContent>
              <form onSubmit={handleTest} className="space-y-6">
                <div>
                  <Label htmlFor="account">Email Account</Label>
                  <Select 
                    value={formData.account_id} 
                    onValueChange={(value) => setFormData(prev => ({ ...prev, account_id: value }))}
                    required
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Select email account" />
                    </SelectTrigger>
                    <SelectContent>
                      {accounts.map(account => (
                        <SelectItem key={account.id} value={account.id}>
                          {account.name} ({account.email})
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                <div>
                  <Label htmlFor="sender">Sender Email</Label>
                  <Input
                    id="sender"
                    type="email"
                    value={formData.sender}
                    onChange={(e) => setFormData(prev => ({ ...prev, sender: e.target.value }))}
                    placeholder="customer@example.com"
                    required
                  />
                </div>

                <div>
                  <Label htmlFor="subject">Subject</Label>
                  <Input
                    id="subject"
                    value={formData.subject}
                    onChange={(e) => setFormData(prev => ({ ...prev, subject: e.target.value }))}
                    placeholder="Need help with product"
                    required
                  />
                </div>

                <div>
                  <Label htmlFor="body">Email Body</Label>
                  <Textarea
                    id="body"
                    value={formData.body}
                    onChange={(e) => setFormData(prev => ({ ...prev, body: e.target.value }))}
                    placeholder="Hi, I need help with your product. Can you please provide more information about pricing and features?"
                    rows={6}
                    required
                  />
                </div>

                <Button 
                  type="submit" 
                  disabled={isLoading}
                  className="w-full bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-700 hover:to-pink-700"
                >
                  {isLoading ? (
                    <>
                      <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
                      Processing...
                    </>
                  ) : (
                    <>
                      <Send className="h-4 w-4 mr-2" />
                      Test Email Processing
                    </>
                  )}
                </Button>
              </form>
            </CardContent>
          </Card>

          {/* Results */}
          <Card className="shadow-lg">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Eye className="h-5 w-5 text-blue-600" />
                Processing Results
              </CardTitle>
            </CardHeader>
            <CardContent>
              {isLoading && (
                <div className="flex items-center justify-center py-12">
                  <RefreshCw className="h-8 w-8 animate-spin text-purple-600" />
                </div>
              )}

              {result?.error && (
                <Alert className="border-red-200 bg-red-50">
                  <AlertCircle className="h-4 w-4 text-red-600" />
                  <AlertDescription className="text-red-800">
                    {result.error}
                  </AlertDescription>
                </Alert>
              )}

              {result && !result.error && (
                <Tabs defaultValue="intents" className="w-full">
                  <TabsList className="grid w-full grid-cols-3">
                    <TabsTrigger value="intents">Intents</TabsTrigger>
                    <TabsTrigger value="draft">Draft</TabsTrigger>
                    <TabsTrigger value="validation">Validation</TabsTrigger>
                  </TabsList>
                  
                  <TabsContent value="intents" className="space-y-4">
                    <div>
                      <Label className="font-medium">Identified Intents:</Label>
                      {result.intents && result.intents.length > 0 ? (
                        <div className="space-y-2 mt-2">
                          {result.intents.map((intent, index) => (
                            <div key={index} className="bg-purple-50 p-3 rounded-lg">
                              <div className="flex justify-between items-center">
                                <span className="font-medium text-purple-800">{intent.name}</span>
                                <Badge variant="outline">
                                  {(intent.confidence * 100).toFixed(1)}%
                                </Badge>
                              </div>
                              <p className="text-sm text-purple-700 mt-1">{intent.description}</p>
                            </div>
                          ))}
                        </div>
                      ) : (
                        <p className="text-slate-500 mt-2">No intents identified</p>
                      )}
                    </div>
                  </TabsContent>
                  
                  <TabsContent value="draft" className="space-y-4">
                    <div>
                      <Label className="font-medium">Generated Draft:</Label>
                      {result.draft ? (
                        <div className="bg-green-50 p-4 rounded-lg mt-2">
                          <p className="whitespace-pre-wrap text-green-800">{result.draft}</p>
                        </div>
                      ) : (
                        <p className="text-slate-500 mt-2">No draft generated</p>
                      )}
                    </div>
                  </TabsContent>
                  
                  <TabsContent value="validation" className="space-y-4">
                    <div>
                      <Label className="font-medium">Validation Result:</Label>
                      {result.validation_result ? (
                        <div className={`p-4 rounded-lg mt-2 ${
                          result.validation_result.status === 'PASS' 
                            ? 'bg-green-50' 
                            : 'bg-red-50'
                        }`}>
                          <div className="flex items-center gap-2 mb-2">
                            {result.validation_result.status === 'PASS' ? (
                              <CheckCircle className="h-5 w-5 text-green-600" />
                            ) : (
                              <AlertCircle className="h-5 w-5 text-red-600" />
                            )}
                            <span className={`font-medium ${
                              result.validation_result.status === 'PASS' 
                                ? 'text-green-800' 
                                : 'text-red-800'
                            }`}>
                              {result.validation_result.status}
                            </span>
                          </div>
                          <p className={`whitespace-pre-wrap ${
                            result.validation_result.status === 'PASS' 
                              ? 'text-green-700' 
                              : 'text-red-700'
                          }`}>
                            {result.validation_result.feedback}
                          </p>
                        </div>
                      ) : (
                        <p className="text-slate-500 mt-2">No validation result</p>
                      )}
                    </div>
                  </TabsContent>
                </Tabs>
              )}

              {!result && !isLoading && (
                <div className="text-center py-12">
                  <Bot className="h-12 w-12 text-slate-400 mx-auto mb-4" />
                  <h3 className="text-lg font-medium text-slate-600 mb-2">Ready to test</h3>
                  <p className="text-slate-500">Enter an email on the left to see AI processing results</p>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </Layout>
  );
};

// Follow-Up Management Component
const FollowUpManagement = () => {
  const [followUps, setFollowUps] = useState([]);
  const [followUpConfig, setFollowUpConfig] = useState(null);
  const [analytics, setAnalytics] = useState({});
  const [isLoading, setIsLoading] = useState(false);
  const [activeTab, setActiveTab] = useState('pending');
  const [showConfigDialog, setShowConfigDialog] = useState(false);
  const [configForm, setConfigForm] = useState({
    global_follow_up_hours: 24,
    max_follow_ups: 3,
    follow_up_interval_hours: 48,
    auto_follow_up: true,
    business_hours_only: false,
    business_start_hour: 9,
    business_end_hour: 17,
    exclude_weekends: true
  });

  useEffect(() => {
    fetchFollowUps();
    fetchFollowUpConfig();
    fetchAnalytics();
  }, []);

  const fetchFollowUps = async (status = null) => {
    try {
      setIsLoading(true);
      const params = status ? `?status=${status}` : '';
      const response = await axios.get(`${API}/follow-ups${params}`);
      setFollowUps(response.data);
    } catch (error) {
      console.error('Error fetching follow-ups:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const fetchFollowUpConfig = async () => {
    try {
      const response = await axios.get(`${API}/follow-up/config`);
      setFollowUpConfig(response.data);
      setConfigForm(response.data);
    } catch (error) {
      console.error('Error fetching follow-up config:', error);
    }
  };

  const fetchAnalytics = async () => {
    try {
      const response = await axios.get(`${API}/follow-ups/analytics`);
      setAnalytics(response.data);
    } catch (error) {
      console.error('Error fetching analytics:', error);
    }
  };

  const updateFollowUpConfig = async () => {
    try {
      const response = await axios.put(`${API}/follow-up/config`, configForm);
      setFollowUpConfig(response.data);
      setShowConfigDialog(false);
      alert('Follow-up configuration updated successfully!');
    } catch (error) {
      console.error('Error updating config:', error);
      alert('Failed to update configuration');
    }
  };

  const sendFollowUp = async (followUpId) => {
    try {
      await axios.post(`${API}/follow-ups/${followUpId}/send`);
      alert('Follow-up sent successfully!');
      fetchFollowUps(activeTab === 'all' ? null : activeTab);
      fetchAnalytics();
    } catch (error) {
      console.error('Error sending follow-up:', error);
      alert('Failed to send follow-up');
    }
  };

  const cancelFollowUp = async (followUpId) => {
    try {
      await axios.delete(`${API}/follow-ups/${followUpId}`);
      alert('Follow-up cancelled successfully!');
      fetchFollowUps(activeTab === 'all' ? null : activeTab);
      fetchAnalytics();
    } catch (error) {
      console.error('Error cancelling follow-up:', error);
      alert('Failed to cancel follow-up');
    }
  };

  const formatDateTime = (dateString) => {
    return new Date(dateString).toLocaleString();
  };

  const getStatusBadge = (status) => {
    const colors = {
      pending: 'bg-yellow-100 text-yellow-800',
      sent: 'bg-green-100 text-green-800',
      failed: 'bg-red-100 text-red-800',
      cancelled: 'bg-slate-100 text-slate-800'
    };
    return colors[status] || 'bg-slate-100 text-slate-800';
  };

  useEffect(() => {
    fetchFollowUps(activeTab === 'all' ? null : activeTab);
  }, [activeTab]);

  return (
    <Layout>
      <div className="p-6 space-y-6">
        <div className="flex justify-between items-center">
          <div>
            <h1 className="text-3xl font-bold text-slate-800">Follow-up Management</h1>
            <p className="text-slate-600 mt-2">Manage your email follow-up settings and track pending follow-ups</p>
          </div>
          <Button onClick={() => setShowConfigDialog(true)} className="bg-purple-600 hover:bg-purple-700">
            <Settings className="h-4 w-4 mr-2" />
            Settings
          </Button>
        </div>

        {/* Analytics Cards */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <Card>
            <CardContent className="p-4">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-yellow-100 rounded-lg">
                  <Clock className="h-5 w-5 text-yellow-600" />
                </div>
                <div>
                  <div className="text-2xl font-bold text-slate-800">{analytics.pending_today || 0}</div>
                  <div className="text-sm text-slate-600">Due Today</div>
                </div>
              </div>
            </CardContent>
          </Card>
          
          <Card>
            <CardContent className="p-4">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-red-100 rounded-lg">
                  <AlertCircle className="h-5 w-5 text-red-600" />
                </div>
                <div>
                  <div className="text-2xl font-bold text-slate-800">{analytics.overdue || 0}</div>
                  <div className="text-sm text-slate-600">Overdue</div>
                </div>
              </div>
            </CardContent>
          </Card>
          
          <Card>
            <CardContent className="p-4">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-green-100 rounded-lg">
                  <Send className="h-5 w-5 text-green-600" />
                </div>
                <div>
                  <div className="text-2xl font-bold text-slate-800">{analytics.total_sent || 0}</div>
                  <div className="text-sm text-slate-600">Total Sent</div>
                </div>
              </div>
            </CardContent>
          </Card>
          
          <Card>
            <CardContent className="p-4">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-blue-100 rounded-lg">
                  <CheckCircle className="h-5 w-5 text-blue-600" />
                </div>
                <div>
                  <div className="text-2xl font-bold text-slate-800">{analytics.response_rate || 0}%</div>
                  <div className="text-sm text-slate-600">Response Rate</div>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Follow-ups List */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Timer className="h-5 w-5" />
              Follow-up Emails
            </CardTitle>
          </CardHeader>
          <CardContent>
            <Tabs value={activeTab} onValueChange={setActiveTab}>
              <TabsList className="grid grid-cols-5 w-full max-w-lg">
                <TabsTrigger value="pending">Pending</TabsTrigger>
                <TabsTrigger value="sent">Sent</TabsTrigger>
                <TabsTrigger value="failed">Failed</TabsTrigger>
                <TabsTrigger value="cancelled">Cancelled</TabsTrigger>
                <TabsTrigger value="all">All</TabsTrigger>
              </TabsList>

              <TabsContent value={activeTab} className="mt-6">
                {isLoading ? (
                  <div className="text-center py-8">
                    <div className="animate-spin w-8 h-8 border-4 border-purple-600 border-t-transparent rounded-full mx-auto"></div>
                    <p className="text-slate-600 mt-4">Loading follow-ups...</p>
                  </div>
                ) : followUps.length === 0 ? (
                  <div className="text-center py-12">
                    <Timer className="h-12 w-12 text-slate-400 mx-auto mb-4" />
                    <h3 className="text-lg font-medium text-slate-600 mb-2">No follow-ups found</h3>
                    <p className="text-slate-500">
                      {activeTab === 'pending' ? 'No pending follow-ups at the moment' : 
                       activeTab === 'all' ? 'No follow-ups have been created yet' :
                       `No ${activeTab} follow-ups found`}
                    </p>
                  </div>
                ) : (
                  <div className="space-y-4">
                    {followUps.map((followUp) => (
                      <div key={followUp.id} className="border border-slate-200 rounded-lg p-4 hover:shadow-md transition-shadow">
                        <div className="flex justify-between items-start mb-3">
                          <div className="flex-1">
                            <div className="flex items-center gap-3 mb-2">
                              <h3 className="font-semibold text-slate-800">{followUp.subject}</h3>
                              <Badge className={getStatusBadge(followUp.status)}>
                                {followUp.status}
                              </Badge>
                              <Badge variant="secondary">
                                Follow-up #{followUp.follow_up_number}
                              </Badge>
                            </div>
                            <div className="text-sm text-slate-600 space-y-1">
                              <div>To: {followUp.recipient_email}</div>
                              <div>Scheduled: {formatDateTime(followUp.scheduled_time)}</div>
                              {followUp.sent_time && (
                                <div>Sent: {formatDateTime(followUp.sent_time)}</div>
                              )}
                              {followUp.error_message && (
                                <div className="text-red-600">Error: {followUp.error_message}</div>
                              )}
                            </div>
                          </div>
                          <div className="flex gap-2">
                            {followUp.status === 'pending' && (
                              <>
                                <Button 
                                  size="sm" 
                                  onClick={() => sendFollowUp(followUp.id)}
                                  className="bg-green-600 hover:bg-green-700"
                                >
                                  <Send className="h-4 w-4 mr-1" />
                                  Send Now
                                </Button>
                                <Button 
                                  size="sm" 
                                  variant="outline"
                                  onClick={() => cancelFollowUp(followUp.id)}
                                >
                                  <Trash2 className="h-4 w-4 mr-1" />
                                  Cancel
                                </Button>
                              </>
                            )}
                          </div>
                        </div>
                        <div className="bg-slate-50 rounded p-3 text-sm">
                          <div className="font-medium text-slate-700 mb-2">Follow-up Content:</div>
                          <div className="text-slate-600">{followUp.draft_content.substring(0, 200)}...</div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </TabsContent>
            </Tabs>
          </CardContent>
        </Card>

        {/* Configuration Dialog */}
        <Dialog open={showConfigDialog} onOpenChange={setShowConfigDialog}>
          <DialogContent className="max-w-2xl">
            <DialogHeader>
              <DialogTitle>Follow-up Configuration</DialogTitle>
              <DialogDescription>
                Configure your automatic follow-up settings
              </DialogDescription>
            </DialogHeader>
            
            <div className="space-y-6">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label htmlFor="follow_up_hours">Initial Follow-up (hours)</Label>
                  <Input
                    id="follow_up_hours"
                    type="number"
                    value={configForm.global_follow_up_hours}
                    onChange={(e) => setConfigForm({...configForm, global_follow_up_hours: parseInt(e.target.value)})}
                  />
                </div>
                <div>
                  <Label htmlFor="max_follow_ups">Max Follow-ups</Label>
                  <Input
                    id="max_follow_ups"
                    type="number"
                    value={configForm.max_follow_ups}
                    onChange={(e) => setConfigForm({...configForm, max_follow_ups: parseInt(e.target.value)})}
                  />
                </div>
              </div>

              <div>
                <Label htmlFor="interval_hours">Interval between Follow-ups (hours)</Label>
                <Input
                  id="interval_hours"
                  type="number"
                  value={configForm.follow_up_interval_hours}
                  onChange={(e) => setConfigForm({...configForm, follow_up_interval_hours: parseInt(e.target.value)})}
                />
              </div>

              <div className="flex items-center space-x-2">
                <Switch
                  id="auto_follow_up"
                  checked={configForm.auto_follow_up}
                  onCheckedChange={(checked) => setConfigForm({...configForm, auto_follow_up: checked})}
                />
                <Label htmlFor="auto_follow_up">Enable automatic follow-ups</Label>
              </div>

              <div className="flex items-center space-x-2">
                <Switch
                  id="business_hours_only"
                  checked={configForm.business_hours_only}
                  onCheckedChange={(checked) => setConfigForm({...configForm, business_hours_only: checked})}
                />
                <Label htmlFor="business_hours_only">Only send during business hours</Label>
              </div>

              {configForm.business_hours_only && (
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <Label htmlFor="start_hour">Business Start Hour</Label>
                    <Input
                      id="start_hour"
                      type="number"
                      min="0"
                      max="23"
                      value={configForm.business_start_hour}
                      onChange={(e) => setConfigForm({...configForm, business_start_hour: parseInt(e.target.value)})}
                    />
                  </div>
                  <div>
                    <Label htmlFor="end_hour">Business End Hour</Label>
                    <Input
                      id="end_hour"
                      type="number"
                      min="0"
                      max="23"
                      value={configForm.business_end_hour}
                      onChange={(e) => setConfigForm({...configForm, business_end_hour: parseInt(e.target.value)})}
                    />
                  </div>
                </div>
              )}

              <div className="flex items-center space-x-2">
                <Switch
                  id="exclude_weekends"
                  checked={configForm.exclude_weekends}
                  onCheckedChange={(checked) => setConfigForm({...configForm, exclude_weekends: checked})}
                />
                <Label htmlFor="exclude_weekends">Exclude weekends</Label>
              </div>
            </div>

            <div className="flex gap-2 justify-end mt-6">
              <Button variant="outline" onClick={() => setShowConfigDialog(false)}>
                Cancel
              </Button>
              <Button onClick={updateFollowUpConfig} className="bg-purple-600 hover:bg-purple-700">
                Save Configuration
              </Button>
            </div>
          </DialogContent>
        </Dialog>
      </div>
    </Layout>
  );
};

export default App;