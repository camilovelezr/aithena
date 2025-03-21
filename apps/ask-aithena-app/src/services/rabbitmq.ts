'use client';

import React, { useState, useEffect } from 'react';
import { StatusUpdate } from '@/lib/types';
import { RABBITMQ_WS_URL } from '@/lib/env';
import { Client } from '@stomp/stompjs';

// Constants for RabbitMQ configuration
const EXCHANGE_NAME = 'ask-aithena-exchange';

class RabbitMQService {
    private client: Client | null = null;
    private statusUpdateCallback: ((status: StatusUpdate) => void) | null = null;
    private connected = false;
    private subscription: any = null;
    private connectionChangeCallback: ((isConnected: boolean) => void) | null = null;
    private heartbeatInterval: any = null;
    private sessionId: string | null = null;

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

        return new Promise((resolve, reject) => {
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

            console.log('Connecting to STOMP WebSocket at:', RABBITMQ_WS_URL);

            // Create a new STOMP client
            this.client = new Client({
                brokerURL: RABBITMQ_WS_URL,
                connectHeaders: {
                    login: 'guest',
                    passcode: 'guest',
                },
                debug: function (str) {
                    console.log('STOMP Debug:', str);
                },
                reconnectDelay: 5000
            });

            // Connection successful
            this.client.onConnect = (frame) => {
                console.log('Connected to STOMP broker:', frame);
                this.connected = true;
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
            this.client.onStompError = (frame) => {
                console.error('STOMP Error:', frame.headers, frame.body);
                this.connected = false;
                if (this.connectionChangeCallback) {
                    this.connectionChangeCallback(false);
                }
                reject(new Error(`STOMP error: ${frame.headers.message}`));
            };

            // Start the connection
            this.client.activate();
        });
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
        const destination = `/exchange/${EXCHANGE_NAME}/${routingKey}`;

        console.log('Subscribing to:', destination);

        this.subscription = this.client.subscribe(destination, (message) => {
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
                setStatusUpdates(prev => [...prev, status]);
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