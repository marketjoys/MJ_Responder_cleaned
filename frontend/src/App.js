import React, { useState, useEffect } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import axios from 'axios';
import './App.css';

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

// Icons
import { 
  Mail, Settings, Brain, Database, Users, BarChart3, 
  Plus, Trash2, Eye, Send, RefreshCw, MessageSquare, 
  AlertCircle, CheckCircle, Clock, Zap, Bot
} from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

// Main App Component
function App() {
  return (
    <div className="App">
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Navigate to="/dashboard" replace />} />
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/intents" element={<IntentManagement />} />
          <Route path="/accounts" element={<EmailAccounts />} />
          <Route path="/knowledge" element={<KnowledgeBase />} />
          <Route path="/emails" element={<EmailProcessing />} />
          <Route path="/test" element={<EmailTesting />} />
        </Routes>
      </BrowserRouter>
    </div>
  );
}

// Navigation Component
const Navigation = ({ activeTab, setActiveTab }) => {
  const navItems = [
    { id: 'dashboard', label: 'Dashboard', icon: BarChart3, path: '/dashboard' },
    { id: 'intents', label: 'Intents', icon: Brain, path: '/intents' },
    { id: 'accounts', label: 'Email Accounts', icon: Mail, path: '/accounts' },
    { id: 'knowledge', label: 'Knowledge Base', icon: Database, path: '/knowledge' },
    { id: 'emails', label: 'Email Processing', icon: MessageSquare, path: '/emails' },
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
      
      <ul className="space-y-2">
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
              <span className="font-medium">{item.label}</span>
            </button>
          </li>
        ))}
      </ul>
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

// Dashboard Component
const Dashboard = () => {
  const [stats, setStats] = useState({});
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchStats();
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
        <div>
          <h1 className="text-4xl font-bold text-slate-800 mb-2">Dashboard</h1>
          <p className="text-slate-600">Monitor your automated email assistant performance</p>
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
              <CardTitle className="text-sm font-medium text-green-800">Processed</CardTitle>
              <CheckCircle className="h-4 w-4 text-green-600" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-green-900">{stats.processed_emails || 0}</div>
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
              <CardTitle className="text-sm font-medium text-purple-800">Active Intents</CardTitle>
              <Brain className="h-4 w-4 text-purple-600" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-purple-900">{stats.total_intents || 0}</div>
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
                onClick={() => window.location.href = '/test'} 
                className="w-full bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-700 hover:to-pink-700"
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
                <span>Email Accounts</span>
                <Badge variant={stats.total_accounts > 0 ? "default" : "secondary"}>
                  {stats.total_accounts || 0} active
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

// Intent Management Component
const IntentManagement = () => {
  const [intents, setIntents] = useState([]);
  const [isCreating, setIsCreating] = useState(false);
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
      setFormData({
        name: '',
        description: '',
        examples: [''],
        system_prompt: '',
        confidence_threshold: 0.7,
        follow_up_hours: 24,
        is_meeting_related: false
      });
      fetchIntents();
    } catch (error) {
      console.error('Error creating intent:', error);
    }
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

        {/* Create Intent Dialog */}
        <Dialog open={isCreating} onOpenChange={setIsCreating}>
          <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
            <DialogHeader>
              <DialogTitle>Create New Intent</DialogTitle>
              <DialogDescription>
                Define a new intent that your AI assistant can recognize and respond to.
              </DialogDescription>
            </DialogHeader>
            <form onSubmit={handleCreateIntent} className="space-y-6">
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
                <Button type="button" variant="outline" onClick={() => setIsCreating(false)}>
                  Cancel
                </Button>
                <Button type="submit" className="bg-gradient-to-r from-purple-600 to-pink-600">
                  Create Intent
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
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => handleDeleteIntent(intent.id)}
                    className="text-red-600 hover:text-red-700"
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
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
  const [formData, setFormData] = useState({
    name: '',
    email: '',
    provider: '',
    username: '',
    password: '',
    persona: 'Professional and helpful',
    signature: ''
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
      setFormData({
        name: '',
        email: '',
        provider: '',
        username: '',
        password: '',
        persona: 'Professional and helpful',
        signature: ''
      });
      fetchAccounts();
    } catch (error) {
      console.error('Error creating account:', error);
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

        {/* Create Account Dialog */}
        <Dialog open={isCreating} onOpenChange={setIsCreating}>
          <DialogContent className="max-w-2xl">
            <DialogHeader>
              <DialogTitle>Add Email Account</DialogTitle>
              <DialogDescription>
                Connect a new email account for automated processing.
              </DialogDescription>
            </DialogHeader>
            <form onSubmit={handleCreateAccount} className="space-y-6">
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
                    placeholder="App password or regular password"
                    required
                  />
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

              <div className="flex justify-end gap-2">
                <Button type="button" variant="outline" onClick={() => setIsCreating(false)}>
                  Cancel
                </Button>
                <Button type="submit" className="bg-gradient-to-r from-purple-600 to-pink-600">
                  Add Account
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
                    </CardTitle>
                    <CardDescription>{account.email}</CardDescription>
                  </div>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => handleDeleteAccount(account.id)}
                    className="text-red-600 hover:text-red-700"
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
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
      setFormData({ title: '', content: '', tags: [] });
      fetchKnowledgeBase();
    } catch (error) {
      console.error('Error creating knowledge item:', error);
    }
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

        {/* Create Knowledge Dialog */}
        <Dialog open={isCreating} onOpenChange={setIsCreating}>
          <DialogContent className="max-w-2xl">
            <DialogHeader>
              <DialogTitle>Add Knowledge Item</DialogTitle>
              <DialogDescription>
                Add information that your AI assistant can reference when generating responses.
              </DialogDescription>
            </DialogHeader>
            <form onSubmit={handleCreateKnowledge} className="space-y-6">
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
                <Button type="button" variant="outline" onClick={() => setIsCreating(false)}>
                  Cancel
                </Button>
                <Button type="submit" className="bg-gradient-to-r from-purple-600 to-pink-600">
                  Add Knowledge
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
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => handleDeleteKnowledge(item.id)}
                    className="text-red-600 hover:text-red-700"
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
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

  const getStatusColor = (status) => {
    switch (status) {
      case 'ready_to_send': return 'bg-green-100 text-green-800 border-green-200';
      case 'processing': return 'bg-blue-100 text-blue-800 border-blue-200';
      case 'needs_redraft': return 'bg-amber-100 text-amber-800 border-amber-200';
      case 'escalate': return 'bg-red-100 text-red-800 border-red-200';
      case 'error': return 'bg-red-100 text-red-800 border-red-200';
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