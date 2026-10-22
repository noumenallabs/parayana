/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: "class",
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        mandapa: {
          950: "#090A0F",
          900: "#0F1117",
          850: "#161822",
          800: "#1E2230",
          700: "#2B3044",
          600: "#3D4460",
          gold: "#FFB300",
          amber: "#FF8F00",
          copper: "#D84315",
          sand: "#E0D7C6",
        },
      },
    },
  },
  plugins: [],
};
