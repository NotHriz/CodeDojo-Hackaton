// ENTRY: loads fonts and CSS, installs the router, mounts the app.
import { createApp } from 'vue'
import '@fontsource/atkinson-hyperlegible/400.css' // font designed for low-vision readers
import '@fontsource/atkinson-hyperlegible/700.css'
import '@fontsource/comfortaa/700.css' // rounded display font used for big titles
import 'leaflet/dist/leaflet.css'
import './style.css'
import App from './App.vue'
import router from './router.js'

createApp(App).use(router).mount('#app')
