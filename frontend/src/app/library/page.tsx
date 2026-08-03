import { CampaignList } from "@/components/CampaignList";

export const metadata = {
  title: "Library",
};

export default function LibraryPage() {
  return (
    <div className="dashboard-page library-page">
      <header className="page-header" aria-labelledby="library-title">
        <div>
          <h1 id="library-title">Library</h1>
          <p>Browse campaigns in progress and revisit completed work.</p>
        </div>
      </header>
      <CampaignList showHeader={false} />
    </div>
  );
}
