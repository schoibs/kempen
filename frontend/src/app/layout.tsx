import type { Metadata } from "next";
import Link from "next/link";
import type { ReactNode } from "react";

import "./globals.css";

export const metadata: Metadata = {
  title: {
    default: "Kempen — Campaign Studio",
    template: "%s · Kempen",
  },
  description: "Turn a product image and campaign brief into a complete short-form campaign.",
};

export default function RootLayout({ children }: Readonly<{ children: ReactNode }>) {
  const deploymentLabel = process.env.NEXT_PUBLIC_DEPLOYMENT_LABEL;
  const fakeProviderMode = process.env.NEXT_PUBLIC_FAKE_PROVIDER_MODE;
  const providerLabel = fakeProviderMode === "true"
    ? "Fake providers"
    : fakeProviderMode === "false"
      ? "Real providers"
      : null;
  const environmentBadge = deploymentLabel && providerLabel
    ? `${deploymentLabel} · ${providerLabel}`
    : null;

  return (
    <html lang="en">
      <body>
        <header className="site-header">
          <div className="shell header-inner">
            <Link className="brand" href="/" aria-label="Kempen campaign dashboard">
              <span className="brand-mark" aria-hidden="true"><i /><i /><i /></span>
              <span>
                <strong>KEMPEN</strong>
                <small>Campaign studio</small>
              </span>
            </Link>
            <div className="header-side">
              {environmentBadge && <span className="environment-badge">{environmentBadge}</span>}
              <Link href="/" className="header-link">Campaigns</Link>
            </div>
          </div>
        </header>
        <main className="shell">{children}</main>
        <footer className="site-footer shell">
          <span>Kempen creative systems</span>
          <span>From product signal to campaign story.</span>
        </footer>
      </body>
    </html>
  );
}
