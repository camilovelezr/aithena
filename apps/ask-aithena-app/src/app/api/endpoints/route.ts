import { NextResponse } from 'next/server';
import { API_URL, RABBITMQ_WS_URL } from '@/lib/server/config';

export async function GET() {
    return NextResponse.json({
        apiUrl: API_URL,
        rabbitmqWsUrl: RABBITMQ_WS_URL
    });
} 