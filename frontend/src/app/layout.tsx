import type { Metadata } from 'next';
import { Inter, Poppins } from 'next/font/google';

import { Providers } from './providers';
import './globals.css';

/**
 * The reference pulls Poppins and Inter from the Google Fonts CDN at runtime.
 * next/font self-hosts them at build time instead, which removes a
 * render-blocking request to a third party and the layout shift that comes
 * with it. The CSS variables are consumed by --font-sans and --font-display.
 */
const inter = Inter({
  subsets: ['latin'],
  weight: ['400', '500', '600', '700'],
  variable: '--font-inter',
  display: 'swap',
});

const poppins = Poppins({
  subsets: ['latin'],
  weight: ['500', '600', '700'],
  variable: '--font-poppins',
  display: 'swap',
});

export const metadata: Metadata = {
  title: 'ReefCommand',
  description:
    'Decision support that turns environmental monitoring, field observations, scientific ' +
    'intervention guidance, and limited conservation resources into continuously updated ' +
    'reef-response plans.',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${inter.variable} ${poppins.variable}`}>
      <body>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
