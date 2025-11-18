/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    '../templates/**/*.html',
    '../../templates/**/*.html',
    '../../**/templates/**/*.html',
    '../../**/*.js',
    '!../../**/node_modules'
  ],
  theme: {
    extend: {
      colors: {
        'primary-custom': '#7B61FF', 
        'secondary-custom': '#5AB2E6',
        'accent-custom': '#875AE6', 
        'principal-font': '#5B5B5B',
        'secondary-font': '#000000',
        'principal-bg': '#F6F6F6',
        'secondary-bg': '#FFFFFF'
      }
    }
  },
  plugins: [
    require('daisyui'),
  ],
  // Aquí integramos los colores con DaisyUI
  daisyui: {
    themes: [
      {
        light: {
          // Sobrescribimos los colores del tema 'light' de DaisyUI
          ...require("daisyui/src/theming/themes")["light"], // Mantenemos el resto del tema light
          // Mapeo de tus colores personalizados a las variables de DaisyUI
          "primary": "#7B61FF",            // primary-custom
          "primary-focus": "#6F4EF0",      // variante de foco (ligeramente más oscuro)
          "primary-content": "#FFFFFF",    // color del texto sobre primary

          "secondary": "#5AB2E6",          // secondary-custom
          "secondary-focus": "#4AA6DB",
          "secondary-content": "#FFFFFF",

          "accent": "#875AE6",             // accent-custom
          "accent-focus": "#7447D4",
          "accent-content": "#FFFFFF",

          // Colores neutrales / tipográficos derivados
          "neutral": "#5B5B5B",            // principal-font
          "neutral-focus": "#4A4A4A",
          "neutral-content": "#FFFFFF",

          // Fondos/base
          "base-100": "#FFFFFF",           // secondary-bg
          "base-200": "#F6F6F6",           // principal-bg
          "base-300": "#EDEDED",
          "base-content": "#000000",       // secondary-font (texto sobre base)
          // Puedes continuar mapeando otros colores si es necesario
        },
      },
    ],
  }
}