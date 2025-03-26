// Safe access to environment variables
const getEnv = (key: string, defaultValue: string = ''): string => {
    // Use a safe approach that works both on server and client
    if (typeof process !== 'undefined' && process.env) {
        return process.env[key] || defaultValue;
    }
    // For client side where process.env might be undefined
    return defaultValue;
};

export const API_URL = getEnv('NEXT_PUBLIC_API_URL', 'http://localhost:8888');
// Make sure to use the full ws URL for STOMP over WebSocket
export const RABBITMQ_WS_URL = getEnv('NEXT_PUBLIC_RABBITMQ_WS_URL', 'ws://localhost:15674/ws'); 