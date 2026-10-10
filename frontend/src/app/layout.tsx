import './globals.css'
import React from 'react'
import { CityProvider } from '@/context/CityContext'
import { AuthProvider } from '@/context/AuthContext'
import Sidebar from '@/components/Sidebar'
import EntrySplash from '@/components/EntrySplash'
import ThemeToggle from '@/components/ThemeToggle'

export const metadata = {
  title: 'Aervia — Urban Air Quality Intelligence & Forecasting',
  description: 'Intelligent decision layer for urban air quality monitoring, atmospheric physics, and forecasting.',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="" />
        <script
          dangerouslySetInnerHTML={{
            __html: `
              try {
                localStorage.removeItem('aervia_theme_legacy');
                document.documentElement.setAttribute('data-theme', 'light');
              } catch (e) {}
            `,
          }}
        />
      </head>
      <body suppressHydrationWarning>
        <AuthProvider>
          <CityProvider>
            <EntrySplash />
            <div className="global-top-right-controls">
              <ThemeToggle />
            </div>
            <div className="app-layout">
              <Sidebar />
              <main className="main-content">{children}</main>
            </div>
          </CityProvider>
        </AuthProvider>
      </body>
    </html>
  )
}
