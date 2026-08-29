"use client";
import { useState, useEffect } from "react";
import { throttle } from "radash";

export function useNetworkStatus() {
  const [isLowEnd, setIsLowEnd] = useState(false);

  useEffect(() => {
    // Throttle the check so it doesn't run continuously and save main thread time on low-end devices
    const checkNetwork = throttle({ interval: 2000 }, () => {
      // @ts-ignore - navigator.connection is not fully typed in standard TS yet
      const connection = navigator.connection || navigator.mozConnection || navigator.webkitConnection;
      
      if (connection) {
        const isSaveData = connection.saveData === true;
        const isSlow = ["slow-2g", "2g", "3g"].includes(connection.effectiveType);
        
        if (isSaveData || isSlow) {
          setIsLowEnd(true);
          // Add global class to disable heavy CSS animations (mesh gradients, blurs, etc)
          document.documentElement.classList.add("reduce-data");
        } else {
          setIsLowEnd(false);
          document.documentElement.classList.remove("reduce-data");
        }
      }
    });

    checkNetwork();
    
    // @ts-ignore
    const connection = navigator.connection || navigator.mozConnection || navigator.webkitConnection;
    if (connection) {
      connection.addEventListener("change", checkNetwork);
      return () => connection.removeEventListener("change", checkNetwork);
    }
  }, []);

  return { isLowEnd };
}
