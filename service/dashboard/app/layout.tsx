import type { Metadata } from 'next';
import './globals.css';
import Navigation from '@/components/Navigation';

export const metadata: Metadata = {
  title: 'Fintech Dashboard - 중소기업 재무 건전성 분석',
  description: '중소기업 신용평가 및 부도 위험 분석 대시보드',
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="ko">
      <body>
        <header className="text-white shadow-md" style={{ backgroundColor: '#2D3748' }}>
          <div className="container mx-auto px-4 py-4">
            <div className="flex items-center justify-between">
              <h1 className="text-2xl font-bold">대시보드</h1>
              <div className="absolute left-1/2 transform -translate-x-1/2">
                <Navigation />
              </div>
            </div>
          </div>
        </header>
        <main className="container mx-auto px-4 py-6">
          {children}
        </main>
        <footer className="bg-gray-100 mt-12">
          <div className="container mx-auto px-4 py-4 text-center text-sm text-gray-600">
            © 2024 Fintech CB Pipeline. All rights reserved.
          </div>
        </footer>
      </body>
    </html>
  );
}
