import type { NextConfig } from "next";
const config: NextConfig = { experimental: { cpus: 1, workerThreads: false } };
export default config;
