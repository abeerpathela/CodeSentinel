import ScanLineOverlay from "./components/ScanLineOverlay";
import SplashScreen from "./components/SplashScreen";
import Toast from "./components/Toast";
import { ScanProvider, useScan } from "./contexts/ScanContext";
import MainShell from "./layout/MainShell";
import LandingPage from "./pages/LandingPage";

function AppRouter() {
  const { phase, setPhase, scanning, toast, setToast } = useScan();

  return (
    <>
      <ScanLineOverlay active={scanning} />
      {phase === "splash" && <SplashScreen onComplete={() => setPhase("landing")} />}
      {phase === "landing" && <LandingPage />}
      {phase === "command" && <MainShell />}
      <Toast
        message={toast?.message || ""}
        visible={!!toast}
        variant={toast?.variant || "info"}
        onDismiss={() => setToast(null)}
      />
    </>
  );
}

export default function App() {
  return (
    <ScanProvider>
      <AppRouter />
    </ScanProvider>
  );
}
