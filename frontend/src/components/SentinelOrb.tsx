import { Suspense, useMemo, useRef } from "react";
import { Canvas, useFrame } from "@react-three/fiber";
import { Float } from "@react-three/drei";
import * as THREE from "three";

export type ScanStatusMode = "idle" | "scanning" | "verifying" | "breach" | "secure";

interface Props {
  scanStatus?: ScanStatusMode;
  className?: string;
  compact?: boolean;
}

const PALETTE: Record<
  ScanStatusMode,
  { color: string; emissive: string; speed: number; pulse: number; label: string }
> = {
  idle: { color: "#10b981", emissive: "#059669", speed: 0.35, pulse: 0.04, label: "Neural-Link Standby" },
  scanning: { color: "#eab308", emissive: "#ca8a04", speed: 1.2, pulse: 0.14, label: "Scanning Mesh" },
  verifying: { color: "#f97316", emissive: "#ea580c", speed: 2.0, pulse: 0.2, label: "Autopsy Verify" },
  breach: { color: "#ef4444", emissive: "#dc2626", speed: 3.5, pulse: 0.35, label: "Breach Detected" },
  secure: { color: "#10b981", emissive: "#047857", speed: 0.2, pulse: 0.02, label: "Perimeter Secure" },
};

function NeuralLinkOrb({ scanStatus }: { scanStatus: ScanStatusMode }) {
  const coreRef = useRef<THREE.Mesh>(null);
  const wireA = useRef<THREE.Mesh>(null);
  const wireB = useRef<THREE.Mesh>(null);
  const ringRef = useRef<THREE.Mesh>(null);
  const cfg = PALETTE[scanStatus];
  const chaotic = scanStatus === "breach";

  useFrame((state) => {
    const t = state.clock.elapsedTime;
    const flicker = chaotic ? Math.sin(t * 18) * 0.08 : 0;
    const pulse = 1 + Math.sin(t * cfg.speed * 3) * cfg.pulse + flicker;

    if (coreRef.current) {
      coreRef.current.rotation.y = t * cfg.speed * 0.4;
      coreRef.current.scale.setScalar(pulse * 0.55);
    }
    if (wireA.current) {
      wireA.current.rotation.x = t * cfg.speed * 0.5;
      wireA.current.rotation.z = t * cfg.speed * 0.25;
    }
    if (wireB.current) {
      wireB.current.rotation.y = -t * cfg.speed * 0.65;
      wireB.current.rotation.x = Math.sin(t * 0.4) * 0.3;
    }
    if (ringRef.current) {
      ringRef.current.rotation.z = t * cfg.speed * 0.2;
    }
  });

  return (
    <Float speed={cfg.speed} rotationIntensity={chaotic ? 0.9 : 0.35} floatIntensity={0.45}>
      <group>
        <mesh ref={coreRef}>
          <icosahedronGeometry args={[0.85, 1]} />
          <meshBasicMaterial color={cfg.emissive} wireframe transparent opacity={0.55} />
        </mesh>
        <mesh ref={wireA}>
          <icosahedronGeometry args={[1.15, 2]} />
          <meshBasicMaterial color={cfg.color} wireframe transparent opacity={0.42} />
        </mesh>
        <mesh ref={wireB}>
          <octahedronGeometry args={[1.35, 0]} />
          <meshBasicMaterial color={cfg.color} wireframe transparent opacity={0.28} />
        </mesh>
        <mesh ref={ringRef} rotation={[Math.PI / 2, 0, 0]}>
          <torusGeometry args={[1.5, 0.012, 8, 64]} />
          <meshBasicMaterial color={cfg.emissive} transparent opacity={0.65} />
        </mesh>
        <pointLight color={cfg.emissive} intensity={chaotic ? 3.2 : 1.6} distance={8} />
        <ambientLight intensity={0.12} />
      </group>
    </Float>
  );
}

export default function SentinelOrb({ scanStatus = "idle", className = "", compact = false }: Props) {
  const height = compact ? "h-48" : "h-[420px]";
  const camera = useMemo(
    () => ({ position: [0, 0, compact ? 4 : 3.4] as [number, number, number], fov: 45 }),
    [compact]
  );
  const cfg = PALETTE[scanStatus];

  return (
    <div className={`relative overflow-hidden rounded-2xl border border-white/5 ${height} ${className}`}>
      <div className="pointer-events-none absolute inset-0 bg-gradient-to-b from-emerald-500/5 via-transparent to-orange-500/5" />
      <Canvas camera={camera} dpr={[1, 1.5]} gl={{ antialias: true, alpha: true }}>
        <Suspense fallback={null}>
          <NeuralLinkOrb scanStatus={scanStatus} />
        </Suspense>
      </Canvas>
      <div className="pointer-events-none absolute bottom-3 left-0 right-0 text-center font-mono text-[10px] uppercase tracking-[0.3em] text-cyber-muted">
        {cfg.label}
      </div>
    </div>
  );
}

export function MiniOrbCanvas({ scanStatus = "idle" }: { scanStatus?: ScanStatusMode }) {
  return (
    <div className="h-16 w-16 overflow-hidden rounded-full border border-emerald-500/30 bg-black/40">
      <Canvas camera={{ position: [0, 0, 3], fov: 50 }}>
        <Suspense fallback={null}>
          <NeuralLinkOrb scanStatus={scanStatus} />
        </Suspense>
      </Canvas>
    </div>
  );
}
