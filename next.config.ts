import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactCompiler: true,
  async rewrites() {
    return [
      {
        source: "/api/extract",
        destination: process.env.NODE_ENV === "development"
          ? "/api/extract-bridge"
          : "/api/extract", // In production (Vercel), it's natively handled by api/extract.py
      },
    ];
  },
};

export default nextConfig;
