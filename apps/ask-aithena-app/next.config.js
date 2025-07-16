/** @type {import('next').NextConfig} */

// Use environment variables directly from ConfigMap
const API_URL = process.env.API_URL || 'http://ask-aithena-agent-service:8000';
const RABBITMQ_WS_URL = process.env.RABBITMQ_WS_URL || 'ws://rabbitmq-service:15674/ws';

// Log the configuration for debugging
console.log(`[Next.js Config] Environment: ${process.env.APP_ENV || 'production'}`);
console.log(`[Next.js Config] API URL: ${API_URL}`);
console.log(`[Next.js Config] RabbitMQ WS URL: ${RABBITMQ_WS_URL}`);

const nextConfig = {
    reactStrictMode: true,
    swcMinify: true,
    output: 'standalone',
    // Optimize for development
    onDemandEntries: {
        // period (in ms) where the server will keep pages in the buffer
        maxInactiveAge: 25 * 1000,
        // number of pages that should be kept simultaneously without being disposed
        pagesBufferLength: 2,
    },
    // Disable source maps in development for faster builds
    productionBrowserSourceMaps: false,
    webpack: (config, { dev, isServer }) => {
        // Don't override devtool in development to avoid performance issues
        return config;
    },
    serverRuntimeConfig: {
        // Server-side only variables
        API_URL: API_URL,
        RABBITMQ_WS_URL: RABBITMQ_WS_URL,
        APP_ENV: process.env.APP_ENV || 'production',
    },
    // Client-side variables must be prefixed with NEXT_PUBLIC_
    publicRuntimeConfig: {
        API_URL: process.env.NEXT_PUBLIC_API_URL || '/api',
        RABBITMQ_WS_URL: process.env.NEXT_PUBLIC_RABBITMQ_WS_URL || '/askaithena/rabbitmq/ws',
        APP_ENV: process.env.APP_ENV || 'production',
    },
    // Define rewrites to handle proxying
    async rewrites() {
        const rewrites = [
            {
                source: '/api/:path*',
                destination: `${API_URL}/:path*`,
            },
            {
                source: '/api/rabbitmq/ws',
                destination: RABBITMQ_WS_URL.replace('ws://', 'http://'),
            },
            {
                source: '/askaithena/rabbitmq/ws',
                destination: RABBITMQ_WS_URL.replace('ws://', 'http://'),
            }
        ];
        
        return rewrites;
    }
};

module.exports = nextConfig;
