import React, { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import axios from 'axios';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './components/ui/card';
import { Alert, AlertDescription } from './components/ui/alert';
import { CheckCircle, AlertCircle, RefreshCw } from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const OAuthCallback = ({ provider = 'google' }) => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const [status, setStatus] = useState('processing'); // processing, success, error
  const [message, setMessage] = useState('Processing OAuth callback...');
  const [result, setResult] = useState(null);
  const providerName = provider === 'google' ? 'Google' : 'Microsoft';

  useEffect(() => {
    const handleCallback = async () => {
      const code = searchParams.get('code');
      const state = searchParams.get('state');
      const error = searchParams.get('error');

      if (error) {
        setStatus('error');
        setMessage(`OAuth error: ${error}`);
        return;
      }

      if (!code || !state) {
        setStatus('error');
        setMessage('Missing required OAuth parameters');
        return;
      }

      try {
        const callbackUrl = provider === 'google' 
          ? `${API}/oauth/google/callback`
          : `${API}/oauth/microsoft/callback`;
          
        const response = await axios.get(callbackUrl, {
          params: { code, state }
        });

        setStatus('success');
        setResult(response.data);
        setMessage(`Successfully authorized ${response.data.authorized_services?.join(' and ')} services!`);

        // Redirect to appropriate page after 3 seconds
        setTimeout(() => {
          const services = response.data.authorized_services || [];
          if (services.includes('email') && services.includes('calendar')) {
            navigate('/dashboard');
          } else if (services.includes('email')) {
            navigate('/accounts');
          } else if (services.includes('calendar')) {
            navigate('/calendar-providers');
          } else {
            navigate('/dashboard');
          }
        }, 3000);

      } catch (error) {
        setStatus('error');
        setMessage(error.response?.data?.detail || 'OAuth callback failed');
      }
    };

    handleCallback();
  }, [searchParams, navigate, provider]);

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-purple-50 flex items-center justify-center p-4">
      <Card className="w-full max-w-md shadow-2xl">
        <CardHeader className="text-center">
          <div className="flex justify-center mb-4">
            <div className={`p-3 rounded-xl ${
              status === 'processing' ? 'bg-gradient-to-r from-blue-500 to-purple-500' :
              status === 'success' ? 'bg-gradient-to-r from-green-500 to-emerald-500' :
              'bg-gradient-to-r from-red-500 to-pink-500'
            }`}>
              {status === 'processing' && <RefreshCw className="h-8 w-8 text-white animate-spin" />}
              {status === 'success' && <CheckCircle className="h-8 w-8 text-white" />}
              {status === 'error' && <AlertCircle className="h-8 w-8 text-white" />}
            </div>
          </div>
          <CardTitle className={`text-2xl font-bold ${
            status === 'success' ? 'text-green-600' :
            status === 'error' ? 'text-red-600' :
            'bg-gradient-to-r from-purple-600 to-pink-600 bg-clip-text text-transparent'
          }`}>
            {status === 'processing' && 'Processing Authorization...'}
            {status === 'success' && 'Authorization Successful!'}
            {status === 'error' && 'Authorization Failed'}
          </CardTitle>
          <CardDescription>
            {status === 'processing' && 'Please wait while we complete your Google OAuth authorization.'}
            {status === 'success' && 'You will be redirected automatically.'}
            {status === 'error' && 'There was an issue with the authorization process.'}
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Alert className={
            status === 'success' ? 'border-green-200 bg-green-50' :
            status === 'error' ? 'border-red-200 bg-red-50' :
            'border-blue-200 bg-blue-50'
          }>
            <AlertCircle className={`h-4 w-4 ${
              status === 'success' ? 'text-green-600' :
              status === 'error' ? 'text-red-600' :
              'text-blue-600'
            }`} />
            <AlertDescription className={
              status === 'success' ? 'text-green-700' :
              status === 'error' ? 'text-red-700' :
              'text-blue-700'
            }>
              {message}
            </AlertDescription>
          </Alert>

          {result && status === 'success' && (
            <div className="mt-4 p-4 bg-slate-50 rounded-lg">
              <h4 className="font-semibold mb-2">Authorization Details:</h4>
              <div className="space-y-2 text-sm">
                <div>
                  <span className="font-medium">User:</span> {result.user_info?.name} ({result.user_info?.email})
                </div>
                <div>
                  <span className="font-medium">Authorized Services:</span> 
                  <div className="flex gap-2 mt-1">
                    {result.authorized_services?.map((service) => (
                      <span key={service} className="px-2 py-1 bg-green-100 text-green-800 rounded text-xs capitalize">
                        {service}
                      </span>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          )}

          {status === 'processing' && (
            <div className="mt-4 text-center">
              <div className="inline-flex items-center gap-2 text-slate-600">
                <RefreshCw className="h-4 w-4 animate-spin" />
                <span className="text-sm">Completing authorization...</span>
              </div>
            </div>
          )}

          {status === 'success' && (
            <div className="mt-4 text-center">
              <div className="text-sm text-slate-600">
                Redirecting you automatically in a few seconds...
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
};

export default OAuthCallback;