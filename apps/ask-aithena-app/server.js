// Load environment variables from .env.local
require('dotenv').config({ path: '.env.local' });

const http = require('http');
const { parse } = require('url');
const next = require('next');
const httpProxy = require('http-proxy');

const dev = process.env.NODE_ENV !== 'production';
const hostname = dev ? 'localhost' : '0.0.0.0';
const port = parseInt(process.env.PORT || '3000', 10);

// Initialize Next.js
const app = next({ dev, hostname, port });
const handle = app.getRequestHandler();

// Use environment variables directly
const API_URL = process.env.API_URL || 'http://ask-aithena-agent-service:8000';
const RABBITMQ_WS_URL = process.env.RABBITMQ_WS_URL || 'ws://rabbitmq-service:15674/ws';

// Log environment variables for debugging
console.log('Environment configuration:');
console.log('NODE_ENV:', process.env.NODE_ENV);
console.log('APP_ENV:', process.env.APP_ENV || 'production');
console.log('API_URL:', API_URL);
console.log('RABBITMQ_WS_URL:', RABBITMQ_WS_URL);

if (!API_URL || !RABBITMQ_WS_URL) {
    console.warn('Environment variables using defaults:');
    console.warn('- API_URL:', API_URL);
    console.warn('- RABBITMQ_WS_URL:', RABBITMQ_WS_URL);
}

// Create a proxy server for WebSocket connections with extended timeouts
const proxy = httpProxy.createProxyServer({
    ws: true,
    changeOrigin: true,
    target: RABBITMQ_WS_URL,
    headers: {
        'Upgrade': 'websocket',
        'Connection': 'Upgrade'
    },
    // Add timeout configurations
    proxyTimeout: 3600000, // 1 hour
    timeout: 3600000, // 1 hour
});

// Handle proxy errors with detailed logging
proxy.on('error', function(err, req, res) {
    console.error('Proxy error:', {
        error: err.message,
        code: err.code,
        stack: err.stack,
        url: req?.url,
        method: req?.method,
        headers: req?.headers
    });
    
    if (res.writeHead) {
        res.writeHead(504, {
            'Content-Type': 'application/json'
        });
        res.end(JSON.stringify({
            error: 'Gateway Timeout',
            message: 'The request took too long to complete'
        }));
    }
});

// Handle WebSocket proxy errors and setup
proxy.on('proxyReqWs', function(proxyReq, req, socket, options, head) {
    console.log('WebSocket proxy request:', {
        url: req.url,
        headers: req.headers,
        target: options.target
    });

    // Add necessary headers for WebSocket upgrade
    proxyReq.setHeader('Upgrade', 'websocket');
    proxyReq.setHeader('Connection', 'Upgrade');
    proxyReq.setHeader('Sec-WebSocket-Version', '13');
    
    socket.on('error', function(err) {
        console.error('WebSocket socket error:', err);
    });
});

// Log successful proxy events with more details
proxy.on('proxyRes', function (proxyRes, req, res) {
    console.log('Proxy response:', {
        statusCode: proxyRes.statusCode,
        headers: proxyRes.headers,
        url: req.url,
        method: req.method,
        timing: {
            startTime: req._startTime,
            endTime: new Date(),
            duration: new Date() - req._startTime
        }
    });
});

app.prepare().then(() => {
    const server = http.createServer(async (req, res) => {
        try {
            // Add request start time for timing
            req._startTime = new Date();
            
            const parsedUrl = parse(req.url, true);
            
            // Handle API requests with extended timeout
            if (parsedUrl.pathname.startsWith('/api/')) {
                return proxy.web(req, res, {
                    target: API_URL,
                    timeout: 3600000, // 1 hour
                    proxyTimeout: 3600000 // 1 hour
                });
            }
            
            await handle(req, res, parsedUrl);
        } catch (err) {
            console.error('Error occurred handling request:', {
                error: err.message,
                stack: err.stack,
                url: req.url,
                method: req.method
            });
            res.statusCode = 500;
            res.end('Internal Server Error');
        }
    });

    // Handle WebSocket upgrade requests
    server.on('upgrade', function (req, socket, head) {
        const parsedUrl = parse(req.url);
        
        // Handle both WebSocket paths
        if (parsedUrl.pathname === '/api/rabbitmq/ws' || parsedUrl.pathname === '/askaithena/rabbitmq/ws') {
            console.log(`Upgrading WebSocket connection on path ${parsedUrl.pathname} to:`, RABBITMQ_WS_URL);
            console.log('Request headers:', req.headers);
            
            // Ensure WebSocket upgrade headers
            req.headers.upgrade = 'websocket';
            req.headers.connection = 'Upgrade';
            
            proxy.ws(req, socket, head, {
                target: RABBITMQ_WS_URL,
                timeout: 3600000, // 1 hour
                proxyTimeout: 3600000, // 1 hour
                headers: {
                    'Upgrade': 'websocket',
                    'Connection': 'Upgrade'
                }
            });
        } else {
            socket.destroy();
        }
    });

    server.listen(port, hostname, (err) => {
        if (err) throw err;
        console.log(`> Ready on http://${hostname}:${port}`);
        console.log('> WebSocket proxy configured for:');
        console.log('  - /api/rabbitmq/ws');
        console.log('  - /askaithena/rabbitmq/ws');
        console.log(`> Using RabbitMQ WebSocket URL: ${RABBITMQ_WS_URL}`);
        console.log('> Proxy timeouts set to 1 hour');
    });
});
