import { AIMode } from '@/lib/types';
import { API_URL } from '@/lib/env';
import { useState, useEffect } from 'react';
import { useSettings } from '@/lib/settings';

// Define the base URL for the API
const API_BASE_URL = API_URL;

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
export async function askAithena(query: string, mode: AIMode, similarityN: number = 10): Promise<Response> {
    const endpoint = `/${mode}/ask`;

    try {
        const response = await fetch(`${API_BASE_URL}${endpoint}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                query,
                similarity_n: similarityN // Add the similarity_n parameter
            }),
        });

        if (!response.ok) {
            throw new Error(`API request failed with status ${response.status}`);
        }

        return response;
    } catch (error) {
        console.error('Error asking Aithena:', error);
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
        const response = await fetch(`${API_BASE_URL}/health`);
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