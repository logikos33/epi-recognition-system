/** @type {import('next').NextConfig} */
const nextConfig = {
  images: {
    domains: ['fgfmjceyrvalvfurqprw.supabase.co'],
    remotePatterns: [
      {
        protocol: 'https',
        hostname: '**.supabase.co',
      },
    ],
  },
}

module.exports = nextConfig
