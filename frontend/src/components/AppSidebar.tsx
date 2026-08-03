"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useRef, useState } from "react";

export function AppSidebar() {
  const pathname = usePathname();
  const [isOpen, setIsOpen] = useState(false);
  const [isCollapsed, setIsCollapsed] = useState(false);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const workspaceActive = pathname === "/";
  const libraryActive = pathname === "/library" || pathname.startsWith("/campaigns/");

  useEffect(() => {
    if (!isOpen) {
      return;
    }

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        setIsOpen(false);
        triggerRef.current?.focus();
      }
    }

    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [isOpen]);

  useEffect(() => {
    setIsOpen(false);
  }, [pathname]);

  function closeSidebar() {
    setIsOpen(false);
    if (window.matchMedia("(max-width: 767px)").matches) {
      triggerRef.current?.focus();
    }
  }

  return (
    <>
      <button
        ref={triggerRef}
        className="sidebar-toggle"
        type="button"
        aria-expanded={isOpen}
        aria-controls="app-sidebar"
        onClick={() => setIsOpen((current) => !current)}
      >
        Menu
      </button>
      <aside
        id="app-sidebar"
        className={`app-sidebar${isOpen ? " is-open" : ""}${isCollapsed ? " is-collapsed" : ""}`}
      >
        <nav className="sidebar-nav" aria-label="Primary navigation">
          <Link
            className="sidebar-link"
            href="/"
            title="Workspace"
            aria-current={workspaceActive ? "page" : undefined}
            onClick={closeSidebar}
          >
            <WorkspaceIcon />
            <span className="sidebar-link-label">Workspace</span>
          </Link>
          <Link
            className="sidebar-link"
            href="/library"
            title="Library"
            aria-current={libraryActive ? "page" : undefined}
            onClick={closeSidebar}
          >
            <LibraryIcon />
            <span className="sidebar-link-label">Library</span>
          </Link>
        </nav>
        <button
          className="sidebar-collapse"
          type="button"
          aria-expanded={!isCollapsed}
          aria-label={isCollapsed ? "Expand sidebar" : "Collapse sidebar"}
          onClick={() => setIsCollapsed((current) => !current)}
        >
          <span className="sidebar-collapse-icon" aria-hidden="true">{isCollapsed ? "→" : "←"}</span>
          <span className="sidebar-collapse-label">{isCollapsed ? "Expand" : "Collapse"}</span>
        </button>
      </aside>
      {isOpen && (
        <button
          className="sidebar-backdrop"
          type="button"
          aria-label="Close navigation"
          onClick={closeSidebar}
        />
      )}
    </>
  );
}

function WorkspaceIcon() {
  return (
    <svg className="sidebar-link-icon" viewBox="0 0 16 16" aria-hidden="true" focusable="false">
      <rect x="2" y="2" width="5" height="5" rx="1" />
      <rect x="9" y="2" width="5" height="5" rx="1" />
      <rect x="2" y="9" width="5" height="5" rx="1" />
      <rect x="9" y="9" width="5" height="5" rx="1" />
    </svg>
  );
}

function LibraryIcon() {
  return (
    <svg className="sidebar-link-icon" viewBox="0 0 16 16" aria-hidden="true" focusable="false">
      <path d="M3 3.5h10M3 7.5h10M3 11.5h10" />
      <path d="M2.5 2.5v11M13.5 2.5v11" />
    </svg>
  );
}
