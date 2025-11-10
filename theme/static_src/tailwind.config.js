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
          "primary": "#7B61FF",   // Mapea a tu 'primary-custom'
          "secondary": "#5AB2E6", // Mapea a tu 'secondary-custom'
          "accent": "#875AE6",    // Mapea a tu 'accent-custom'
          "base-100": "#FFFFFF",  // Color base del contenido (tu 'secondary-bg')
          "base-200": "#F6F6F6",  // Color base más oscuro (tu 'principal-bg')
          // Puedes continuar mapeando otros colores si es necesario
        },
      },
    ],
  }
}