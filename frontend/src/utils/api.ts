/**
 * API configuration and URL resolution utility.
 * Ensures consistent routing across local development (port 3000 -> 8000)
 * and production deployments (AWS EC2 / custom domains via Nginx reverse proxy).
 */

export function getApiBaseUrl(): string {
  if (typeof window !== 'undefined') {
    // In browser:
    // If running on a remote host (e.g. EC2 public DNS, IP, or domain), use relative path
    // so requests automatically route via the origin through Nginx /api proxy without CORS or domain issues.
    const isLocalhost =
      window.location.hostname === 'localhost' ||
      window.location.hostname === '127.0.0.1';

    if (!isLocalhost) {
      return '';
    }

    // On local machine dev, use configured env var or default to local FastAPI port
    return process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000';
  }

  // In Node.js / SSR:
  return (
    process.env.BACKEND_URL ||
    process.env.NEXT_PUBLIC_API_URL ||
    'http://127.0.0.1:8000'
  );
}

export function apiUrl(path: string): string {
  const cleanPath = path.startsWith('/') ? path : `/${path}`;
  const base = getApiBaseUrl().replace(/\/$/, '');
  return `${base}${cleanPath}`;
}
