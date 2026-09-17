import { createPortal } from 'react-dom';
import { useEffect, useState } from 'react';
import { Outlet } from 'react-router-dom';
import Sidebar from './Sidebar';
import Header from './Header';
import OfflineSyncBadge from './OfflineSyncBadge';

export default function Layout() {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const closeMobile = () => setMobileMenuOpen(false);
  const toggleMobile = () => setMobileMenuOpen((v) => !v);

  useEffect(() => {
    if (!mobileMenuOpen) return undefined;
    const prev = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => {
      document.body.style.overflow = prev;
    };
  }, [mobileMenuOpen]);

  return (
    <div className="app-shell flex">
      {mobileMenuOpen &&
        createPortal(
          <div
            className="fixed inset-0 z-40 bg-encre/60 backdrop-blur-sm lg:hidden"
            onClick={closeMobile}
            aria-hidden="true"
          />,
          document.body
        )}
      <Sidebar
        collapsed={sidebarCollapsed}
        mobileOpen={mobileMenuOpen}
        onCloseMobile={closeMobile}
      />
      <div className="flex min-w-0 flex-1 flex-col">
        <Header
          mobileMenuOpen={mobileMenuOpen}
          onMenuClick={toggleMobile}
          sidebarCollapsed={sidebarCollapsed}
          onToggleSidebar={() => setSidebarCollapsed((v) => !v)}
        />
        <div className="flex justify-end px-4 pt-2 sm:px-6 lg:px-8">
          <OfflineSyncBadge />
        </div>
        <main
          className={`flex-1 p-4 sm:p-6 lg:p-8 ${mobileMenuOpen ? 'overflow-hidden' : 'overflow-auto'}`}
        >
          <div className="mx-auto max-w-[1440px] animate-fade-in">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  );
}
