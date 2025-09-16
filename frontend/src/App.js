import React, { useState, useEffect, createContext, useContext } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import axios from 'axios';
import './App.css';

// Import Calendar Components
import { CalendarEvents, MeetingDetection } from './CalendarComponents';

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
  Cloud, Smartphone, Monitor, MapPin, Users2, Timer
} from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

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
      const response = await axios.get(`${API}/auth/profile`);
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
  const [formData, setFormData] = useState({ email: '', password: '' });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    const result = await login(formData.email, formData.password);
    if (!result.success) {
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
                onClick={() => window.location.href = '/register'}
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
              onClick={() => window.location.href = '/login'}
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
                onClick={() => window.location.href = '/login'}
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
              onClick={() => window.location.href = item.path}
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
                <Alert className={message.includes('success') ? 'border-green-200 bg-green-50' : 'border-red-200 bg-red-50'}>
                  <AlertCircle className={`h-4 w-4 ${message.includes('success') ? 'text-green-600' : 'text-red-600'}`} />
                  <AlertDescription className={message.includes('success') ? 'text-green-700' : 'text-red-700'}>
                    {message}
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

// Calendar Providers Component
const CalendarProviders = () => {
  const [providers, setProviders] = useState([]);
  const [isCreating, setIsCreating] = useState(false);
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
  }, []);

  const fetchProviders = async () => {
    try {
      const response = await axios.get(`${API}/calendar/providers`);
      setProviders(response.data);
    } catch (error) {
      console.error('Error fetching providers:', error);
    }
  };

  const handleCreateProvider = async (e) => {
    e.preventDefault();
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
      default:
        return null;
    }
  };

  const getProviderIcon = (type) => {
    switch (type) {
      case 'google': return <Cloud className="h-5 w-5 text-blue-600" />;
      case 'microsoft': return <Monitor className="h-5 w-5 text-blue-800" />;
      case 'apple': return <Smartphone className="h-5 w-5 text-slate-800" />;
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

        {message && (
          <Alert className={message.includes('success') ? 'border-green-200 bg-green-50' : 'border-red-200 bg-red-50'}>
            <AlertCircle className={`h-4 w-4 ${message.includes('success') ? 'text-green-600' : 'text-red-600'}`} />
            <AlertDescription className={message.includes('success') ? 'text-green-700' : 'text-red-700'}>
              {message}
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
          <DialogContent className="max-w-2xl">
            <DialogHeader>
              <DialogTitle>Add Calendar Provider</DialogTitle>
              <DialogDescription>
                Connect a calendar service to manage your meetings and events.
              </DialogDescription>
            </DialogHeader>
            <form onSubmit={handleCreateProvider} className="space-y-6">
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
                  </SelectContent>
                </Select>
              </div>

              <div>
                <Label htmlFor="provider_name">Provider Name</Label>
                <Input
                  id="provider_name"
                  value={formData.provider_name}
                  onChange={(e) => setFormData(prev => ({ ...prev, provider_name: e.target.value }))}
                  placeholder="e.g., My Google Calendar"
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

              {renderCredentialsFields()}

              <div className="flex justify-end gap-2">
                <Button 
                  type="button" 
                  variant="outline" 
                  onClick={() => {
                    setIsCreating(false);
                    resetForm();
                    setMessage('');
                  }}
                >
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
                      Adding...
                    </>
                  ) : (
                    <>
                      <Plus className="h-4 w-4 mr-2" />
                      Add Provider
                    </>
                  )}
                </Button>
              </div>
            </form>
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
                    </CardTitle>
                    <CardDescription>
                      {provider.provider_type.charAt(0).toUpperCase() + provider.provider_type.slice(1)} Calendar Provider
                    </CardDescription>
                  </div>
                  <div className="flex gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleDeleteProvider(provider.id)}
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
                    <span className="font-medium text-slate-700">Timezone:</span>
                    <div className="text-slate-600">{provider.timezone}</div>
                  </div>
                  <div>
                    <span className="font-medium text-slate-700">Calendars:</span>
                    <div className="text-slate-600">{provider.calendar_count} connected</div>
                  </div>
                  <div>
                    <span className="font-medium text-slate-700">Created:</span>
                    <div className="text-slate-600">{new Date(provider.created_at).toLocaleDateString()}</div>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
          
          {providers.length === 0 && (
            <Card className="text-center py-12">
              <CardContent>
                <Cloud className="h-12 w-12 text-slate-400 mx-auto mb-4" />
                <h3 className="text-lg font-medium text-slate-600 mb-2">No calendar providers connected</h3>
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
                onClick={() => window.location.href = '/monitoring'} 
                className="w-full bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-700 hover:to-pink-700"
              >
                <Activity className="h-4 w-4 mr-2" />
                Live Email Monitoring
              </Button>
              <Button 
                onClick={() => window.location.href = '/test'} 
                variant="outline" 
                className="w-full"
              >
                <Zap className="h-4 w-4 mr-2" />
                Test Email Processing
              </Button>
              <Button 
                onClick={() => window.location.href = '/intents'} 
                variant="outline" 
                className="w-full"
              >
                <Brain className="h-4 w-4 mr-2" />
                Manage Intents
              </Button>
              <Button 
                onClick={() => window.location.href = '/accounts'} 
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
                        <span className="ml-1">{email.status.replace('_', ' ')}</span>
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
                      onClick={() => window.location.href = '/emails'}
                    >
                      <Eye className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
                
                {/* Quick Preview */}
                {email.intents && email.intents.length > 0 && (
                  <div className="mt-3 pt-3 border-t">
                    <div className="flex flex-wrap gap-2">
                      {email.intents.map((intent, index) => (
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
                      {intent.examples.slice(0, 3).map((example, index) => (
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

// Email Accounts Component  
const EmailAccounts = () => {
  const [accounts, setAccounts] = useState([]);
  const [providers, setProviders] = useState({});
  const [isCreating, setIsCreating] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [editingAccount, setEditingAccount] = useState(null);
  const [formData, setFormData] = useState({
    name: '',
    email: '',
    provider: '',
    username: '',
    password: '',
    persona: 'Professional and helpful',
    signature: '',
    auto_send: true
  });

  useEffect(() => {
    fetchAccounts();
    fetchProviders();
  }, []);

  const fetchAccounts = async () => {
    try {
      const response = await axios.get(`${API}/email-accounts`);
      setAccounts(response.data);
    } catch (error) {
      console.error('Error fetching accounts:', error);
    }
  };

  const fetchProviders = async () => {
    try {
      const response = await axios.get(`${API}/email-providers`);
      setProviders(response.data);
    } catch (error) {
      console.error('Error fetching providers:', error);
    }
  };

  const handleCreateAccount = async (e) => {
    e.preventDefault();
    try {
      await axios.post(`${API}/email-accounts`, formData);
      setIsCreating(false);
      resetAccountForm();
      fetchAccounts();
    } catch (error) {
      console.error('Error creating account:', error);
    }
  };

  const handleEditAccount = (account) => {
    setEditingAccount(account);
    setFormData({
      name: account.name,
      email: account.email,
      provider: account.provider,
      username: account.username,
      password: '', // Don't pre-fill password for security
      persona: account.persona || 'Professional and helpful',
      signature: account.signature || '',
      auto_send: account.auto_send
    });
    setIsEditing(true);
  };

  const handleUpdateAccount = async (e) => {
    e.preventDefault();
    try {
      const updateData = { ...formData };
      // If password is empty, don't send it (keep existing password)
      if (!updateData.password.trim()) {
        delete updateData.password;
      }
      await axios.put(`${API}/email-accounts/${editingAccount.id}`, updateData);
      setIsEditing(false);
      setEditingAccount(null);
      resetAccountForm();
      fetchAccounts();
    } catch (error) {
      console.error('Error updating account:', error);
    }
  };

  const resetAccountForm = () => {
    setFormData({
      name: '',
      email: '',
      provider: '',
      username: '',
      password: '',
      persona: 'Professional and helpful',
      signature: '',
      auto_send: true
    });
  };

  const handleDeleteAccount = async (accountId) => {
    try {
      await axios.delete(`${API}/email-accounts/${accountId}`);
      fetchAccounts();
    } catch (error) {
      console.error('Error deleting account:', error);
    }
  };

  const toggleAccount = async (accountId) => {
    try {
      await axios.put(`${API}/email-accounts/${accountId}/toggle`);
      fetchAccounts();
    } catch (error) {
      console.error('Error toggling account:', error);
    }
  };

  return (
    <Layout>
      <div className="space-y-8">
        <div className="flex justify-between items-center">
          <div>
            <h1 className="text-4xl font-bold text-slate-800 mb-2">Email Accounts</h1>
            <p className="text-slate-600">Connect your email accounts for automated processing</p>
          </div>
          <Button 
            onClick={() => setIsCreating(true)}
            className="bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-700 hover:to-pink-700"
          >
            <Plus className="h-4 w-4 mr-2" />
            Add Account
          </Button>
        </div>

        {/* Create/Edit Account Dialog */}
        <Dialog open={isCreating || isEditing} onOpenChange={(open) => {
          if (!open) {
            setIsCreating(false);
            setIsEditing(false);
            setEditingAccount(null);
            resetAccountForm();
          }
        }}>
          <DialogContent className="max-w-2xl">
            <DialogHeader>
              <DialogTitle>{isEditing ? 'Edit Email Account' : 'Add Email Account'}</DialogTitle>
              <DialogDescription>
                {isEditing ? 'Update email account settings.' : 'Connect a new email account for automated processing.'}
              </DialogDescription>
            </DialogHeader>
            <form onSubmit={isEditing ? handleUpdateAccount : handleCreateAccount} className="space-y-6">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label htmlFor="name">Account Name</Label>
                  <Input
                    id="name"
                    value={formData.name}
                    onChange={(e) => setFormData(prev => ({ ...prev, name: e.target.value }))}
                    placeholder="e.g., Support Team"
                    required
                  />
                </div>
                <div>
                  <Label htmlFor="email">Email Address</Label>
                  <Input
                    id="email"
                    type="email"
                    value={formData.email}
                    onChange={(e) => setFormData(prev => ({ ...prev, email: e.target.value }))}
                    placeholder="support@company.com"
                    required
                  />
                </div>
              </div>

              <div>
                <Label htmlFor="provider">Email Provider</Label>
                <Select 
                  value={formData.provider} 
                  onValueChange={(value) => setFormData(prev => ({ ...prev, provider: value }))}
                  required
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Select email provider" />
                  </SelectTrigger>
                  <SelectContent>
                    {Object.entries(providers).map(([key, provider]) => (
                      <SelectItem key={key} value={key}>
                        {provider.name}
                        {provider.requires_app_password && <span className="text-xs text-amber-600 ml-2">(App Password Required)</span>}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                {formData.provider && providers[formData.provider]?.requires_app_password && (
                  <Alert className="mt-2">
                    <AlertCircle className="h-4 w-4" />
                    <AlertDescription>
                      This provider requires an app-specific password. Please generate one in your email account settings.
                    </AlertDescription>
                  </Alert>
                )}
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label htmlFor="username">Username</Label>
                  <Input
                    id="username"
                    value={formData.username}
                    onChange={(e) => setFormData(prev => ({ ...prev, username: e.target.value }))}
                    placeholder="Usually your email address"
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
                    placeholder={isEditing ? "Leave empty to keep current password" : "App password or regular password"}
                    required={!isEditing}
                  />
                  {isEditing && (
                    <p className="text-xs text-slate-500 mt-1">Leave empty to keep current password</p>
                  )}
                </div>
              </div>

              <div>
                <Label htmlFor="persona">AI Persona</Label>
                <Input
                  id="persona"
                  value={formData.persona}
                  onChange={(e) => setFormData(prev => ({ ...prev, persona: e.target.value }))}
                  placeholder="e.g., Professional and helpful, Friendly and casual"
                />
              </div>

              <div>
                <Label htmlFor="signature">Email Signature (Optional)</Label>
                <Textarea
                  id="signature"
                  value={formData.signature}
                  onChange={(e) => setFormData(prev => ({ ...prev, signature: e.target.value }))}
                  placeholder="Best regards,&#10;John Doe&#10;Support Team"
                />
              </div>

              <div className="flex items-center space-x-2">
                <Switch
                  id="auto_send"
                  checked={formData.auto_send}
                  onCheckedChange={(checked) => setFormData(prev => ({ ...prev, auto_send: checked }))}
                />
                <Label htmlFor="auto_send">Auto-send approved replies</Label>
              </div>

              <div className="flex justify-end gap-2">
                <Button type="button" variant="outline" onClick={() => {
                  setIsCreating(false);
                  setIsEditing(false);
                  setEditingAccount(null);
                  resetAccountForm();
                }}>
                  Cancel
                </Button>
                <Button type="submit" className="bg-gradient-to-r from-purple-600 to-pink-600">
                  {isEditing ? 'Update Account' : 'Add Account'}
                </Button>
              </div>
            </form>
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
                      {account.auto_send && (
                        <Badge variant="outline">Auto-send</Badge>
                      )}
                    </CardTitle>
                    <CardDescription>{account.email}</CardDescription>
                  </div>
                  <div className="flex gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleEditAccount(account)}
                      className="text-blue-600 hover:text-blue-700"
                    >
                      <Settings className="h-4 w-4" />
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => toggleAccount(account.id)}
                    >
                      {account.is_active ? <PowerOff className="h-4 w-4" /> : <Power className="h-4 w-4" />}
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
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
                  <div>
                    <span className="font-medium text-slate-700">Provider:</span>
                    <div className="text-slate-600">{providers[account.provider]?.name || account.provider}</div>
                  </div>
                  <div>
                    <span className="font-medium text-slate-700">Server:</span>
                    <div className="text-slate-600">{account.imap_server}:{account.imap_port}</div>
                  </div>
                  <div>
                    <span className="font-medium text-slate-700">Persona:</span>
                    <div className="text-slate-600">{account.persona || "Default"}</div>
                  </div>
                </div>
                {account.last_polled && (
                  <div className="mt-2 text-xs text-slate-500">
                    Last polled: {new Date(account.last_polled).toLocaleString()}
                  </div>
                )}
              </CardContent>
            </Card>
          ))}
          
          {accounts.length === 0 && (
            <Card className="text-center py-12">
              <CardContent>
                <Mail className="h-12 w-12 text-slate-400 mx-auto mb-4" />
                <h3 className="text-lg font-medium text-slate-600 mb-2">No email accounts connected</h3>
                <p className="text-slate-500 mb-4">Connect your first email account to start processing emails</p>
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
  const [emails, setEmails] = useState([]);
  const [selectedEmail, setSelectedEmail] = useState(null);

  useEffect(() => {
    fetchEmails();
  }, []);

  const fetchEmails = async () => {
    try {
      const response = await axios.get(`${API}/emails`);
      setEmails(response.data);
    } catch (error) {
      console.error('Error fetching emails:', error);
    }
  };

  const handleRedraft = async (emailId) => {
    try {
      await axios.post(`${API}/emails/${emailId}/redraft`);
      fetchEmails();
    } catch (error) {
      console.error('Error redrafting email:', error);
    }
  };

  const handleSendEmail = async (emailId) => {
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

  return (
    <Layout>
      <div className="space-y-8">
        <div>
          <h1 className="text-4xl font-bold text-slate-800 mb-2">Email Processing</h1>
          <p className="text-slate-600">View and manage processed emails</p>
        </div>

        <div className="grid gap-6">
          {emails.map(email => (
            <Card key={email.id} className="shadow-lg hover:shadow-xl transition-shadow">
              <CardHeader>
                <div className="flex justify-between items-start">
                  <div className="flex-1">
                    <CardTitle className="flex items-center gap-2 mb-2">
                      <MessageSquare className="h-5 w-5 text-blue-600" />
                      {email.subject}
                      <Badge className={getStatusColor(email.status)}>
                        {email.status.replace('_', ' ')}
                      </Badge>
                    </CardTitle>
                    <CardDescription>
                      From: {email.sender} • {new Date(email.received_at).toLocaleString()}
                    </CardDescription>
                  </div>
                  <div className="flex gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setSelectedEmail(selectedEmail?.id === email.id ? null : email)}
                    >
                      <Eye className="h-4 w-4" />
                    </Button>
                    {email.status === 'ready_to_send' && (
                      <Button
                        size="sm"
                        onClick={() => handleSendEmail(email.id)}
                        className="bg-green-600 hover:bg-green-700"
                      >
                        <Send className="h-4 w-4" />
                      </Button>
                    )}
                    {(email.status === 'needs_redraft' || email.status === 'escalate') && (
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => handleRedraft(email.id)}
                      >
                        <RefreshCw className="h-4 w-4" />
                      </Button>
                    )}
                  </div>
                </div>
              </CardHeader>
              
              {selectedEmail?.id === email.id && (
                <CardContent className="border-t">
                  <Tabs defaultValue="email" className="w-full">
                    <TabsList>
                      <TabsTrigger value="email">Original Email</TabsTrigger>
                      <TabsTrigger value="intents">Intents</TabsTrigger>
                      <TabsTrigger value="draft">Draft Response</TabsTrigger>
                      <TabsTrigger value="validation">Validation</TabsTrigger>
                    </TabsList>
                    
                    <TabsContent value="email" className="space-y-4">
                      <div>
                        <Label className="font-medium">Email Body:</Label>
                        <div className="bg-slate-50 p-4 rounded-lg mt-2">
                          <p className="whitespace-pre-wrap">{email.body}</p>
                        </div>
                      </div>
                    </TabsContent>
                    
                    <TabsContent value="intents" className="space-y-4">
                      {email.intents && email.intents.length > 0 ? (
                        email.intents.map((intent, index) => (
                          <div key={index} className="bg-purple-50 p-4 rounded-lg">
                            <div className="flex justify-between items-center mb-2">
                              <h4 className="font-medium text-purple-800">{intent.name}</h4>
                              <Badge variant="outline">
                                {(intent.confidence * 100).toFixed(1)}% confidence
                              </Badge>
                            </div>
                            <p className="text-sm text-purple-700">{intent.description}</p>
                          </div>
                        ))
                      ) : (
                        <p className="text-slate-500">No intents identified</p>
                      )}
                    </TabsContent>
                    
                    <TabsContent value="draft" className="space-y-4">
                      {email.draft ? (
                        <div>
                          <Label className="font-medium">Generated Draft:</Label>
                          <div className="bg-green-50 p-4 rounded-lg mt-2">
                            <p className="whitespace-pre-wrap">{email.draft}</p>
                          </div>
                        </div>
                      ) : (
                        <p className="text-slate-500">No draft generated yet</p>
                      )}
                    </TabsContent>
                    
                    <TabsContent value="validation" className="space-y-4">
                      {email.validation_result ? (
                        <div>
                          <Label className="font-medium">Validation Result:</Label>
                          <div className={`p-4 rounded-lg mt-2 ${
                            email.validation_result.status === 'PASS' 
                              ? 'bg-green-50 text-green-800' 
                              : 'bg-red-50 text-red-800'
                          }`}>
                            <p className="font-medium mb-2">{email.validation_result.status}</p>
                            <p className="whitespace-pre-wrap">{email.validation_result.feedback}</p>
                          </div>
                        </div>
                      ) : (
                        <p className="text-slate-500">No validation result yet</p>
                      )}
                    </TabsContent>
                  </Tabs>
                </CardContent>
              )}
            </Card>
          ))}
          
          {emails.length === 0 && (
            <Card className="text-center py-12">
              <CardContent>
                <MessageSquare className="h-12 w-12 text-slate-400 mx-auto mb-4" />
                <h3 className="text-lg font-medium text-slate-600 mb-2">No emails processed yet</h3>
                <p className="text-slate-500">Processed emails will appear here</p>
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

export default App;