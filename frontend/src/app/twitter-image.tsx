import { ImageResponse } from 'next/og';

export const runtime = 'edge';

export const alt = 'Idées pour Montréal';
export const size = {
  width: 1200,
  height: 600,
};
export const contentType = 'image/png';

export default async function TwitterImage() {
  return new ImageResponse(
    <div
      style={{
        background: 'linear-gradient(135deg, #0066CC 0%, #003366 100%)',
        width: '100%',
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        padding: 50,
      }}
    >
      <div
        style={{
          fontSize: 64,
          fontWeight: 'bold',
          color: 'white',
          marginBottom: 16,
        }}
      >
        Idées pour Montréal
      </div>
      <div
        style={{
          fontSize: 28,
          color: 'rgba(255,255,255,0.9)',
          textAlign: 'center',
        }}
      >
        Plateforme citoyenne pour améliorer Montréal
      </div>
    </div>,
    {
      ...size,
    }
  );
}
