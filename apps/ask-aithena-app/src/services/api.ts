'use client';

import { AIMode } from '@/lib/types';
import { useState, useEffect } from 'react';
import { useSettings } from '@/lib/settings';

// API Health Status Interface
export interface ApiHealthStatus {
    status: string;
    api?: string;
    litellm?: string;
    statusCode?: number;
    error?: string;
    [key: string]: any; // For any additional fields
}

// Function to ask the AI based on the selected mode
export async function askQuestion(query: string, mode: AIMode, sessionId: string): Promise<Response> {
    try {
        const response = await fetch('/api/ask', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ query, mode, sessionId }),
        });

        if (!response.ok) {
            throw new Error(`API request failed: ${response.statusText}`);
        }

        return response;
    } catch (error) {
        console.error('Error asking question:', error);
        throw error;
    }
}

// Parse streaming response
export async function* parseStreamingResponse(response: Response): AsyncGenerator<string, void, unknown> {
    const reader = response.body?.getReader();
    if (!reader) throw new Error('Response has no readable body');

    const decoder = new TextDecoder();

    try {
        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            const chunk = decoder.decode(value, { stream: true });

            // Yield each chunk immediately for real-time updates
            yield chunk;
        }
    } finally {
        reader.releaseLock();
    }
}

// Health check function
export async function checkApiHealth(): Promise<ApiHealthStatus> {
    try {
        const response = await fetch('/api/health');
        if (!response.ok) {
            return { status: 'error', statusCode: response.status };
        }
        return await response.json();
    } catch (error) {
        console.error('API health check failed:', error);
        return {
            status: 'error',
            error: error instanceof Error ? error.message : 'Unknown error'
        };
    }
}

// Hook for API health status
export function useApiHealth(pollingInterval = 30000) {
    const [healthStatus, setHealthStatus] = useState<ApiHealthStatus>({ status: 'checking...' });
    const [error, setError] = useState<string | null>(null);
    const [loading, setLoading] = useState(false);

    async function refreshStatus() {
        try {
            setLoading(true);
            setError(null);
            const status = await checkApiHealth();
            setHealthStatus(status);
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Unknown error occurred');
            setHealthStatus({ status: 'error' });
        } finally {
            setLoading(false);
        }
    }

    useEffect(() => {
        // Check immediately on mount
        refreshStatus();

        // Set up polling interval
        const intervalId = setInterval(refreshStatus, pollingInterval);

        // Cleanup on unmount
        return () => clearInterval(intervalId);
    }, [pollingInterval]);

    return {
        healthStatus,
        error,
        loading,
        refreshStatus
    };
} 