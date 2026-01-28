"use client";

import Image from "next/image";
import { Building2 } from "lucide-react";
import { config } from "@/lib/config";
import { cn } from "@/lib/utils";

interface BrandLogoProps {
  className?: string;
  size?: "sm" | "md" | "lg" | "xl";
  showText?: boolean;
}

const sizeConfig = {
  sm: { icon: "h-6 w-6", image: 24, text: "text-sm" },
  md: { icon: "h-8 w-8", image: 32, text: "text-base" },
  lg: { icon: "h-10 w-10", image: 40, text: "text-lg" },
  xl: { icon: "h-12 w-12", image: 48, text: "text-xl" },
};

export function BrandLogo({ className, size = "md", showText = false }: BrandLogoProps) {
  const { icon, image, text } = sizeConfig[size];

  return (
    <div className={cn("flex items-center gap-2", className)}>
      {config.logoUrl ? (
        <Image
          src={config.logoUrl}
          alt={config.logoAlt || config.appName}
          width={image}
          height={image}
          className="object-contain"
        />
      ) : (
        <div className={cn("flex items-center justify-center rounded-lg bg-gradient-to-br from-blue-600 to-indigo-600 text-white", icon)}>
          <Building2 className="h-1/2 w-1/2" />
        </div>
      )}
      {showText && (
        <span className={cn("font-semibold", text)}>{config.appName}</span>
      )}
    </div>
  );
}

// Agent-specific logo component
interface AgentLogoProps {
  logoUrl?: string;
  name: string;
  domain: string;
  className?: string;
  size?: "sm" | "md" | "lg";
}

const domainGradients: Record<string, string> = {
  Router: "from-purple-500 to-indigo-600",
  Strategy: "from-blue-500 to-cyan-500",
  Legislative: "from-amber-500 to-orange-500",
  Utilities: "from-cyan-500 to-blue-500",
  Communications: "from-pink-500 to-rose-500",
  PublicHealth: "from-green-500 to-emerald-500",
  Building: "from-orange-500 to-red-500",
  PublicSafety: "from-red-500 to-rose-600",
  ParksRec: "from-emerald-500 to-green-600",
  HR: "from-violet-500 to-purple-500",
  Finance: "from-teal-500 to-cyan-500",
  "311": "from-yellow-500 to-amber-500",
  General: "from-slate-500 to-zinc-500",
};

export function AgentLogo({ logoUrl, name, domain, className, size = "md" }: AgentLogoProps) {
  const { icon, image } = sizeConfig[size];
  const gradient = domainGradients[domain] || domainGradients.General;

  if (logoUrl) {
    return (
      <Image
        src={logoUrl}
        alt={name}
        width={image}
        height={image}
        className={cn("rounded-lg object-contain", className)}
      />
    );
  }

  // Generate initials from name
  const initials = name
    .split(" ")
    .map((word) => word[0])
    .slice(0, 2)
    .join("")
    .toUpperCase();

  return (
    <div
      className={cn(
        "flex items-center justify-center rounded-lg bg-gradient-to-br text-white font-semibold",
        gradient,
        icon,
        className
      )}
    >
      <span className="text-xs">{initials}</span>
    </div>
  );
}
