import { CampaignList } from "@/components/CampaignList";

export default function DashboardPage() {
  return (
    <div className="dashboard-page">
      <section className="dashboard-hero" aria-labelledby="dashboard-title">
        <div className="hero-index" aria-hidden="true">K/01</div>
        <div className="hero-copy">
          <p className="eyebrow">Campaign operations</p>
          <h1 id="dashboard-title">Ideas in motion.<br />Stories taking shape.</h1>
          <p>
            Track every product campaign from first analysis to the final frame—without losing
            the creative thread.
          </p>
        </div>
        <div className="hero-signal" aria-hidden="true">
          <span>Brief</span><i />
          <span>Story</span><i />
          <span>Motion</span>
        </div>
      </section>
      <CampaignList />
    </div>
  );
}
