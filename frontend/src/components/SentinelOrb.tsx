import { Suspense, useMemo, useRef } from "react";
import { Canvas, useFrame } from "@react-three/fiber";
import { Float, MeshDistortMaterial, Sphere } from "@react-three/drei";
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
  idle: { color: "#06b6d4", emissive: "#0891b2", speed: 0.35, pulse: 0.04, label: "Standby" },
  scanning: { color: "#eab308", emissive: "#ca8a04", speed: 1.2, pulse: 0.14, label: "Scanning" },
  verifying: { color: "#f97316", emissive: "#ea580c", speed: 2.0, pulse: 0.2, label: "Verifying" },
  breach: { color: "#ef4444", emissive: "#dc2626", speed: 3.5, pulse: 0.35, label: "Breach" },
  secure: { color: "#22c55e", emissive: "#16a34a", speed: 0.2, pulse: 0.02, label: "Secure" },
};

function CyberOrb({ scanStatus }: { scanStatus: ScanStatusMode }) {
  const meshRef = useRef<THREE.Mesh>(null);
  const wireRef = useRef<THREE.Mesh>(null);
  const cfg = PALETTE[scanStatus];
  const chaotic = scanStatus === "breach";

  useFrame((state) => {
    const t = state.clock.elapsedTime;
    const flicker = chaotic ? Math.sin(t * 18) * 0.08 : 0;
    const pulse = 1 + Math.sin(t * cfg.speed * 3) * cfg.pulse + flicker;
    if (meshRef.current) {
      meshRef.current.rotation.y = t * cfg.speed * 0.5;
      meshRef.current.rotation.x = Math.sin(t * 0.3) * 0.2;
      meshRef.current.scale.setScalar(pulse);
    }
    if (wireRef.current) {
      wireRef.current.rotation.y = -t * cfg.speed * 0.7;
      wireRef.current.rotation.z = t * cfg.speed * 0.3;
    }
  });

  return (
    <Float speed={cfg.speed} rotationIntensity={chaotic ? 0.9 : 0.4} floatIntensity={0.6}>
      <group>
        <Sphere ref={meshRef} args={[1, 64, 64]}>
          <MeshDistortMaterial
            color={cfg.color}
            emissive={cfg.emissive}
            emissiveIntensity={chaotic ? 1.5 : 0.65}
            distort={chaotic ? 0.55 : 0.28}
            speed={cfg.speed}
            roughness={0.15}
            metalness={0.85}
            transparent
            opacity={0.92}
          />
        </Sphere>
        <mesh ref={wireRef}>
          <icosahedronGeometry args={[1.35, 2]} />
          <meshBasicMaterial color={cfg.color} wireframe transparent opacity={0.35} />
        </mesh>
        <pointLight color={cfg.emissive} intensity={chaotic ? 3.5 : 1.8} distance={8} />
        <ambientLight intensity={0.15} />
      </group>
    </Float>
  );
}

export default function SentinelOrb({ scanStatus = "idle", className = "", compact = false }: Props) {
  const height = compact ? "h-48" : "h-[420px]";
  const camera = useMemo(
    () => ({ position: [0, 0, compact ? 4 : 3.2] as [number, number, number], fov: 45 }),
    [compact]
  );
  const cfg = PALETTE[scanStatus];

  return (
    <div className={`relative overflow-hidden rounded-2xl ${height} ${className}`}>
      <div className="pointer-events-none absolute inset-0 bg-gradient-to-b from-cyan-500/5 via-transparent to-red-500/5" />
      <Canvas camera={camera} dpr={[1, 1.5]} gl={{ antialias: true, alpha: true }}>
        <Suspense fallback={null}>
          <CyberOrb scanStatus={scanStatus} />
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
    <div className="h-16 w-16 overflow-hidden rounded-full border border-cyan-500/30">
      <Canvas camera={{ position: [0, 0, 3], fov: 50 }}>
        <Suspense fallback={null}>
          <CyberOrb scanStatus={scanStatus} />
        </Suspense>
      </Canvas>
    </div>
  );
}
