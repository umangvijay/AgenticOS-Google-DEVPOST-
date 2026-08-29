"use client";
import React, { useEffect, useRef, useState } from "react";

export function DiagramScaler({ children }: { children: React.ReactNode }) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [scale, setScale] = useState(1);
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
    const updateScale = () => {
      if (containerRef.current) {
        // The container width relative to the fixed 1000px diagram
        const width = containerRef.current.clientWidth;
        // Don't scale up beyond 1.0 (100%)
        setScale(Math.min(1, width / 1000));
      }
    };
    
    updateScale();
    window.addEventListener("resize", updateScale);
    return () => window.removeEventListener("resize", updateScale);
  }, []);

  return (
    <div 
      ref={containerRef} 
      style={{
        width: "100%",
        maxWidth: 1000,
        margin: "0 auto",
        overflow: "hidden",
        position: "relative",
        // Only set dynamic height if mounted, otherwise use a fallback 450px
        height: mounted ? 450 * scale : 450,
      }}
    >
      <div 
        style={{
          width: 1000,
          height: 450,
          transformOrigin: "top left",
          position: "absolute",
          top: 0,
          left: 0,
          // Only scale if mounted
          transform: `scale(${mounted ? scale : 1})`,
        }}
      >
        {children}
      </div>
    </div>
  );
}
