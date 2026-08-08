import { createPortal } from 'react-dom';
import { useState } from 'react';
import { Outlet } from 'react-router-dom';
import Sidebar from './Sidebar';
import Header from './Header';

export default function Layout() {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const closeMobile = () => setMobileMenuOpen(false);

  return (
    <div className="flex min-h-screen bg-craie">
      {mobileMenuOpen &&
        createPortal(
          <div
            className="fixed inset-0 z-40 bg-encre/50 lg:hidden"
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
      <div className="flex flex-1 flex-col lg:min-w-0">
        <Header
          onMenuClick={() => setMobileMenuOpen(true)}
          sidebarCollapsed={sidebarCollapsed}
          onToggleSidebar={() => setSidebarCollapsed((v) => !v)}
        />
        <main className="flex-1 overflow-auto p-4 lg:p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
