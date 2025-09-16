import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Button } from './components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './components/ui/card';
import { Input } from './components/ui/input';
import { Label } from './components/ui/label';
import { Textarea } from './components/ui/textarea';
import { Badge } from './components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from './components/ui/tabs';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from './components/ui/select';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from './components/ui/dialog';
import { Alert, AlertDescription } from './components/ui/alert';
import { 
  Calendar, CalendarDays, CalendarPlus, MapPin, Users2, 
  Timer, Plus, Trash2, Edit, Eye, RefreshCw, AlertCircle, 
  CheckCircle, Clock, Zap, Brain, Send
} from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

// Calendar Events Component
export const CalendarEvents = ({ Layout }) => {
  const [events, setEvents] = useState([]);
  const [calendars, setCalendars] = useState([]);
  const [isCreating, setIsCreating] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [editingEvent, setEditingEvent] = useState(null);
  const [formData, setFormData] = useState({
    title: '',
    description: '',
    start_time: '',
    end_time: '',
    timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
    location: '',
    attendees: [],
    calendar_id: '',
    provider_id: ''
  });
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');

  useEffect(() => {
    fetchEvents();
    fetchCalendars();
  }, []);

  const fetchEvents = async () => {
    try {
      const response = await axios.get(`${API}/calendar/events`);
      setEvents(response.data);
    } catch (error) {
      console.error('Error fetching events:', error);
    }
  };

  const fetchCalendars = async () => {
    try {
      const response = await axios.get(`${API}/calendar/calendars`);
      setCalendars(response.data || []);
    } catch (error) {
      console.error('Error fetching calendars:', error);
      setCalendars([]); // Set empty array on error
    }
  };

  const handleCreateEvent = async (e) => {
    e.preventDefault();
    setLoading(true);
    setMessage('');

    try {
      const eventData = {
        ...formData,
        attendees: formData.attendees.filter(email => email.trim() !== ''),
        start_time: new Date(formData.start_time).toISOString(),
        end_time: new Date(formData.end_time).toISOString()
      };
      await axios.post(`${API}/calendar/events`, eventData);
      setMessage('Event created successfully!');
      setIsCreating(false);
      resetForm();
      fetchEvents();
    } catch (error) {
      setMessage(error.response?.data?.detail || 'Error creating event');
    }
    setLoading(false);
  };

  const handleEditEvent = (event) => {
    setEditingEvent(event);
    setFormData({
      title: event.title,
      description: event.description,
      start_time: new Date(event.start_time).toISOString().slice(0, 16),
      end_time: new Date(event.end_time).toISOString().slice(0, 16),
      timezone: event.timezone,
      location: event.location,
      attendees: event.attendees || [],
      calendar_id: event.calendar_id,
      provider_id: event.provider_id
    });
    setIsEditing(true);
  };

  const handleUpdateEvent = async (e) => {
    e.preventDefault();
    setLoading(true);
    setMessage('');

    try {
      const eventData = {
        ...formData,
        attendees: formData.attendees.filter(email => email.trim() !== ''),
        start_time: new Date(formData.start_time).toISOString(),
        end_time: new Date(formData.end_time).toISOString()
      };
      await axios.put(`${API}/calendar/events/${editingEvent.id}`, eventData);
      setMessage('Event updated successfully!');
      setIsEditing(false);
      setEditingEvent(null);
      resetForm();
      fetchEvents();
    } catch (error) {
      setMessage(error.response?.data?.detail || 'Error updating event');
    }
    setLoading(false);
  };

  const handleDeleteEvent = async (eventId) => {
    try {
      await axios.delete(`${API}/calendar/events/${eventId}`);
      fetchEvents();
    } catch (error) {
      console.error('Error deleting event:', error);
    }
  };

  const resetForm = () => {
    setFormData({
      title: '',
      description: '',
      start_time: '',
      end_time: '',
      timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
      location: '',
      attendees: [],
      calendar_id: '',
      provider_id: ''
    });
  };

  const addAttendee = () => {
    setFormData(prev => ({
      ...prev,
      attendees: [...prev.attendees, '']
    }));
  };

  const updateAttendee = (index, value) => {
    setFormData(prev => ({
      ...prev,
      attendees: prev.attendees.map((email, i) => i === index ? value : email)
    }));
  };

  const removeAttendee = (index) => {
    setFormData(prev => ({
      ...prev,
      attendees: prev.attendees.filter((_, i) => i !== index)
    }));
  };

  return (
    <Layout>
      <div className="space-y-8">
        <div className="flex justify-between items-center">
          <div>
            <h1 className="text-4xl font-bold text-slate-800 mb-2">Calendar Events</h1>
            <p className="text-slate-600">Manage your calendar events and meetings</p>
          </div>
          <Button 
            onClick={() => setIsCreating(true)}
            className="bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-700 hover:to-pink-700"
          >
            <CalendarPlus className="h-4 w-4 mr-2" />
            Create Event
          </Button>
        </div>

        {(!calendars || calendars.length === 0) && (
          <Alert className="border-yellow-200 bg-yellow-50">
            <AlertCircle className="h-4 w-4 text-yellow-600" />
            <AlertDescription className="text-yellow-700">
              No calendars available. Please set up calendar providers first by visiting the 
              <a href="/calendar-providers" className="underline ml-1">Calendar Providers</a> page.
            </AlertDescription>
          </Alert>
        )}

        {message && (
          <Alert className={message.includes('success') ? 'border-green-200 bg-green-50' : 'border-red-200 bg-red-50'}>
            <AlertCircle className={`h-4 w-4 ${message.includes('success') ? 'text-green-600' : 'text-red-600'}`} />
            <AlertDescription className={message.includes('success') ? 'text-green-700' : 'text-red-700'}>
              {message}
            </AlertDescription>
          </Alert>
        )}

        {/* Create/Edit Event Dialog */}
        <Dialog open={isCreating || isEditing} onOpenChange={(open) => {
          if (!open) {
            setIsCreating(false);
            setIsEditing(false);
            setEditingEvent(null);
            resetForm();
            setMessage('');
          }
        }}>
          <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
            <DialogHeader>
              <DialogTitle>{isEditing ? 'Edit Event' : 'Create New Event'}</DialogTitle>
              <DialogDescription>
                {isEditing ? 'Update event details.' : 'Create a new calendar event.'}
              </DialogDescription>
            </DialogHeader>
            <form onSubmit={isEditing ? handleUpdateEvent : handleCreateEvent} className="space-y-6">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label htmlFor="title">Event Title</Label>
                  <Input
                    id="title"
                    value={formData.title}
                    onChange={(e) => setFormData(prev => ({ ...prev, title: e.target.value }))}
                    placeholder="Meeting with team"
                    required
                  />
                </div>
                <div>
                  <Label htmlFor="calendar_id">Calendar</Label>
                  <Select 
                    value={formData.calendar_id} 
                    onValueChange={(value) => {
                      const selectedCalendar = calendars && calendars.find(cal => cal.id === value);
                      setFormData(prev => ({ 
                        ...prev, 
                        calendar_id: value,
                        provider_id: selectedCalendar?.provider_id || ''
                      }));
                    }}
                    required
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Select calendar" />
                    </SelectTrigger>
                    <SelectContent>
                      {calendars && calendars.length > 0 ? (
                        calendars.map(calendar => (
                          <SelectItem key={calendar.id} value={calendar.id}>
                            {calendar.name} ({calendar.provider_name})
                          </SelectItem>
                        ))
                      ) : (
                        <SelectItem value="" disabled>
                          No calendars available - Please set up calendar providers first
                        </SelectItem>
                      )}
                    </SelectContent>
                  </Select>
                </div>
              </div>

              <div>
                <Label htmlFor="description">Description</Label>
                <Textarea
                  id="description"
                  value={formData.description}
                  onChange={(e) => setFormData(prev => ({ ...prev, description: e.target.value }))}
                  placeholder="Event description..."
                  rows={3}
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label htmlFor="start_time">Start Time</Label>
                  <Input
                    id="start_time"
                    type="datetime-local"
                    value={formData.start_time}
                    onChange={(e) => setFormData(prev => ({ ...prev, start_time: e.target.value }))}
                    required
                  />
                </div>
                <div>
                  <Label htmlFor="end_time">End Time</Label>
                  <Input
                    id="end_time"
                    type="datetime-local"
                    value={formData.end_time}
                    onChange={(e) => setFormData(prev => ({ ...prev, end_time: e.target.value }))}
                    required
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label htmlFor="location">Location</Label>
                  <Input
                    id="location"
                    value={formData.location}
                    onChange={(e) => setFormData(prev => ({ ...prev, location: e.target.value }))}
                    placeholder="Conference room, Zoom link, etc."
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
              </div>

              <div>
                <Label>Attendees</Label>
                {formData.attendees.map((email, index) => (
                  <div key={index} className="flex gap-2 mt-2">
                    <Input
                      value={email}
                      onChange={(e) => updateAttendee(index, e.target.value)}
                      placeholder="attendee@example.com"
                      type="email"
                    />
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      onClick={() => removeAttendee(index)}
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                ))}
                <Button type="button" variant="outline" onClick={addAttendee} className="mt-2">
                  <Plus className="h-4 w-4 mr-2" />
                  Add Attendee
                </Button>
              </div>

              <div className="flex justify-end gap-2">
                <Button type="button" variant="outline" onClick={() => {
                  setIsCreating(false);
                  setIsEditing(false);
                  setEditingEvent(null);
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
                      {isEditing ? 'Updating...' : 'Creating...'}
                    </>
                  ) : (
                    <>
                      <CalendarPlus className="h-4 w-4 mr-2" />
                      {isEditing ? 'Update Event' : 'Create Event'}
                    </>
                  )}
                </Button>
              </div>
            </form>
          </DialogContent>
        </Dialog>

        {/* Events List */}
        <div className="grid gap-6">
          {events.map(event => (
            <Card key={event.id} className="shadow-lg hover:shadow-xl transition-shadow">
              <CardHeader>
                <div className="flex justify-between items-start">
                  <div>
                    <CardTitle className="flex items-center gap-2">
                      <CalendarDays className="h-5 w-5 text-blue-600" />
                      {event.title}
                      <Badge variant={event.status === 'confirmed' ? "default" : "secondary"}>
                        {event.status}
                      </Badge>
                    </CardTitle>
                    <CardDescription>{event.description}</CardDescription>
                  </div>
                  <div className="flex gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleEditEvent(event)}
                      className="text-blue-600 hover:text-blue-700"
                    >
                      <Edit className="h-4 w-4" />
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleDeleteEvent(event.id)}
                      className="text-red-600 hover:text-red-700"
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
                  <div>
                    <span className="font-medium text-slate-700 flex items-center gap-1">
                      <Clock className="h-4 w-4" />
                      Start:
                    </span>
                    <div className="text-slate-600">{new Date(event.start_time).toLocaleString()}</div>
                  </div>
                  <div>
                    <span className="font-medium text-slate-700 flex items-center gap-1">
                      <Clock className="h-4 w-4" />
                      End:
                    </span>
                    <div className="text-slate-600">{new Date(event.end_time).toLocaleString()}</div>
                  </div>
                  {event.location && (
                    <div>
                      <span className="font-medium text-slate-700 flex items-center gap-1">
                        <MapPin className="h-4 w-4" />
                        Location:
                      </span>
                      <div className="text-slate-600">{event.location}</div>
                    </div>
                  )}
                  {event.attendees && event.attendees.length > 0 && (
                    <div>
                      <span className="font-medium text-slate-700 flex items-center gap-1">
                        <Users2 className="h-4 w-4" />
                        Attendees:
                      </span>
                      <div className="text-slate-600">{event.attendees.length} participants</div>
                    </div>
                  )}
                </div>
                {event.attendees && event.attendees.length > 0 && (
                  <div className="mt-4">
                    <span className="font-medium text-slate-700 text-sm">Participants:</span>
                    <div className="flex flex-wrap gap-2 mt-2">
                      {event.attendees.slice(0, 3).map((email, index) => (
                        <Badge key={index} variant="outline" className="text-xs">
                          {email}
                        </Badge>
                      ))}
                      {event.attendees.length > 3 && (
                        <Badge variant="outline" className="text-xs">
                          +{event.attendees.length - 3} more
                        </Badge>
                      )}
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>
          ))}
          
          {events.length === 0 && (
            <Card className="text-center py-12">
              <CardContent>
                <CalendarDays className="h-12 w-12 text-slate-400 mx-auto mb-4" />
                <h3 className="text-lg font-medium text-slate-600 mb-2">No events scheduled</h3>
                <p className="text-slate-500 mb-4">Create your first calendar event to get started</p>
                <Button 
                  onClick={() => setIsCreating(true)}
                  className="bg-gradient-to-r from-purple-600 to-pink-600"
                >
                  <CalendarPlus className="h-4 w-4 mr-2" />
                  Create First Event
                </Button>
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </Layout>
  );
};

// Meeting Detection Component
export const MeetingDetection = ({ Layout }) => {
  const [meetingIntents, setMeetingIntents] = useState([]);
  const [testMode, setTestMode] = useState(false);
  const [testData, setTestData] = useState({
    email_content: '',
    sender: '',
    subject: '',
    user_timezone: Intl.DateTimeFormat().resolvedOptions().timeZone
  });
  const [detectionResult, setDetectionResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');

  useEffect(() => {
    fetchMeetingIntents();
  }, []);

  const fetchMeetingIntents = async () => {
    try {
      const response = await axios.get(`${API}/calendar/meeting-intents`);
      setMeetingIntents(response.data);
    } catch (error) {
      console.error('Error fetching meeting intents:', error);
    }
  };

  const handleTestDetection = async (e) => {
    e.preventDefault();
    setLoading(true);
    setMessage('');
    setDetectionResult(null);

    try {
      const response = await axios.post(`${API}/calendar/detect-meeting`, testData);
      setDetectionResult(response.data);
      if (response.data.meeting_detected) {
        setMessage('Meeting detected successfully!');
      } else {
        setMessage('No meeting detected in the email content.');
      }
    } catch (error) {
      setMessage(error.response?.data?.detail || 'Error detecting meeting');
    }
    setLoading(false);
  };

  const createEventFromDetection = async (intent) => {
    setLoading(true);
    try {
      await axios.post(`${API}/calendar/meeting-intents/${intent.id}/create-event`);
      setMessage('Event created successfully from meeting detection!');
      fetchMeetingIntents();
    } catch (error) {
      setMessage(error.response?.data?.detail || 'Error creating event');
    }
    setLoading(false);
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'created': return 'bg-green-100 text-green-800 border-green-200';
      case 'processed': return 'bg-blue-100 text-blue-800 border-blue-200';
      case 'detected': return 'bg-yellow-100 text-yellow-800 border-yellow-200';
      case 'failed': return 'bg-red-100 text-red-800 border-red-200';
      default: return 'bg-slate-100 text-slate-800 border-slate-200';
    }
  };

  const getStatusIcon = (status) => {
    switch (status) {
      case 'created': return <CheckCircle className="h-4 w-4" />;
      case 'processed': return <Zap className="h-4 w-4" />;
      case 'detected': return <Eye className="h-4 w-4" />;
      case 'failed': return <AlertCircle className="h-4 w-4" />;
      default: return <Clock className="h-4 w-4" />;
    }
  };

  return (
    <Layout>
      <div className="space-y-8">
        <div className="flex justify-between items-center">
          <div>
            <h1 className="text-4xl font-bold text-slate-800 mb-2">Meeting Detection</h1>
            <p className="text-slate-600">AI-powered meeting detection from email content</p>
          </div>
          <Button 
            onClick={() => setTestMode(!testMode)}
            variant={testMode ? "default" : "outline"}
            className={testMode ? "bg-gradient-to-r from-purple-600 to-pink-600" : ""}
          >
            <Brain className="h-4 w-4 mr-2" />
            {testMode ? 'Exit Test Mode' : 'Test Detection'}
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

        {testMode && (
          <Card className="shadow-lg">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Brain className="h-5 w-5 text-purple-600" />
                Test Meeting Detection
              </CardTitle>
              <CardDescription>
                Test the AI meeting detection system with sample email content
              </CardDescription>
            </CardHeader>
            <CardContent>
              <form onSubmit={handleTestDetection} className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <Label htmlFor="sender">Email Sender</Label>
                    <Input
                      id="sender"
                      value={testData.sender}
                      onChange={(e) => setTestData(prev => ({ ...prev, sender: e.target.value }))}
                      placeholder="john@example.com"
                      required
                    />
                  </div>
                  <div>
                    <Label htmlFor="subject">Email Subject</Label>
                    <Input
                      id="subject"
                      value={testData.subject}
                      onChange={(e) => setTestData(prev => ({ ...prev, subject: e.target.value }))}
                      placeholder="Meeting tomorrow at 2 PM"
                      required
                    />
                  </div>
                </div>

                <div>
                  <Label htmlFor="email_content">Email Content</Label>
                  <Textarea
                    id="email_content"
                    value={testData.email_content}
                    onChange={(e) => setTestData(prev => ({ ...prev, email_content: e.target.value }))}
                    placeholder="Hi, let's schedule a meeting tomorrow at 2 PM in the conference room to discuss the project..."
                    rows={6}
                    required
                  />
                </div>

                <div>
                  <Label htmlFor="user_timezone">Your Timezone</Label>
                  <Input
                    id="user_timezone"
                    value={testData.user_timezone}
                    onChange={(e) => setTestData(prev => ({ ...prev, user_timezone: e.target.value }))}
                    placeholder="Your timezone"
                  />
                </div>

                <Button 
                  type="submit" 
                  disabled={loading}
                  className="w-full bg-gradient-to-r from-purple-600 to-pink-600"
                >
                  {loading ? (
                    <>
                      <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
                      Analyzing...
                    </>
                  ) : (
                    <>
                      <Brain className="h-4 w-4 mr-2" />
                      Analyze Email Content
                    </>
                  )}
                </Button>
              </form>

              {detectionResult && (
                <div className="mt-6 p-4 border rounded-lg bg-slate-50">
                  <h4 className="font-semibold mb-3">Detection Result:</h4>
                  <div className="space-y-2">
                    <div className="flex items-center gap-2">
                      <Badge className={detectionResult.meeting_detected ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}>
                        {detectionResult.meeting_detected ? 'Meeting Detected' : 'No Meeting'}
                      </Badge>
                      <span className="text-sm text-slate-600">
                        Confidence: {(detectionResult.confidence_score * 100).toFixed(1)}%
                      </span>
                    </div>
                    
                    {detectionResult.meeting_detected && (
                      <>
                        {detectionResult.detected_datetime && (
                          <div>
                            <span className="font-medium">Detected Time:</span>
                            <span className="ml-2">{new Date(detectionResult.detected_datetime).toLocaleString()}</span>
                          </div>
                        )}
                        {detectionResult.detected_title && (
                          <div>
                            <span className="font-medium">Title:</span>
                            <span className="ml-2">{detectionResult.detected_title}</span>
                          </div>
                        )}
                        {detectionResult.detected_location && (
                          <div>
                            <span className="font-medium">Location:</span>
                            <span className="ml-2">{detectionResult.detected_location}</span>
                          </div>
                        )}
                        {detectionResult.detected_attendees && detectionResult.detected_attendees.length > 0 && (
                          <div>
                            <span className="font-medium">Attendees:</span>
                            <span className="ml-2">{detectionResult.detected_attendees.join(', ')}</span>
                          </div>
                        )}
                        <div>
                          <span className="font-medium">Suggested Duration:</span>
                          <span className="ml-2">{detectionResult.suggested_duration} minutes</span>
                        </div>
                      </>
                    )}
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        )}

        {/* Meeting Intents List */}
        <div className="grid gap-6">
          <Card className="shadow-lg">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Users2 className="h-5 w-5 text-blue-600" />
                Detected Meeting Intents
              </CardTitle>
              <CardDescription>
                Meetings automatically detected from your email conversations
              </CardDescription>
            </CardHeader>
            <CardContent>
              {meetingIntents.length > 0 ? (
                <div className="space-y-4">
                  {meetingIntents.map(intent => (
                    <div key={intent.id} className="border rounded-lg p-4 hover:bg-slate-50 transition-colors">
                      <div className="flex justify-between items-start mb-3">
                        <div>
                          <div className="flex items-center gap-2 mb-2">
                            <Badge className={getStatusColor(intent.status)} variant="outline">
                              {getStatusIcon(intent.status)}
                              <span className="ml-1">{intent.status}</span>
                            </Badge>
                            <span className="text-sm text-slate-500">
                              Confidence: {(intent.confidence_score * 100).toFixed(1)}%
                            </span>
                          </div>
                          {intent.detected_title && (
                            <h4 className="font-semibold text-lg">{intent.detected_title}</h4>
                          )}
                        </div>
                        
                        {intent.status === 'detected' && (
                          <Button
                            size="sm"
                            onClick={() => createEventFromDetection(intent)}
                            disabled={loading}
                            className="bg-green-600 hover:bg-green-700"
                          >
                            <CalendarPlus className="h-4 w-4 mr-1" />
                            Create Event
                          </Button>
                        )}
                      </div>
                      
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
                        {intent.detected_datetime && (
                          <div>
                            <span className="font-medium text-slate-700">Date & Time:</span>
                            <div className="text-slate-600">{new Date(intent.detected_datetime).toLocaleString()}</div>
                          </div>
                        )}
                        {intent.detected_location && (
                          <div>
                            <span className="font-medium text-slate-700">Location:</span>
                            <div className="text-slate-600">{intent.detected_location}</div>
                          </div>
                        )}
                        <div>
                          <span className="font-medium text-slate-700">Duration:</span>
                          <div className="text-slate-600">{intent.detected_duration} minutes</div>
                        </div>
                        <div>
                          <span className="font-medium text-slate-700">Detected:</span>
                          <div className="text-slate-600">{new Date(intent.created_at).toLocaleString()}</div>
                        </div>
                      </div>
                      
                      {intent.detected_attendees && intent.detected_attendees.length > 0 && (
                        <div className="mt-3">
                          <span className="font-medium text-slate-700 text-sm">Attendees:</span>
                          <div className="flex flex-wrap gap-2 mt-1">
                            {intent.detected_attendees.map((email, index) => (
                              <Badge key={index} variant="outline" className="text-xs">
                                {email}
                              </Badge>
                            ))}
                          </div>
                        </div>
                      )}
                      
                      {intent.error_message && (
                        <div className="mt-3 p-2 bg-red-50 border border-red-200 rounded text-sm text-red-700">
                          Error: {intent.error_message}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-center py-12">
                  <Users2 className="h-12 w-12 text-slate-400 mx-auto mb-4" />
                  <h3 className="text-lg font-medium text-slate-600 mb-2">No meeting intents detected</h3>
                  <p className="text-slate-500 mb-4">Meeting intents will appear here when detected from your emails</p>
                  <Button 
                    onClick={() => setTestMode(true)}
                    className="bg-gradient-to-r from-purple-600 to-pink-600"
                  >
                    <Brain className="h-4 w-4 mr-2" />
                    Test Detection System
                  </Button>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </Layout>
  );
};