import { Shield, Github } from "lucide-react";

interface Props {
  repoPath: string;
  onChange: (v: string) => void;
  onScan: () => void;
  scanning: boolean;
  cloning?: boolean;
}

export default function ScanEngine({ repoPath, onChange, onScan, scanning, cloning }: Props) {
  const isRemote = repoPath.trim().toLowerCase().startsWith("http");

  return (
    <div className="glass-panel p-6">
      <div className="mb-4 flex items-center gap-2">
        {isRemote ? (
          <Github className="h-5 w-5 text-cyber-accent" />
        ) : (
          <Shield className="h-5 w-5 text-cyber-accent" />
        )}
        <h2 className="text-lg font-semibold tracking-wide">Triage Scan Engine</h2>
      </div>
      <p className="mb-4 text-sm text-cyber-muted">
        Scan a local repository path or clone and analyze a public GitHub repository.
      </p>
      <div className="flex gap-3">
        <input
          className="cyber-input flex-1"
          placeholder="Enter Local Path or GitHub Repository URL..."
          value={repoPath}
          onChange={(e) => onChange(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && onScan()}
        />
        <button className="cyber-btn" onClick={onScan} disabled={scanning || !repoPath.trim()}>
          <Shield className="h-4 w-4" />
          {cloning ? "Cloning…" : scanning ? "Scanning…" : "Shield Scan"}
        </button>
      </div>
    </div>
  );
}
