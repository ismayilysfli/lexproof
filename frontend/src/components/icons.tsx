type IconProps = { className?: string };

export function ArrowIcon({
  diagonal = false,
  className,
}: IconProps & { diagonal?: boolean }) {
  return (
    <svg
      className={className}
      width="18"
      height="18"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.6"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      {diagonal ? (
        <path d="M6 18 18 6M6 6h12v12" />
      ) : (
        <path d="M4 12h16m-6-6 6 6-6 6" />
      )}
    </svg>
  );
}

export function DocumentIcon({ className }: IconProps) {
  return (
    <svg
      className={className}
      width="18"
      height="18"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M14 3H5v18h14V8l-5-5Zm0 0v5h5M8 12h8m-8 4h6" />
    </svg>
  );
}

export function StatusIcon({
  kind,
}: {
  kind: "supported" | "contradicted" | "insufficient";
}) {
  return (
    <svg
      width="20"
      height="20"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.7"
      strokeLinecap="round"
      aria-hidden="true"
    >
      <circle cx="12" cy="12" r="9" />
      {kind === "supported" ? (
        <path d="m8 12 3 3 5-6" />
      ) : kind === "contradicted" ? (
        <path d="m9 9 6 6m0-6-6 6" />
      ) : (
        <path d="M12 7v6m0 4h.01" />
      )}
    </svg>
  );
}
