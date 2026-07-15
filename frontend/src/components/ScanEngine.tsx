import { Shield } from "lucide-react";

interface Props {
  repoPath: string;
  onChange: (v: string) => void;
  onScan: () => void;
  scanning: boolean;
}

export default function ScanEngine({ repoPath, onChange, onScan, scanning }: Props) {
  return (
    <div className="cyber-panel p-6">
      <div className="mb-4 flex items-center gap-2">
        <Shield className="h-5 w-5 text-cyber-accent" />
        <h2 className="text-lg font-semibold tracking-wide">Scan Engine</h2>
      </div>
      <p className="mb-4 text-sm text-cyber-muted">
        Point Codebreaker at a local repository path to run source + SBOM analysis.
      </p>
      <div className="flex gap-3">
        <input
          className="cyber-input flex-1"
          placeholder="C:\path\to\repository"
          value={repoPath}
          onChange={(e) => onChange(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && onScan()}
        />
        <button className="cyber-btn" onClick={onScan} disabled={scanning || !repoPath.trim()}>
          <Shield className="h-4 w-4" />
          {scanning ? "Scanning..." : "Shield Scan"}
        </button>
      </div>
    </div>
  );
}
