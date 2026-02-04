interface MoboxLogoProps {
  className?: string;
  size?: number;
}

export function MoboxLogo({ className, size = 48 }: MoboxLogoProps) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 100 100"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
    >
      {/* Package/Box - main outline */}
      <rect
        x="20"
        y="25"
        width="60"
        height="50"
        rx="6"
        stroke="currentColor"
        strokeWidth="3"
        fill="none"
      />

      {/* Package tape - center cross */}
      <line
        x1="50"
        y1="25"
        x2="50"
        y2="75"
        stroke="currentColor"
        strokeWidth="2.5"
        opacity="0.4"
      />
      <line
        x1="20"
        y1="50"
        x2="80"
        y2="50"
        stroke="currentColor"
        strokeWidth="2.5"
        opacity="0.4"
      />

      {/* Robot - simplified face - black for visibility */}
      <circle cx="50" cy="50" r="12" fill="#1a1a1a" />

      {/* Antenna */}
      <line
        x1="50"
        y1="38"
        x2="50"
        y2="32"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
      />
      <circle cx="50" cy="30" r="2" fill="currentColor" />

      {/* Eyes - white on black face */}
      <circle cx="45" cy="48" r="2" fill="white" />
      <circle cx="55" cy="48" r="2" fill="white" />

      {/* Smile - white on black face */}
      <path
        d="M 45 54 Q 50 56 55 54"
        stroke="white"
        strokeWidth="2"
        fill="none"
        strokeLinecap="round"
      />
    </svg>
  );
}
