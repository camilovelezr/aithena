/** @type {import('next').NextConfig} */
const nextConfig = {
    reactStrictMode: true,
    swcMinify: true,
    output: 'standalone',
    serverRuntimeConfig: {
        // Server-side only variables
        API_URL: process.env.API_URL || 'http://ask-aithena-agent-service:8000',
        RABBITMQ_WS_URL: process.env.RABBITMQ_WS_URL || 'ws://rabbitmq-service:15674/ws',
    },
    // Client-side variables must be prefixed with NEXT_PUBLIC_
    publicRuntimeConfig: {
        API_URL: process.env.NEXT_PUBLIC_API_URL || '/api',
        RABBITMQ_WS_URL: process.env.NEXT_PUBLIC_RABBITMQ_WS_URL || '/api/rabbitmq/ws',
    },
    // Define rewrites to handle proxying
    async rewrites() {
        return [
            {
                source: '/api/:path*',
                destination: 'http://ask-aithena-agent-service:8000/:path*',
            },
            {
                source: '/api/rabbitmq/ws',
                destination: 'http://rabbitmq-service:15674/ws',
            },
            {
                source: '/askaithena/rabbitmq/ws',
                destination: 'http://rabbitmq-service:15674/ws',
            }
        ];
    }
};

module.exports = nextConfig; 