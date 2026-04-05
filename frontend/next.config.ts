import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: 'http://nginx:80/api/:path*',
      },
      {
        source: '/shorten',
        destination: 'http://nginx:80/shorten',
      },
      {
        source: '/health/:path*',
        destination: 'http://nginx:80/health/:path*',
      },
    ]
  },
};

export default nextConfig;
