import type { Metadata } from "next";
import type { ReactNode } from "react";

import { AppSidebar } from "@/components/AppSidebar";

import "./globals.css";

export const metadata: Metadata = {
  title: {
    default: "Kempen",
    template: "%s · Kempen",
  },
  description: "Turn a product image and campaign brief into a complete short-form campaign.",
};

export default function RootLayout({ children }: Readonly<{ children: ReactNode }>) {
  const showSidebar = process.env.NEXT_PUBLIC_SHOW_SIDEBAR !== "false";

  return (
    <html lang="en">
      <body>
        <div className={`app-shell${showSidebar ? " has-sidebar" : ""}`}>
          {showSidebar && <AppSidebar />}
          <div className="app-main">
            <main className="shell">{children}</main>
          </div>
        </div>
      </body>
    </html>
  );
}
