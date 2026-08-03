import { CampaignForm } from "@/components/CampaignForm";

export default function WorkspacePage() {
  return (
    <div className="dashboard-page workspace-page">
      <header className="page-header" aria-labelledby="dashboard-title">
        <div>
          <h1 id="dashboard-title">Workspace</h1>
          <p>Create a focused brief and start a new campaign.</p>
        </div>
      </header>
      <CampaignForm />
    </div>
  );
}
