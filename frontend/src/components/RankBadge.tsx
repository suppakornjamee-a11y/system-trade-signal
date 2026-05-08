"use client";

export default function RankBadge({ rank, size = "md" }: { rank: number; size?: "sm" | "md" }) {
  const cfg: Record<number, { bg: string; text: string; label: string }> = {
    1: { bg: "bg-neutral/20", text: "text-neutral", label: "1" },
    2: { bg: "bg-blue-900/40", text: "text-blue-400", label: "2" },
    3: { bg: "bg-yellow-900/40", text: "text-yellow-400", label: "3" },
    4: { bg: "bg-orange-900/40", text: "text-orange-400", label: "4" },
    5: { bg: "bg-red-900/40", text: "text-red-400", label: "5" },
  };
  const { bg, text, label } = cfg[rank] ?? cfg[1];
  const sizeClass = size === "sm" ? "w-4 h-4 text-[9px]" : "w-6 h-6 text-xs";

  return (
    <span className={`inline-flex items-center justify-center rounded-full font-bold shrink-0 ${sizeClass} ${bg} ${text}`}>
      {label}
    </span>
  );
}
