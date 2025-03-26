// Server-side only configuration
// Using internal Kubernetes service names since all calls are server-side
import 'server-only';
import getConfig from 'next/config';

// Get the server-side runtime configuration
const { serverRuntimeConfig } = getConfig() || { serverRuntimeConfig: {} };

export const API_URL = serverRuntimeConfig.API_URL || process.env.API_URL || 'http://ask-aithena-agent-service:8000';
export const RABBITMQ_WS_URL = serverRuntimeConfig.RABBITMQ_WS_URL || process.env.RABBITMQ_WS_URL || 'ws://rabbitmq-service:15674/ws'; 