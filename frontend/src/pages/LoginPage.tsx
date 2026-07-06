import { useSearchParams } from "react-router-dom";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL as string;

export default function LoginPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const error = searchParams.get("error");
  const callbackFailed = error === "callback_failed";
  const sessionExpired = error === "session_expired";

  const signIn = () => {
    window.location.href = `${API_BASE_URL}/auth/login`;
  };

  const clearError = () => {
    setSearchParams({});
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-background p-md font-body text-on-surface">
      <div className="mx-auto flex w-full max-w-[400px] flex-col gap-lg rounded-lg border border-outline-variant bg-surface-container-lowest p-xl shadow-sm">
        <div className="space-y-xs">
          <h1 className="font-headings text-[32px] font-bold leading-[40px] tracking-[-0.02em] text-primary">
            Precision Archival
          </h1>
          <p className="font-body text-[11px] font-bold uppercase leading-[16px] tracking-[0.05em] text-on-surface-variant">
            Document Management Platform
          </p>
        </div>

        {callbackFailed ? (
          <div className="rounded border border-error/30 bg-background p-md text-error">
            <h2 className="font-headings text-base font-bold">
              We couldn't sign you in.
            </h2>
            <p className="mt-xs text-sm leading-5">
              Something went wrong completing sign-in. Please try again, or contact your administrator if this keeps happening.
            </p>
            <button
              className="mt-md rounded border border-error px-md py-xs text-sm font-bold text-error hover:bg-error hover:text-white"
              type="button"
              onClick={clearError}
            >
              Try Again
            </button>
          </div>
        ) : null}

        {sessionExpired ? (
          <p className="rounded border border-error/30 bg-background p-sm text-sm font-bold text-error">
            Your session has expired. Please sign in again.
          </p>
        ) : null}

        <div className="space-y-sm">
          <button
            className="w-full rounded bg-primary px-lg py-sm font-body text-sm font-bold text-white hover:bg-primary/90 focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2 focus:ring-offset-surface-container-lowest"
            type="button"
            onClick={signIn}
          >
            Sign In
          </button>
          <p className="text-center text-sm leading-5 text-on-surface-variant">
            Sign in with your organization account to continue.
          </p>
        </div>
      </div>
    </div>
  );
}
