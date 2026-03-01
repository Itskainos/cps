import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactCompiler: true,
  async rewrites() {
    return [
      {
        source: "/api/extract",
        destination: process.env.NODE_ENV === "development"
          ? "http://127.0.0.1:5000/api/extract"
          : "/api/extract", // In production (Vercel), it's natively handled
      },
    ];
  },
};

export default nextConfig;
