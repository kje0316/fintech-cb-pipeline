'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';

export default function Navigation() {
  const pathname = usePathname();

  const navItems = [
    { href: '/', label: '메인 페이지' },
    { href: '/upload', label: '기업 리포트' },
    { href: '/partners', label: '협력사' },
  ];

  return (
    <nav className="flex gap-6">
      {navItems.map((item) => (
        <Link
          key={item.href}
          href={item.href}
          className={`text-white hover:text-gray-300 transition-colors ${
            pathname === item.href ? 'font-bold border-b-2 border-white' : ''
          }`}
        >
          {item.label}
        </Link>
      ))}
    </nav>
  );
}
