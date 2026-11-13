import type { Metadata } from "next";
import "./globals.css";
import { AppShell } from "@/components/layout/AppShell";
export const metadata: Metadata = { title: "iSquare — Visual Intelligence & Digital Research", description: "An image-first visual intelligence and digital research workspace." };
export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) { return <html lang="en"><body><AppShell>{children}</AppShell></body></html>; }
