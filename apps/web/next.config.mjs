/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // Standalone output is convenient for the Cloud Run / webview bundle later.
  output: "standalone",
};

export default nextConfig;
