#!/bin/bash
echo "⚡ ElianaMC Service Starting..."

echo "🔀 Starting Java Proxy (port 25565)..."
python3 proxy_java.py &
JAVA_PROXY_PID=$!

echo "🔀 Starting Bedrock Proxy (port 19132)..."
python3 proxy_bedrock.py &
BEDROCK_PROXY_PID=$!

echo "🔐 Starting Auth (port 8008)..."
python3 auth.py &
AUTH_PID=$!

sleep 1

echo "🔧 Starting Backend (port 8007)..."
python3 backend.py &
BACKEND_PID=$!

sleep 2

echo "🌐 Starting Frontend (port 2000)..."
python3 -m http.server 2000 &
FRONTEND_PID=$!

echo ""
echo "✅ ElianaMC Service Running!"
echo "🎮 Java:     port 25565"
echo "🎮 Bedrock:  port 19132"
echo "🌐 Frontend: http://localhost:2000"
echo "🔧 Backend:  http://localhost:8007"
echo ""
echo "Press Ctrl+C to stop all..."

trap "kill $AUTH_PID $JAVA_PROXY_PID $BEDROCK_PROXY_PID $BACKEND_PID $FRONTEND_PID 2>/dev/null; echo '⛔ Stopped.'" EXIT

wait
