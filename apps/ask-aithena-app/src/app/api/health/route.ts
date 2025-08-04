import { NextResponse } from 'next/server';
import { request } from 'undici';
import { API_URL } from '@/lib/server/config';

export async function GET() {
    try {
        const { body, statusCode } = await request(`${API_URL}/health`, {
            method: 'GET',
            // Health checks should have reasonable timeouts
            bodyTimeout: 30000, // 30 seconds
            headersTimeout: 30000, // 30 seconds
        });
        
        if (statusCode !== 200) {
            return NextResponse.json(
                { status: 'error', statusCode },
                { status: statusCode }
            );
        }
        
        const data = await body.json();
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
