import { Suspense, useMemo, useRef } from "react";
import { Canvas, useFrame } from "@react-three/fiber";
import { Float, Points, PointMaterial } from "@react-three/drei";
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
  idle: { color: "#00ff41", emissive: "#00cc33", speed: 0.35, pulse: 0.04, label: "Point-Cloud Standby" },
  scanning: { color: "#ffffff", emissive: "#cccccc", speed: 1.2, pulse: 0.14, label: "Mesh Acquisition" },
  verifying: { color: "#ff4b2b", emissive: "#cc3a22", speed: 2.0, pulse: 0.2, label: "Autopsy Verify" },
  breach: { color: "#ff4b2b", emissive: "#ff2200", speed: 3.5, pulse: 0.35, label: "Threat Detected" },
  secure: { color: "#00ff41", emissive: "#00aa33", speed: 0.2, pulse: 0.02, label: "Perimeter Secure" },
};

function PointCloudOrb({ scanStatus }: { scanStatus: ScanStatusMode }) {
  const groupRef = useRef<THREE.Group>(null);
  const wireRef = useRef<THREE.Mesh>(null);
  const cfg = PALETTE[scanStatus];
  const chaotic = scanStatus === "breach";

  const positions = useMemo(() => {
    const count = 420;
    const arr = new Float32Array(count * 3);
    for (let i = 0; i < count; i += 1) {
      const r = 1 + Math.random() * 0.35;
      const theta = Math.random() * Math.PI * 2;
      const phi = Math.acos(2 * Math.random() - 1);
      arr[i * 3] = r * Math.sin(phi) * Math.cos(theta);
      arr[i * 3 + 1] = r * Math.sin(phi) * Math.sin(theta);
      arr[i * 3 + 2] = r * Math.cos(phi);
    }
    return arr;
  }, []);

  useFrame((state) => {
    const t = state.clock.elapsedTime;
    const flicker = chaotic ? Math.sin(t * 18) * 0.08 : 0;
    const pulse = 1 + Math.sin(t * cfg.speed * 3) * cfg.pulse + flicker;
    if (groupRef.current) {
      groupRef.current.rotation.y = t * cfg.speed * 0.35;
      groupRef.current.rotation.x = Math.sin(t * 0.25) * 0.15;
      groupRef.current.scale.setScalar(pulse);
    }
    if (wireRef.current) {
      wireRef.current.rotation.z = -t * cfg.speed * 0.45;
    }
  });

  return (
    <Float speed={cfg.speed} rotationIntensity={chaotic ? 0.85 : 0.3} floatIntensity={0.4}>
      <group ref={groupRef}>
        <Points positions={positions} stride={3} frustumCulled={false}>
          <PointMaterial
            transparent
            color={cfg.color}
            size={0.035}
            sizeAttenuation
            depthWrite={false}
            opacity={0.92}
          />
        </Points>
        <mesh ref={wireRef}>
          <icosahedronGeometry args={[1.25, 2]} />
          <meshBasicMaterial color={cfg.emissive} wireframe transparent opacity={0.22} />
        </mesh>
        <pointLight color={cfg.emissive} intensity={chaotic ? 2.8 : 1.4} distance={8} />
        <ambientLight intensity={0.08} />
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
      <div className="pointer-events-none absolute inset-0 bg-gradient-to-b from-[#00ff41]/5 via-transparent to-[#ff4b2b]/5" />
      <Canvas camera={camera} dpr={[1, 1.5]} gl={{ antialias: true, alpha: true }}>
        <Suspense fallback={null}>
          <PointCloudOrb scanStatus={scanStatus} />
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
    <div className="h-16 w-16 overflow-hidden rounded-full border border-[#00ff41]/30 bg-black/50">
      <Canvas camera={{ position: [0, 0, 3], fov: 50 }}>
        <Suspense fallback={null}>
          <PointCloudOrb scanStatus={scanStatus} />
        </Suspense>
      </Canvas>
    </div>
  );
}
