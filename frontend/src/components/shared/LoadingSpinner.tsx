

export function LoadingSpinner({ size = 24 }: { size?: number }) {
  return (
    <div
      style={{
        width: size,
        height: size,
        border: `2px solid var(--border)`,
        borderTop: `2px solid var(--accent-blue)`,
        borderRadius: '50%',
        animation: 'spin 0.8s linear infinite',
      }}
    />
  );
}
