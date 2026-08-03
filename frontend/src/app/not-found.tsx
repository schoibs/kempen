import Link from "next/link";

export default function NotFoundPage() {
  return (
    <div className="route-state">
      <span className="route-state-mark" aria-hidden="true">404</span>
      <p className="eyebrow">Off script</p>
      <h1>This page isn’t part of the campaign.</h1>
      <p>The route may have moved, or the address may be incomplete.</p>
      <Link href="/" className="button button-primary">Return to workspace</Link>
    </div>
  );
}
