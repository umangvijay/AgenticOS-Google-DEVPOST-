"use client";

import React, { useRef, useState } from "react";

export default function TiltCard({ children, className, style }: any) {
  const cardRef = useRef<HTMLDivElement>(null);
  const rectRef = useRef<DOMRect | null>(null);
  const [isHovered, setIsHovered] = useState(false);
  const [tilt, setTilt] = useState("");

  const handleMouseMove = (e: React.MouseEvent<HTMLDivElement>) => {
    if (!cardRef.current || !rectRef.current) return;
    const rect = rectRef.current;
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    
    const centerX = rect.width / 2;
    const centerY = rect.height / 2;
    
    // Subtler 5-degree tilt for a smoother, less aggressive feel
    const rotateX = ((y - centerY) / centerY) * -5;
    const rotateY = ((x - centerX) / centerX) * 5;
    
    setTilt(`rotateX(${rotateX}deg) rotateY(${rotateY}deg)`);
  };

  const handleMouseEnter = () => {
    if (cardRef.current) {
      rectRef.current = cardRef.current.getBoundingClientRect();
    }
    setIsHovered(true);
  };
  const handleMouseLeave = () => {
    setIsHovered(false);
    setTilt("");
  };

  const baseTransform = style?.transform || "";
  const innerStyle = { ...style };
  delete innerStyle.transform;

  return (
    <div 
      style={{
        transform: isHovered ? `${baseTransform} translateY(-12px)` : baseTransform,
        transition: "transform 0.5s cubic-bezier(0.4, 0, 0.2, 1)",
        perspective: "1200px",
        zIndex: isHovered ? 10 : style?.zIndex,
        height: "100%"
      }}
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
      onMouseMove={handleMouseMove}
    >
      <div 
        ref={cardRef}
        className={className}
        style={{
          ...innerStyle,
          transform: isHovered ? tilt : "rotateX(0deg) rotateY(0deg)",
          transition: isHovered 
            ? "transform 0.1s cubic-bezier(0.2, 0.8, 0.2, 1), box-shadow 0.5s cubic-bezier(0.4, 0, 0.2, 1), border-color 0.5s" 
            : "all 0.5s cubic-bezier(0.4, 0, 0.2, 1)",
          boxShadow: isHovered ? "0 25px 50px rgba(236, 72, 153, 0.25)" : style?.boxShadow,
          height: "100%",
          margin: 0
        }}
      >
        {children}
      </div>
    </div>
  );
}
