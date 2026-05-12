const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,

  // Proxy frontend API calls to the Railway backend.
  async rewrites() {
    return [
      {
        source: "/api/backend/:path*",
        destination: `${apiUrl}/:path*`,
      },
    ];
  },

  // Seoul Open API assets, if any are used through next/image.
  images: {
    domains: ["openapi.seoul.go.kr"],
  },

  ...(process.env.ANALYZE === "true" && {
    // Add next-bundle-analyzer configuration here when enabled.
  }),
};

export default nextConfig;
