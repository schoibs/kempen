import type { NextConfig } from "next";

const apiInternalUrl = (process.env.API_INTERNAL_URL ?? "http://127.0.0.1:8000").replace(
  /\/$/,
  "",
);

const nextConfig: NextConfig = {
  output: "standalone",
  async rewrites() {
    return [
      {
        source: "/v1/:path*",
        destination: `${apiInternalUrl}/v1/:path*`,
      },
      {
        source: "/health/:path*",
        destination: `${apiInternalUrl}/health/:path*`,
      },
    ];
  },
};

export default nextConfig;
