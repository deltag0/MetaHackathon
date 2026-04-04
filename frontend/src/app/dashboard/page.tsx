"use client";

import { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/context/auth-context";
import {
  shortenUrl,
  getLinks,
  updateLink,
  deleteLink,
  type Link,
} from "@/lib/api";

export default function DashboardPage() {
  const { user, isAuthenticated, isLoading, logout } = useAuth();
  const router = useRouter();

  const [url, setUrl] = useState("");
  const [title, setTitle] = useState("");
  const [shortenLoading, setShortenLoading] = useState(false);
  const [shortenResult, setShortenResult] = useState<Link | null>(null);
  const [shortenError, setShortenError] = useState("");
  const [copied, setCopied] = useState<string | null>(null);

  const [links, setLinks] = useState<Link[]>([]);
  const [linksLoading, setLinksLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const perPage = 10;

  const [editLink, setEditLink] = useState<Link | null>(null);
  const [editUrl, setEditUrl] = useState("");
  const [editTitle, setEditTitle] = useState("");
  const [editLoading, setEditLoading] = useState(false);
  const [editError, setEditError] = useState("");

  const [deleteCode, setDeleteCode] = useState<string | null>(null);
  const [deleteLoading, setDeleteLoading] = useState(false);

  useEffect(() => {
    if (!isLoading && !isAuthenticated) router.push("/login");
  }, [isLoading, isAuthenticated, router]);

  const fetchLinks = useCallback(async () => {
    setLinksLoading(true);
    try {
      const data = await getLinks(page, perPage);
      setLinks(data.links);
      setTotal(data.total);
    } catch { /* API not available */ }
    finally { setLinksLoading(false); }
  }, [page]);

  useEffect(() => {
    if (isAuthenticated) fetchLinks();
  }, [isAuthenticated, fetchLinks]);

  const handleShorten = async (e: React.FormEvent) => {
    e.preventDefault();
    setShortenError("");
    setShortenResult(null);
    setShortenLoading(true);
    try {
      const result = await shortenUrl(url, title || undefined);
      setShortenResult(result);
      setUrl("");
      setTitle("");
      fetchLinks();
    } catch (err) {
      setShortenError(err instanceof Error ? err.message : "Failed to shorten URL");
    } finally {
      setShortenLoading(false);
    }
  };

  const handleCopy = async (text: string) => {
    await navigator.clipboard.writeText(text);
    setCopied(text);
    setTimeout(() => setCopied(null), 2000);
  };

  const openEdit = (link: Link) => {
    setEditLink(link);
    setEditUrl(link.original_url);
    setEditTitle(link.title || "");
    setEditError("");
  };

  const handleEdit = async () => {
    if (!editLink) return;
    setEditLoading(true);
    setEditError("");
    try {
      await updateLink(editLink.short_code, editUrl, editTitle || undefined);
      setEditLink(null);
      fetchLinks();
    } catch (err) {
      setEditError(err instanceof Error ? err.message : "Failed to update");
    } finally {
      setEditLoading(false);
    }
  };

  const handleDelete = async () => {
    if (!deleteCode) return;
    setDeleteLoading(true);
    try {
      await deleteLink(deleteCode);
      setDeleteCode(null);
      fetchLinks();
    } catch { /* silent */ }
    finally { setDeleteLoading(false); }
  };

  const totalPages = Math.ceil(total / perPage);
  const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:5000";

  const timeAgo = (dateStr: string) => {
    const diff = Date.now() - new Date(dateStr).getTime();
    const mins = Math.floor(diff / 60000);
    if (mins < 1) return "just now";
    if (mins < 60) return `${mins}m ago`;
    const hrs = Math.floor(mins / 60);
    if (hrs < 24) return `${hrs}h ago`;
    const days = Math.floor(hrs / 24);
    if (days < 30) return `${days}d ago`;
    return new Date(dateStr).toLocaleDateString();
  };

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[#1a1a2e]">
        <div className="w-6 h-6 border-2 border-[#22d3ee]/20 border-t-[#22d3ee] rounded-full animate-spin" />
      </div>
    );
  }

  if (!isAuthenticated) return null;

  return (
    <div className="min-h-screen flex flex-col bg-[#1a1a2e] glow-bg">
      {/* Nav */}
      <header className="sticky top-0 z-50 bg-[#1a1a2e]/80 backdrop-blur-lg border-b border-[#2e2e4a]">
        <div className="flex items-center justify-between px-10 py-4">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-[#22d3ee] flex items-center justify-center">
              <svg className="w-5 h-5 text-[#1a1a2e]" fill="none" stroke="currentColor" strokeWidth={2.5} viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" />
              </svg>
            </div>
            <span className="font-[var(--font-outfit)] text-[18px] font-bold text-white tracking-tight">shorten.it</span>
          </div>
          <div className="flex items-center gap-6">
            <span className="text-[14px] text-[#6e6e8a] hidden sm:block">{user?.email}</span>
            <button
              onClick={logout}
              className="text-[14px] text-[#8888a0] hover:text-white transition-colors duration-200"
            >
              Log out
            </button>
          </div>
        </div>
      </header>

      <main className="flex-1 px-10 py-12 relative z-10">
        <div className="stagger">
          {/* Page header */}
          <div className="mb-12">
            <h1 className="font-[var(--font-outfit)] text-[36px] font-extrabold text-white tracking-tight">
              Links
            </h1>
            <p className="text-[16px] text-[#6e6e8a] mt-2">Create and manage your shortened URLs.</p>
          </div>

          {/* Shorten form */}
          <div className="bg-[#232340] border border-[#2e2e4a] rounded-2xl p-8 mb-10">
            <form onSubmit={handleShorten}>
              <div className="flex flex-col lg:flex-row gap-4">
                <input
                  className="flex-1 h-14 bg-[#1a1a2e] border border-[#2e2e4a] rounded-xl px-5 text-[16px] text-white focus:border-[#22d3ee]/50 focus:outline-none transition-all placeholder:text-[#52526e]"
                  placeholder="Paste a long URL..."
                  type="text"
                  value={url}
                  onChange={(e) => setUrl(e.target.value)}
                  required
                />
                <input
                  className="lg:w-56 h-14 bg-[#1a1a2e] border border-[#2e2e4a] rounded-xl px-5 text-[16px] text-white focus:border-[#22d3ee]/50 focus:outline-none transition-all placeholder:text-[#52526e]"
                  placeholder="Title (optional)"
                  type="text"
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                />
                <button
                  type="submit"
                  disabled={shortenLoading}
                  className="btn-press h-14 px-8 bg-[#22d3ee] hover:bg-[#06b6d4] text-[#1a1a2e] text-[16px] font-bold rounded-xl transition-all duration-200 disabled:opacity-50 shrink-0 flex items-center justify-center gap-2.5"
                >
                  {shortenLoading ? (
                    <>
                      <div className="w-5 h-5 border-2 border-[#1a1a2e]/20 border-t-[#1a1a2e] rounded-full animate-spin" />
                      Shortening...
                    </>
                  ) : (
                    <>
                      <svg className="w-5 h-5" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" />
                      </svg>
                      Shorten
                    </>
                  )}
                </button>
              </div>

              {shortenError && (
                <div className="mt-4 text-[14px] text-[#f43f5e]">{shortenError}</div>
              )}

              {shortenResult && (
                <div className="mt-5 flex items-center gap-4 h-14 bg-[#22d3ee]/[0.06] border border-[#22d3ee]/20 rounded-xl px-5">
                  <div className="w-2.5 h-2.5 rounded-full bg-[#22c55e] shrink-0 animate-pulse" />
                  <code className="text-[15px] text-[#22d3ee] font-[var(--font-fira-code)] font-medium truncate">
                    {shortenResult.short_url || `${API_BASE}/${shortenResult.short_code}`}
                  </code>
                  <button
                    type="button"
                    onClick={() => handleCopy(shortenResult.short_url || `${API_BASE}/${shortenResult.short_code}`)}
                    className="ml-auto text-[14px] font-semibold text-[#8888a0] hover:text-white transition-colors shrink-0"
                  >
                    {copied === (shortenResult.short_url || `${API_BASE}/${shortenResult.short_code}`) ? "Copied!" : "Copy"}
                  </button>
                </div>
              )}
            </form>
          </div>

          {/* Links section */}
          <div>
            <div className="flex items-center justify-between mb-6">
              <div className="flex items-center gap-4">
                <h2 className="font-[var(--font-outfit)] text-[20px] font-bold text-white">All links</h2>
                {total > 0 && (
                  <span className="text-[13px] font-semibold text-[#22d3ee] bg-[#22d3ee]/[0.08] border border-[#22d3ee]/15 px-3 py-1 rounded-lg tabular-nums">
                    {total}
                  </span>
                )}
              </div>
            </div>

            <div className="border border-[#2e2e4a] rounded-2xl overflow-hidden">
              {linksLoading ? (
                <div className="py-28 text-center">
                  <div className="w-6 h-6 border-2 border-[#22d3ee]/20 border-t-[#22d3ee] rounded-full animate-spin mx-auto" />
                </div>
              ) : links.length === 0 ? (
                <div className="py-28 text-center">
                  <div className="w-14 h-14 rounded-2xl bg-[#232340] border border-[#2e2e4a] flex items-center justify-center mx-auto mb-4">
                    <svg className="w-7 h-7 text-[#52526e]" fill="none" stroke="currentColor" strokeWidth={1.5} viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" />
                    </svg>
                  </div>
                  <p className="text-[16px] text-[#6e6e8a]">No links yet</p>
                  <p className="text-[14px] text-[#52526e] mt-1">Create your first short link above.</p>
                </div>
              ) : (
                <div>
                  {links.map((link, i) => (
                    <div
                      key={link.short_code}
                      className={`row-hover group flex items-center gap-5 px-8 py-6 transition-colors ${
                        i < links.length - 1 ? "border-b border-[#2e2e4a]" : ""
                      }`}
                    >
                      {/* Icon */}
                      <div className="w-12 h-12 rounded-xl bg-[#232340] border border-[#2e2e4a] flex items-center justify-center shrink-0 group-hover:border-[#22d3ee]/25 group-hover:bg-[#22d3ee]/[0.04] transition-all">
                        <svg className="w-5 h-5 text-[#6e6e8a] group-hover:text-[#22d3ee] transition-colors" fill="none" stroke="currentColor" strokeWidth={1.5} viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" />
                        </svg>
                      </div>

                      {/* URL info */}
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-3">
                          <code className="text-[16px] text-[#22d3ee] font-[var(--font-fira-code)] font-medium">
                            /{link.short_code}
                          </code>
                          <button
                            onClick={() => handleCopy(`${API_BASE}/${link.short_code}`)}
                            className="opacity-0 group-hover:opacity-100 transition-opacity text-[#6e6e8a] hover:text-white"
                          >
                            {copied === `${API_BASE}/${link.short_code}` ? (
                              <svg className="w-4 h-4 text-[#22c55e]" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                              </svg>
                            ) : (
                              <svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
                                <rect x="9" y="9" width="13" height="13" rx="2" />
                                <path d="M5 15H4a2 2 0 01-2-2V4a2 2 0 012-2h9a2 2 0 012 2v1" />
                              </svg>
                            )}
                          </button>
                        </div>
                        <p className="text-[14px] text-[#6e6e8a] truncate mt-1">
                          {link.original_url}
                        </p>
                      </div>

                      {/* Meta */}
                      <div className="hidden md:flex items-center gap-4 shrink-0">
                        {link.title && (
                          <span className="text-[13px] text-[#a1a1aa] bg-[#232340] border border-[#2e2e4a] px-3 py-1 rounded-lg max-w-[140px] truncate">
                            {link.title}
                          </span>
                        )}
                        <span className="text-[13px] text-[#52526e] tabular-nums whitespace-nowrap">
                          {timeAgo(link.created_at)}
                        </span>
                      </div>

                      {/* Actions */}
                      <div className="flex items-center gap-1.5 shrink-0 opacity-0 group-hover:opacity-100 transition-opacity">
                        <button
                          onClick={() => openEdit(link)}
                          className="p-2.5 rounded-lg text-[#6e6e8a] hover:text-white hover:bg-[#2e2e4a] transition-colors"
                          title="Edit"
                        >
                          <svg className="w-5 h-5" fill="none" stroke="currentColor" strokeWidth={1.5} viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" d="M16.862 4.487l1.687-1.688a1.875 1.875 0 112.652 2.652L10.582 16.07a4.5 4.5 0 01-1.897 1.13L6 18l.8-2.685a4.5 4.5 0 011.13-1.897l8.932-8.931z" />
                          </svg>
                        </button>
                        <button
                          onClick={() => setDeleteCode(link.short_code)}
                          className="p-2.5 rounded-lg text-[#6e6e8a] hover:text-[#f43f5e] hover:bg-[#f43f5e]/10 transition-colors"
                          title="Delete"
                        >
                          <svg className="w-5 h-5" fill="none" stroke="currentColor" strokeWidth={1.5} viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" d="M14.74 9l-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 01-2.244 2.077H8.084a2.25 2.25 0 01-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 00-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 013.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 00-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 00-7.5 0" />
                          </svg>
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Pagination */}
            {totalPages > 1 && (
              <div className="flex items-center justify-between mt-6">
                <p className="text-[14px] text-[#52526e] tabular-nums">{total} links</p>
                <div className="flex items-center gap-3">
                  <button
                    disabled={page <= 1}
                    onClick={() => setPage((p) => p - 1)}
                    className="h-10 px-4 text-[14px] text-[#8888a0] hover:text-white border border-[#2e2e4a] hover:border-[#3a3a56] rounded-lg transition-colors disabled:opacity-30"
                  >
                    Prev
                  </button>
                  <span className="text-[14px] text-[#6e6e8a] tabular-nums">{page}/{totalPages}</span>
                  <button
                    disabled={page >= totalPages}
                    onClick={() => setPage((p) => p + 1)}
                    className="h-10 px-4 text-[14px] text-[#8888a0] hover:text-white border border-[#2e2e4a] hover:border-[#3a3a56] rounded-lg transition-colors disabled:opacity-30"
                  >
                    Next
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      </main>

      {/* Edit Modal */}
      {editLink && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm" onClick={() => setEditLink(null)}>
          <div className="bg-[#1a1a2e] border border-[#2e2e4a] rounded-2xl p-8 w-full max-w-lg shadow-2xl animate-in" onClick={(e) => e.stopPropagation()}>
            <h3 className="font-[var(--font-outfit)] text-[20px] font-bold text-white mb-6">Edit link</h3>
            <div className="space-y-4">
              <div>
                <label className="block text-[14px] font-medium text-[#a1a1aa] mb-2">Destination URL</label>
                <input
                  className="w-full h-12 bg-[#232340] border border-[#2e2e4a] rounded-xl px-4 text-[15px] text-white focus:border-[#22d3ee]/50 focus:outline-none transition-all placeholder:text-[#52526e]"
                  value={editUrl}
                  onChange={(e) => setEditUrl(e.target.value)}
                />
              </div>
              <div>
                <label className="block text-[14px] font-medium text-[#a1a1aa] mb-2">Title</label>
                <input
                  className="w-full h-12 bg-[#232340] border border-[#2e2e4a] rounded-xl px-4 text-[15px] text-white focus:border-[#22d3ee]/50 focus:outline-none transition-all placeholder:text-[#52526e]"
                  placeholder="Optional"
                  value={editTitle}
                  onChange={(e) => setEditTitle(e.target.value)}
                />
              </div>
              {editError && <p className="text-[14px] text-[#f43f5e]">{editError}</p>}
            </div>
            <div className="flex justify-end gap-3 mt-8">
              <button
                onClick={() => setEditLink(null)}
                className="h-11 px-5 text-[14px] text-[#8888a0] hover:text-white border border-[#2e2e4a] hover:border-[#3a3a56] rounded-xl transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleEdit}
                disabled={editLoading}
                className="btn-press h-11 px-6 bg-[#22d3ee] hover:bg-[#06b6d4] text-[#1a1a2e] text-[14px] font-bold rounded-xl transition-all disabled:opacity-50"
              >
                {editLoading ? "Saving..." : "Save changes"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Delete Modal */}
      {deleteCode && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm" onClick={() => setDeleteCode(null)}>
          <div className="bg-[#1a1a2e] border border-[#2e2e4a] rounded-2xl p-8 w-full max-w-md shadow-2xl animate-in" onClick={(e) => e.stopPropagation()}>
            <h3 className="font-[var(--font-outfit)] text-[20px] font-bold text-white mb-3">Delete link</h3>
            <p className="text-[15px] text-[#8888a0] mb-8">This will permanently remove this link. This cannot be undone.</p>
            <div className="flex justify-end gap-3">
              <button
                onClick={() => setDeleteCode(null)}
                className="h-11 px-5 text-[14px] text-[#8888a0] hover:text-white border border-[#2e2e4a] hover:border-[#3a3a56] rounded-xl transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleDelete}
                disabled={deleteLoading}
                className="btn-press h-11 px-6 bg-[#f43f5e] hover:bg-[#e11d48] text-white text-[14px] font-bold rounded-xl transition-all disabled:opacity-50"
              >
                {deleteLoading ? "Deleting..." : "Delete"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
