'use client';

import React, { useState, useEffect } from 'react';
import { StatusUpdate } from '@/lib/types';
import { Client, Frame, Message, StompHeaders } from '@stomp/stompjs';

// Constants for RabbitMQ configuration
const DEFAULT_EXCHANGE = 'ask-aithena-exchange';
const DEFAULT_WS_URL = '/api/rabbitmq/ws'; // Updated to match API response

interface RabbitMQConfig {
    wsUrl: string;
    exchange: string;
}

// Function to get RabbitMQ configuration from server
async function getRabbitMQConfig(): Promise<RabbitMQConfig> {
    try {
        const response = await fetch('/api/rabbitmq');
        if (!response.ok) {
            throw new Error('Failed to fetch RabbitMQ config');
        }
        return await response.json();
    } catch (error) {
        console.error('Error fetching RabbitMQ config:', error);
        // Use default values
        return {
            wsUrl: DEFAULT_WS_URL,
            exchange: DEFAULT_EXCHANGE
        };
    }
}

class RabbitMQService {
    private client: Client | null = null;
    private statusUpdateCallback: ((status: StatusUpdate) => void) | null = null;
    private connected = false;
    private subscription: any = null;
    private connectionChangeCallback: ((isConnected: boolean) => void) | null = null;
    private heartbeatInterval: any = null;
    private sessionId: string | null = null;
    private config: RabbitMQConfig = {
        wsUrl: DEFAULT_WS_URL,
        exchange: DEFAULT_EXCHANGE
    };
    private reconnectAttempts = 0;
    private maxReconnectAttempts = 5;

    isConnected(): boolean {
        return this.connected && this.client?.connected || false;
    }

    onStatusUpdate(callback: (status: StatusUpdate) => void) {
        this.statusUpdateCallback = callback;
    }

    onConnectionChange(callback: (isConnected: boolean) => void) {
        this.connectionChangeCallback = callback;
    }

    setSessionId(sessionId: string) {
        console.log('Setting session ID:', sessionId);
        this.sessionId = sessionId;
        // If already connected, resubscribe with new session ID
        if (this.connected && this.client?.connected) {
            this.subscribe();
        }
    }

    getSessionId(): string | null {
        return this.sessionId;
    }

    async connect(): Promise<void> {
        if (this.connected && this.client?.connected) {
            console.log('Already connected to RabbitMQ');
            return;
        }

        // Get configuration from server
        try {
            this.config = await getRabbitMQConfig();
            console.log('Got RabbitMQ config:', this.config);
        } catch (error) {
            console.error('Failed to get RabbitMQ config:', error);
            // Use defaults
            this.config = {
                wsUrl: DEFAULT_WS_URL,
                exchange: DEFAULT_EXCHANGE
            };
        }

        return new Promise((resolve, reject) => {
            // Clean up existing resources
            this.cleanup();

            // Construct the WebSocket URL
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            const wsUrl = `${protocol}//${window.location.host}${this.config.wsUrl}`;
            console.log('Connecting to STOMP WebSocket at:', wsUrl);

            // Create a new STOMP client
            this.client = new Client({
                brokerURL: wsUrl,
                connectHeaders: {
                    login: 'guest',
                    passcode: 'guest',
                },
                debug: function (str: string) {
                    console.log('STOMP Debug:', str);
                },
                reconnectDelay: 5000,
                heartbeatIncoming: 4000,
                heartbeatOutgoing: 4000
            });

            // Connection successful
            this.client.onConnect = (frame: Frame) => {
                console.log('Connected to STOMP broker:', frame);
                this.connected = true;
                this.reconnectAttempts = 0;
                if (this.connectionChangeCallback) {
                    this.connectionChangeCallback(true);
                }

                // Only subscribe if we have a session ID
                if (this.sessionId) {
                    this.subscribe();
                }

                resolve();
            };

            // Connection error
            this.client.onStompError = (frame: Frame) => {
                console.error('STOMP Error:', frame.headers, frame.body);
                this.handleConnectionError(frame);
                reject(new Error(`STOMP error: ${frame.headers.message}`));
            };

            // WebSocket level error
            this.client.onWebSocketError = (event: Event) => {
                console.error('WebSocket Error:', event);
                this.handleConnectionError();
            };

            // Start the connection
            try {
                this.client.activate();
            } catch (error) {
                console.error('Error activating STOMP client:', error);
                this.handleConnectionError();
                reject(error);
            }
        });
    }

    private handleConnectionError(frame?: Frame) {
        this.connected = false;
        if (this.connectionChangeCallback) {
            this.connectionChangeCallback(false);
        }

        // Attempt to reconnect if within limits
        this.reconnectAttempts++;
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
            console.log(`Reconnect attempt ${this.reconnectAttempts} of ${this.maxReconnectAttempts}`);
            setTimeout(() => this.connect(), 5000 * this.reconnectAttempts);
        } else {
            console.error('Max reconnection attempts reached');
        }
    }

    private cleanup() {
        // Clear any existing heartbeat
        if (this.heartbeatInterval) {
            clearInterval(this.heartbeatInterval);
            this.heartbeatInterval = null;
        }

        // Clean up any existing client
        if (this.client) {
            try {
                this.client.deactivate();
            } catch (e) {
                console.log('Error deactivating existing client:', e);
            }
        }

        // Reset connection state
        this.connected = false;
        if (this.connectionChangeCallback) {
            this.connectionChangeCallback(false);
        }
    }

    disconnect(): void {
        this.cleanup();
    }

    private subscribe(): void {
        if (!this.client || !this.sessionId) {
            console.error('Cannot subscribe: client not initialized or session ID not set');
            return;
        }

        // Unsubscribe from any existing subscription
        if (this.subscription) {
            try {
                this.subscription.unsubscribe();
            } catch (e) {
                console.error('Error unsubscribing:', e);
            }
        }

        // Subscribe to messages for this specific session
        const routingKey = `session.${this.sessionId}`;
        const destination = `/exchange/${this.config.exchange}/${routingKey}`;

        console.log('Subscribing to:', destination);

        this.subscription = this.client.subscribe(destination, (message: Message) => {
            console.log('Received message:', message.body);
            if (this.statusUpdateCallback) {
                try {
                    // Try to parse as JSON first
                    const parsed = JSON.parse(message.body);
                    this.statusUpdateCallback({
                        status: parsed.status || message.body,
                        message: parsed.message || message.body,
                        timestamp: new Date()
                    });
                } catch (e) {
                    // If not JSON, treat the entire message as both status and message
                    this.statusUpdateCallback({
                        status: message.body,
                        message: message.body,
                        timestamp: new Date()
                    });
                }
            }
        });
    }
}

// Create a singleton instance
const rabbitmqService = new RabbitMQService();

// Export the hook
export function useRabbitMQ() {
    const [connected, setConnected] = useState(false);
    const [statusUpdates, setStatusUpdates] = useState<StatusUpdate[]>([]);

    useEffect(() => {
        let mounted = true;

        // Set up callbacks first
        const statusCallback = (status: StatusUpdate) => {
            if (mounted) {
                console.log('Received status update:', status);
                setStatusUpdates((prev: StatusUpdate[]) => [...prev, status]);
            }
        };

        const connectionCallback = (isConnected: boolean) => {
            if (mounted) {
                console.log('Connection status changed:', isConnected);
                setConnected(isConnected);
            }
        };

        rabbitmqService.onStatusUpdate(statusCallback);
        rabbitmqService.onConnectionChange(connectionCallback);

        // Then connect
        rabbitmqService.connect().catch(error => {
            console.error('Failed to connect to RabbitMQ:', error);
        });

        return () => {
            mounted = false;
            rabbitmqService.disconnect();
        };
    }, []);

    const clearStatusUpdates = () => {
        setStatusUpdates([]);
    };

    return {
        connected,
        statusUpdates,
        clearStatusUpdates,
        setSessionId: (sessionId: string) => rabbitmqService.setSessionId(sessionId)
    };
}

export default rabbitmqService;