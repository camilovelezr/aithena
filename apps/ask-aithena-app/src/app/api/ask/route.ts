import { NextRequest, NextResponse } from 'next/server';
import { API_URL } from '@/lib/server/config';

export async function POST(request: NextRequest) {
    try {
        const { query, mode, sessionId, similarity_n, languages, start_year, end_year } = await request.json();
        
        // Make the request server-side
        const response = await fetch(`${API_URL}/${mode}/ask`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Session-ID': sessionId
            },
            body: JSON.stringify({ 
                query, 
                similarity_n,
                languages,
                start_year,
                end_year
            })
        });

        if (!response.ok) {
            throw new Error(`API request failed: ${response.statusText}`);
        }

        // Create a transform stream to handle the response
        const transformStream = new TransformStream();
        const writer = transformStream.writable.getWriter();
        
        // Start reading the response body
        const reader = response.body?.getReader();
        if (!reader) {
            throw new Error('No response body');
        }

        // Process the stream
        (async () => {
            try {
                while (true) {
                    const { done, value } = await reader.read();
                    if (done) break;
                    await writer.write(value);
                }
            } finally {
                await writer.close();
                reader.releaseLock();
            }
        })();

        // Return the readable part of the transform stream
        return new NextResponse(transformStream.readable, {
            status: 200,
            headers: {
                'Content-Type': 'text/event-stream',
                'Cache-Control': 'no-cache',
                'Connection': 'keep-alive'
            }
        });
    } catch (error) {
        console.error('Error in ask route:', error);
        return NextResponse.json(
            { error: 'Failed to process request' },
            { status: 500 }
        );
    }
}
