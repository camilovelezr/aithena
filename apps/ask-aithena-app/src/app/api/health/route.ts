import { NextResponse } from 'next/server';
import { API_URL } from '@/lib/server/config';

export async function GET() {
    try {
        const response = await fetch(`${API_URL}/health`);
        if (!response.ok) {
            return NextResponse.json(
                { status: 'error', statusCode: response.status },
                { status: response.status }
            );
        }
        const data = await response.json();
        return NextResponse.json(data);
    } catch (error) {
        console.error('Health check failed:', error);
        return NextResponse.json(
            { 
                status: 'error',
                error: error instanceof Error ? error.message : 'Unknown error'
            },
            { status: 500 }
        );
    }
} 