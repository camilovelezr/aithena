'use client';

import React, { useState, useEffect } from 'react';
import { StatusUpdate } from '@/lib/types';
import { RABBITMQ_WS_URL } from '@/lib/env';
import { Client } from '@stomp/stompjs';

// Constants for RabbitMQ configuration
const EXCHANGE_NAME = 'ask-aithena-exchange';
const ROUTING_KEY = 'session.*'; // Use wildcard to catch all session messages

class RabbitMQService {
    private client: Client | null = null;
    private statusUpdateCallback: ((status: StatusUpdate) => void) | null = null;
    private connected = false;
    private subscription: any = null;
    private connectionChangeCallback: ((isConnected: boolean) => void) | null = null;
    private heartbeatInterval: any = null;

    connect(): Promise<void> {
        return new Promise((resolve, reject) => {
            if (this.connected && this.client?.connected) {
                console.log('Already connected to RabbitMQ');
                resolve();
                return;
            }

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

            // Expose client for debugging
            (window as any).stompClient = this.client;

            // Connection successful
            this.client.onConnect = (frame) => {
                console.log('Connected to STOMP broker:', frame);
                this.connected = true;
                if (this.connectionChangeCallback) {
                    this.connectionChangeCallback(true);
                }

                // Subscribe to the exchange
                this.subscribe();

                // Set up heartbeat to ensure connection stays active
                this.setupHeartbeat();

                resolve();
            };

            // Connection error
            this.client.onStompError = (frame) => {
                console.error('STOMP Error:', frame.headers, frame.body);
                this.connected = false;
                if (this.connectionChangeCallback) {
                    this.connectionChangeCallback(false);
                }

                // Clear heartbeat on error
                if (this.heartbeatInterval) {
                    clearInterval(this.heartbeatInterval);
                    this.heartbeatInterval = null;
                }

                reject(new Error(`STOMP error: ${frame.headers.message}`));
            };

            this.client.onWebSocketError = (event) => {
                console.error('WebSocket Error:', event);
                this.connected = false;
                if (this.connectionChangeCallback) {
                    this.connectionChangeCallback(false);
                }

                // Clear heartbeat on error
                if (this.heartbeatInterval) {
                    clearInterval(this.heartbeatInterval);
                    this.heartbeatInterval = null;
                }

                reject(event);
            };

            this.client.onDisconnect = () => {
                console.log('Disconnected from STOMP broker');
                this.connected = false;
                if (this.connectionChangeCallback) {
                    this.connectionChangeCallback(false);
                }

                // Clear heartbeat on disconnect
                if (this.heartbeatInterval) {
                    clearInterval(this.heartbeatInterval);
                    this.heartbeatInterval = null;
                }
            };

            // Activate the connection
            try {
                this.client.activate();
            } catch (error) {
                console.error('Failed to activate STOMP client:', error);
                this.connected = false;
                if (this.connectionChangeCallback) {
                    this.connectionChangeCallback(false);
                }

                // Clear heartbeat on error
                if (this.heartbeatInterval) {
                    clearInterval(this.heartbeatInterval);
                    this.heartbeatInterval = null;
                }

                reject(error);
            }
        });
    }

    // Set up a heartbeat to keep the connection active and verify it's working
    private setupHeartbeat(): void {
        // Clear any existing interval
        if (this.heartbeatInterval) {
            clearInterval(this.heartbeatInterval);
        }

        // Check connection every 30 seconds
        this.heartbeatInterval = setInterval(() => {
            if (!this.client?.connected) {
                console.warn('Heartbeat detected disconnected client');
                this.connected = false;
                if (this.connectionChangeCallback) {
                    this.connectionChangeCallback(false);
                }

                // Try to reconnect
                this.connect().catch(err => {
                    console.error('Failed to reconnect during heartbeat:', err);
                });
                return;
            }

            // Send a lightweight heartbeat message
            this.sendHeartbeat();

        }, 30000); // Every 30 seconds
    }

    // Send a lightweight heartbeat message to verify connection
    private sendHeartbeat(): void {
        if (!this.client?.connected) {
            return;
        }

        try {
            this.client.publish({
                destination: `/exchange/${EXCHANGE_NAME}/heartbeat`,
                body: 'heartbeat',
                headers: { 'content-type': 'text/plain' }
            });
            console.log('Heartbeat sent to RabbitMQ');
        } catch (error) {
            console.error('Error sending heartbeat:', error);
            this.connected = false;
            if (this.connectionChangeCallback) {
                this.connectionChangeCallback(false);
            }
        }
    }

    private subscribe(): void {
        if (!this.client?.connected) {
            console.error('Cannot subscribe - STOMP client not connected');
            return;
        }

        try {
            // Unsubscribe if there's an existing subscription
            if (this.subscription) {
                this.subscription.unsubscribe();
                this.subscription = null;
            }

            console.log('Setting up STOMP subscription to:', `/exchange/${EXCHANGE_NAME}/${ROUTING_KEY}`);

            // Subscribe to all messages from the exchange with our routing key pattern
            this.subscription = this.client.subscribe(
                `/exchange/${EXCHANGE_NAME}/${ROUTING_KEY}`,
                (message) => {
                    console.log('⭐ Received STOMP message:', {
                        body: message.body,
                        headers: message.headers,
                        destination: message.headers.destination
                    });

                    try {
                        // Try to parse JSON if it is JSON
                        let messageBody = message.body;
                        try {
                            const parsed = JSON.parse(message.body);
                            messageBody = typeof parsed === 'string' ? parsed : JSON.stringify(parsed);
                        } catch (e) {
                            // Not JSON, use as is
                        }

                        if (this.statusUpdateCallback) {
                            this.statusUpdateCallback({
                                status: messageBody,
                                timestamp: new Date()
                            });
                        }
                    } catch (error) {
                        console.error('Error processing message:', error);
                    }
                },
                {
                    id: 'status-updates-subscription',
                    ack: 'auto'
                }
            );

            console.log('✅ Successfully subscribed to RabbitMQ exchange:', EXCHANGE_NAME);
        } catch (error) {
            console.error('Error subscribing to RabbitMQ:', error);
        }
    }

    onStatusUpdate(callback: (status: StatusUpdate) => void): void {
        this.statusUpdateCallback = callback;
    }

    onConnectionChange(callback: (isConnected: boolean) => void): void {
        this.connectionChangeCallback = callback;
        // Immediately call with current status
        callback(this.connected);
    }

    disconnect(): void {
        // Clear heartbeat
        if (this.heartbeatInterval) {
            clearInterval(this.heartbeatInterval);
            this.heartbeatInterval = null;
        }

        if (this.client) {
            try {
                // Unsubscribe first
                if (this.subscription) {
                    this.subscription.unsubscribe();
                    this.subscription = null;
                }

                // Then deactivate the client
                this.client.deactivate();
                console.log('STOMP client deactivated');
            } catch (error) {
                console.error('Error disconnecting STOMP client:', error);
            } finally {
                this.client = null;
                this.connected = false;
            }
        }
    }

    // For debugging - check if connected
    isConnected(): boolean {
        const result = this.connected && !!this.client?.connected;

        // Force a heartbeat immediately if we think we're connected
        // This will help verify the connection
        if (result) {
            this.sendHeartbeat();
        }

        return result;
    }

    // For debugging - send a test message
    sendTestMessage(): void {
        if (!this.client?.connected) {
            console.error('Cannot send test message - not connected');
            return;
        }

        try {
            this.client.publish({
                destination: `/exchange/${EXCHANGE_NAME}/session.123`,
                body: 'test_message',
                headers: { 'content-type': 'text/plain' }
            });
            console.log('Test message sent');
        } catch (error) {
            console.error('Error sending test message:', error);
        }
    }
}

// Singleton instance
const rabbitmqService = new RabbitMQService();

export function useRabbitMQ() {
    const [connected, setConnected] = useState(false);
    const [statusUpdates, setStatusUpdates] = useState<StatusUpdate[]>([]);

    // Force check connection directly from service
    const checkConnectionStatus = () => {
        return rabbitmqService.isConnected();
    };

    useEffect(() => {
        // Only run once on component mount
        let mounted = true;

        async function setupConnection() {
            try {
                await rabbitmqService.connect();
                if (mounted) {
                    setConnected(true);
                }
            } catch (error) {
                console.error('RabbitMQ connection failed:', error);
                if (mounted) {
                    setConnected(false);
                }
            }
        }

        setupConnection();

        // Set up the status update callback
        const statusCallback = (status: StatusUpdate) => {
            console.log('Status update received:', status);
            if (mounted) {
                setStatusUpdates(prev => [...prev, status]);
            }
        };

        // Set up connection change callback
        const connectionCallback = (isConnected: boolean) => {
            console.log('Connection status changed:', isConnected);
            if (mounted) {
                setConnected(isConnected);
            }
        };

        rabbitmqService.onStatusUpdate(statusCallback);
        rabbitmqService.onConnectionChange(connectionCallback);

        // Clean up on unmount
        return () => {
            mounted = false;
            // Don't disconnect here - keep the singleton alive
        };
    }, []);

    const clearStatusUpdates = () => {
        setStatusUpdates([]);
    };

    // For debugging
    const sendTestMessage = () => {
        rabbitmqService.sendTestMessage();
    };

    return {
        connected,
        statusUpdates,
        clearStatusUpdates,
        sendTestMessage, // Expose the test function
        checkConnectionStatus // Expose direct connection check
    };
}

export default rabbitmqService;