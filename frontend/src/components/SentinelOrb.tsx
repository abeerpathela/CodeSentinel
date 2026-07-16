import { Suspense, useMemo, useRef } from "react";
import { Canvas, useFrame } from "@react-three/fiber";
import { Float, MeshDistortMaterial, Sphere } from "@react-three/drei";
import * as THREE from "three";
import type { ThreatLevel } from "../contexts/ScanContext";

interface Props {
  threatLevel?: ThreatLevel;
  className?: string;
  compact?: boolean;
}

const PALETTE: Record<
  ThreatLevel,
  { color: string; emissive: string; speed: number; pulse: number; label: string; emoji: string }
> = {
  idle: { color: "#22c55e", emissive: "#16a34a", speed: 0.3, pulse: 0.03, label: "Standby", emoji: "🟢" },
  cloning: { color: "#eab308", emissive: "#ca8a04", speed: 1.1, pulse: 0.14, label: "Cloning", emoji: "🟡" },
  scanning: { color: "#f97316", emissive: "#ea580c", speed: 1.4, pulse: 0.16, label: "Scanning", emoji: "🟠" },
  threat: { color: "#ef4444", emissive: "#dc2626", speed: 2.4, pulse: 0.24, label: "Critical", emoji: "🔴" },
};

function CyberOrb({ threatLevel }: { threatLevel: ThreatLevel }) {
  const meshRef = useRef<THREE.Mesh>(null);
  const wireRef = useRef<THREE.Mesh>(null);
  const cfg = PALETTE[threatLevel];

  useFrame((state) => {
    const t = state.clock.elapsedTime;
    const pulse = 1 + Math.sin(t * cfg.speed * 3) * cfg.pulse;
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
    <Float speed={cfg.speed} rotationIntensity={0.4} floatIntensity={0.6}>
      <group>
        <Sphere ref={meshRef} args={[1, 64, 64]}>
          <MeshDistortMaterial
            color={cfg.color}
            emissive={cfg.emissive}
            emissiveIntensity={threatLevel === "threat" ? 1.3 : 0.65}
            distort={threatLevel === "threat" ? 0.5 : 0.28}
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
        <pointLight color={cfg.emissive} intensity={threatLevel === "threat" ? 3.2 : 1.8} distance={8} />
        <ambientLight intensity={0.15} />
      </group>
    </Float>
  );
}

export default function SentinelOrb({ threatLevel = "idle", className = "", compact = false }: Props) {
  const height = compact ? "h-48" : "h-[420px]";
  const camera = useMemo(
    () => ({ position: [0, 0, compact ? 4 : 3.2] as [number, number, number], fov: 45 }),
    [compact]
  );
  const cfg = PALETTE[threatLevel];

  return (
    <div className={`relative overflow-hidden rounded-2xl ${height} ${className}`}>
      <div className="pointer-events-none absolute inset-0 bg-gradient-to-b from-cyan-500/5 via-transparent to-red-500/5" />
      <Canvas camera={camera} dpr={[1, 1.5]} gl={{ antialias: true, alpha: true }}>
        <Suspense fallback={null}>
          <CyberOrb threatLevel={threatLevel} />
        </Suspense>
      </Canvas>
      <div className="pointer-events-none absolute bottom-3 left-0 right-0 text-center font-mono text-[10px] uppercase tracking-[0.3em] text-cyber-muted">
        {cfg.emoji} {cfg.label}
      </div>
    </div>
  );
}

export function MiniOrbCanvas({ threatLevel = "idle" }: { threatLevel?: ThreatLevel }) {
  return (
    <div className="h-16 w-16 overflow-hidden rounded-full border border-cyan-500/30">
      <Canvas camera={{ position: [0, 0, 3], fov: 50 }}>
        <Suspense fallback={null}>
          <CyberOrb threatLevel={threatLevel} />
        </Suspense>
      </Canvas>
    </div>
  );
}
