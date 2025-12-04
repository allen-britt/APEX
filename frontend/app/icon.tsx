import { ImageResponse } from "next/og";

const width = 32;
const height = 32;

export const size = { width, height };
export const contentType = "image/svg+xml";

export default function Icon() {
  return new ImageResponse(
    (
      <svg
        width={width}
        height={height}
        viewBox="0 0 32 32"
        xmlns="http://www.w3.org/2000/svg"
      >
        <defs>
          <linearGradient id="apex-icon-gradient" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#00F5FF" />
            <stop offset="50%" stopColor="#00E4A8" />
            <stop offset="100%" stopColor="#00B39F" />
          </linearGradient>
        </defs>
        <rect width="32" height="32" rx="8" fill="#050C16" />
        <path
          d="M16 6l8 20h-4l-1.6-4h-4.8L12 26H8l8-20zm0 5.6l-1.76 4.8h3.52L16 11.6z"
          fill="url(#apex-icon-gradient)"
        />
      </svg>
    ),
    {
      width,
      height,
    },
  );
}
