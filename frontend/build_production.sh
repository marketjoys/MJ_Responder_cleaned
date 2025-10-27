#!/bin/bash

# Frontend Production Build Script
# This script creates an optimized production build of the React frontend

echo "🎨 Building Email Automation Frontend for Production..."
echo "======================================================"

cd /app/frontend

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
    echo "📦 Installing dependencies..."
    yarn install
else
    echo "✅ Dependencies already installed"
fi

# Clean previous build
echo "🧹 Cleaning previous build..."
rm -rf build

# Create production build
echo "🏗️  Creating production build..."
yarn build

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Build completed successfully!"
    echo "📂 Build location: /app/frontend/build/"
    echo ""
    echo "📋 Next steps:"
    echo "   1. Copy build folder to your public directory:"
    echo "      cp -r /app/frontend/build/* /path/to/public/folder/"
    echo ""
    echo "   2. Or use the provided deployment script:"
    echo "      ./deploy_to_public.sh /path/to/public/folder"
    echo ""
    echo "   3. Make sure backend is running on port 9000"
    echo "   4. Update REACT_APP_BACKEND_URL in .env.production if needed"
else
    echo ""
    echo "❌ Build failed! Please check the errors above."
    exit 1
fi
