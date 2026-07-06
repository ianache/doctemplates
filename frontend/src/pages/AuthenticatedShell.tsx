// Placeholder authenticated shell. Real copy, backend-fetch, and Sign Out
// wiring against the backend auth contract happen in 01-07-PLAN.
export default function AuthenticatedShell() {
  return (
    <div className="min-h-screen bg-background">
      <div className="bg-surface-container p-md">
        <p className="font-body text-on-surface">You&apos;re signed in</p>
      </div>
    </div>
  );
}
