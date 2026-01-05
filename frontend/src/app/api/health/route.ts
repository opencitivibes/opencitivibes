import { NextResponse } from 'next/server';

export async function GET() {
  return NextResponse.json({
    status: 'healthy',
    timestamp: new Date().toISOString(),
    service: 'frontend',
  });
}

// Disable caching for health checks
export const dynamic = 'force-dynamic';
