import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import '@fontsource/hind/latin-400.css'
import '@fontsource/hind/latin-500.css'
import '@fontsource/hind/latin-600.css'
import '@fontsource/hind/latin-700.css'
import '@fontsource/hind/devanagari-400.css'
import '@fontsource/hind/devanagari-500.css'
import '@fontsource/hind/devanagari-600.css'
import '@fontsource/hind/devanagari-700.css'
import '@fontsource/azeret-mono/latin-400.css'
import '@fontsource/azeret-mono/latin-500.css'
import './index.css'
import App from './App'
import { I18nProvider } from './i18n'

createRoot(document.getElementById('root')!).render(
  <StrictMode><BrowserRouter><I18nProvider><App /></I18nProvider></BrowserRouter></StrictMode>,
)
