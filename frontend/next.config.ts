import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  serverExternalPackages: ["pdf-parse"],
  cacheComponents: true,
  output: "standalone", // Enable standalone output for Docker
};

export default nextConfig;
