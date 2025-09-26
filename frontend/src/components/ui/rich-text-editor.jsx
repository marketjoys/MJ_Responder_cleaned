import React, { useState, useRef } from 'react';
import { Button } from './button';
import { Card, CardContent } from './card';
import { Bold, Italic, Underline, Link2, AtSign, Type } from 'lucide-react';

const RichTextEditor = ({ value = "", onChange, placeholder = "Enter text...", className = "" }) => {
  const editorRef = useRef(null);
  const [isEditing, setIsEditing] = useState(false);

  const handleFormat = (command, value = null) => {
    document.execCommand(command, false, value);
    if (editorRef.current) {
      onChange(editorRef.current.innerHTML);
    }
  };

  const handleContentChange = () => {
    if (editorRef.current) {
      onChange(editorRef.current.innerHTML);
    }
  };

  const handlePlainTextChange = (e) => {
    onChange(e.target.value);
  };

  const convertToPlainText = (html) => {
    const tempDiv = document.createElement('div');
    tempDiv.innerHTML = html;
    return tempDiv.textContent || tempDiv.innerText || '';
  };

  const convertToHtml = (text) => {
    return text.replace(/\n/g, '<br>');
  };

  const insertTemplate = (template) => {
    if (!editorRef.current) {
      // If editor ref is not available, update the value directly
      const currentContent = value || '';
      const plainCurrentContent = convertToPlainText(currentContent);
      const plainTemplate = convertToPlainText(template);
      const newContent = convertToHtml(plainCurrentContent + (plainCurrentContent ? '\n\n' : '') + plainTemplate);
      onChange(newContent);
      return;
    }
    
    const currentContent = editorRef.current.innerHTML || '';
    const newContent = currentContent + (currentContent ? '<br><br>' : '') + template;
    editorRef.current.innerHTML = newContent;
    onChange(newContent);
  };

  const commonSignatureTemplates = [
    {
      name: "Professional",
      content: "Best regards,<br>[Your Name]<br>[Your Title]<br>[Company Name]<br>[Email] | [Phone]"
    },
    {
      name: "Simple",
      content: "Best regards,<br>[Your Name]"
    },
    {
      name: "Corporate",
      content: "Kind regards,<br><br>[Your Name]<br>[Your Title]<br>[Company Name]<br>Email: [Email]<br>Phone: [Phone]<br>Website: [Website]"
    }
  ];

  return (
    <Card className={`w-full ${className}`}>
      <CardContent className="p-4">
        <div className="space-y-4">
          {/* Templates */}
          <div className="flex flex-wrap gap-2">
            <span className="text-sm text-slate-600 font-medium">Templates:</span>
            {commonSignatureTemplates.map((template) => (
              <Button
                key={template.name}
                variant="outline"
                size="sm"
                onClick={() => insertTemplate(template.content)}
                className="text-xs"
              >
                {template.name}
              </Button>
            ))}
          </div>

          {/* Formatting Toolbar */}
          <div className="flex flex-wrap gap-2 border-b pb-2">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => handleFormat('bold')}
              className="p-2"
            >
              <Bold className="h-4 w-4" />
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => handleFormat('italic')}
              className="p-2"
            >
              <Italic className="h-4 w-4" />
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => handleFormat('underline')}
              className="p-2"
            >
              <Underline className="h-4 w-4" />
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => {
                const url = prompt('Enter URL:');
                if (url) handleFormat('createLink', url);
              }}
              className="p-2"
            >
              <Link2 className="h-4 w-4" />
            </Button>
          </div>

          {/* Editor Tabs */}
          <div className="flex gap-2 border-b">
            <Button
              variant={!isEditing ? "default" : "ghost"}
              size="sm"
              onClick={() => setIsEditing(false)}
            >
              <Type className="h-4 w-4 mr-1" />
              Visual
            </Button>
            <Button
              variant={isEditing ? "default" : "ghost"}
              size="sm"
              onClick={() => setIsEditing(true)}
            >
              Text
            </Button>
          </div>

          {/* Editor Area */}
          {!isEditing ? (
            <div
              ref={editorRef}
              contentEditable
              className="min-h-32 p-3 border border-slate-200 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              style={{ minHeight: '120px' }}
              onInput={handleContentChange}
              dangerouslySetInnerHTML={{ __html: value }}
              placeholder={placeholder}
            />
          ) : (
            <textarea
              className="min-h-32 p-3 border border-slate-200 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent w-full resize-y"
              style={{ minHeight: '120px' }}
              value={convertToPlainText(value)}
              onChange={handlePlainTextChange}
              placeholder={placeholder}
            />
          )}

          {/* Helper Text */}
          <div className="text-xs text-slate-500">
            Use [Your Name], [Your Title], [Company Name], [Email], [Phone], [Website] as placeholders that can be replaced later.
          </div>
        </div>
      </CardContent>
    </Card>
  );
};

export { RichTextEditor };