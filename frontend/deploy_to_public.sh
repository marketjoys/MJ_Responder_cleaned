#!/bin/bash

# Deploy Frontend Build to Public Folder
# Usage: ./deploy_to_public.sh /path/to/public/folder

if [ -z "$1" ]; then
    echo "❌ Error: Please provide the public folder path"
    echo "Usage: ./deploy_to_public.sh /path/to/public/folder"
    echo ""
    echo "Examples:"
    echo "  ./deploy_to_public.sh /var/www/html"
    echo "  ./deploy_to_public.sh /usr/share/nginx/html"
    echo "  ./deploy_to_public.sh ~/public_html"
    exit 1
fi

PUBLIC_FOLDER=$1

# Check if build folder exists
if [ ! -d "/app/frontend/build" ]; then
    echo "❌ Build folder not found. Please run build_production.sh first"
    exit 1
fi

# Check if public folder exists
if [ ! -d "$PUBLIC_FOLDER" ]; then
    echo "❌ Public folder does not exist: $PUBLIC_FOLDER"
    read -p "Create it? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        mkdir -p "$PUBLIC_FOLDER"
        echo "✅ Created folder: $PUBLIC_FOLDER"
    else
        exit 1
    fi
fi

echo "🚀 Deploying frontend to: $PUBLIC_FOLDER"
echo "======================================================"

# Backup existing files if they exist
if [ "$(ls -A $PUBLIC_FOLDER 2>/dev/null)" ]; then
    BACKUP_FOLDER="${PUBLIC_FOLDER}_backup_$(date +%Y%m%d_%H%M%S)"
    echo "📦 Creating backup: $BACKUP_FOLDER"
    cp -r "$PUBLIC_FOLDER" "$BACKUP_FOLDER"
fi

# Clear the public folder (except hidden files)
echo "🧹 Clearing public folder..."
rm -rf "$PUBLIC_FOLDER"/*

# Copy build files
echo "📂 Copying build files..."
cp -r /app/frontend/build/* "$PUBLIC_FOLDER/"

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Deployment completed successfully!"
    echo "📂 Files deployed to: $PUBLIC_FOLDER"
    echo ""
    echo "📋 Next steps:"
    echo "   1. Ensure backend is running on port 9000"
    echo "   2. Configure web server (Nginx/Apache) if needed"
    echo "   3. Test the application at your domain"
    echo ""
    echo "🔍 To verify deployment:"
    echo "   ls -la $PUBLIC_FOLDER"
else
    echo ""
    echo "❌ Deployment failed!"
    exit 1
fi
