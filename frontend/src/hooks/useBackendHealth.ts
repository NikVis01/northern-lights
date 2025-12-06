import { useState, useEffect } from "react";
import { getBackendUrl } from "@/lib/api";

export const useBackendHealth = () => {
  const [isHealthy, setIsHealthy] = useState<boolean>(true);
  const [isChecking, setIsChecking] = useState<boolean>(false);
  const [lastChecked, setLastChecked] = useState<Date | null>(null);

  const checkHealth = async () => {
    try {
      setIsChecking(true);
      const response = await fetch(getBackendUrl("/health"), {
        method: "GET",
        signal: AbortSignal.timeout(5000), // 5 second timeout
      });
      
      if (response.ok) {
        const data = await response.json();
        setIsHealthy(data.status === "ok");
        setLastChecked(new Date());
      } else {
        setIsHealthy(false);
      }
    } catch (error) {
      console.error("Health check failed:", error);
      setIsHealthy(false);
    } finally {
      setIsChecking(false);
    }
  };

  useEffect(() => {
    // Initial check
    checkHealth();

    // Poll every 10 seconds
    const interval = setInterval(checkHealth, 10000);

    return () => clearInterval(interval);
  }, []);

  return { isHealthy, isChecking, checkHealth, lastChecked };
};
