import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactCompiler: true,
  async rewrites() {
    if (process.env.NODE_ENV !== "development") return [];

    return [
      {
        source: "/api/extract",
        destination: "/api/extract-bridge",
      },
    ];
  },
};

export default nextConfig;
