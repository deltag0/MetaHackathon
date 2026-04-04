"use client";

import { useState } from "react";
import { useAuth } from "@/context/auth-context";

export default function LoginPage() {
  const { login, register } = useAuth();
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [mode, setMode] = useState<"login" | "register">("login");

  const [loginEmail, setLoginEmail] = useState("");
  const [loginPassword, setLoginPassword] = useState("");
  const [regEmail, setRegEmail] = useState("");
  const [regPassword, setRegPassword] = useState("");
  const [regConfirm, setRegConfirm] = useState("");

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await login(loginEmail, loginPassword);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed");
    } finally {
      setLoading(false);
    }
  };

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    if (regPassword !== regConfirm) { setError("Passwords do not match"); return; }
    if (regPassword.length < 8) { setError("Password must be at least 8 characters"); return; }
    setLoading(true);
    try {
      await register(regEmail, regPassword);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Registration failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex bg-[#1a1a2e] glow-bg">
      {/* Left panel — branding */}
      <div className="hidden lg:flex lg:w-[45%] relative overflow-hidden">
        <div className="absolute inset-0 bg-[#212145]">
          {/* Grid */}
          <div className="absolute inset-0" style={{
            backgroundImage: `
              linear-gradient(rgba(34,211,238,0.04) 1px, transparent 1px),
              linear-gradient(90deg, rgba(34,211,238,0.04) 1px, transparent 1px)
            `,
            backgroundSize: "60px 60px",
          }} />
          {/* Diagonal accents */}
          <div className="absolute -top-20 -right-20 w-[200%] h-[1px] bg-gradient-to-r from-transparent via-[#22d3ee]/25 to-transparent rotate-[35deg] origin-top-left" />
          <div className="absolute top-[30%] -right-20 w-[200%] h-[1px] bg-gradient-to-r from-transparent via-[#f0abfc]/15 to-transparent rotate-[35deg] origin-top-left" />
          {/* Glow blobs */}
          <div className="absolute bottom-0 left-0 w-[500px] h-[500px] bg-[#22d3ee]/[0.06] rounded-full blur-[120px]" />
          <div className="absolute top-[10%] right-[10%] w-[300px] h-[300px] bg-[#f0abfc]/[0.04] rounded-full blur-[100px]" />
        </div>

        <div className="relative z-10 flex flex-col justify-between p-14 w-full">
          {/* Logo */}
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-[#22d3ee] flex items-center justify-center">
              <svg className="w-5 h-5 text-[#1a1a2e]" fill="none" stroke="currentColor" strokeWidth={2.5} viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" />
              </svg>
            </div>
            <span className="font-[var(--font-outfit)] text-[20px] font-bold text-white tracking-tight">
              shorten.it
            </span>
          </div>

          {/* Tagline */}
          <div className="stagger">
            <h2 className="font-[var(--font-outfit)] text-[56px] leading-[1.05] font-extrabold text-white tracking-tight max-w-md">
              Every link,<br />
              <span className="bg-gradient-to-r from-[#22d3ee] to-[#f0abfc] bg-clip-text text-transparent">refined.</span>
            </h2>
            <p className="mt-5 text-[17px] text-[#8888a0] max-w-sm leading-relaxed">
              Shorten, track, and manage your URLs with precision.
            </p>
          </div>

          {/* Stats */}
          <div className="flex gap-12 stagger">
            <div>
              <div className="font-[var(--font-outfit)] text-[32px] font-bold text-white">2.4M+</div>
              <div className="text-[14px] text-[#6e6e8a] mt-0.5">Links shortened</div>
            </div>
            <div>
              <div className="font-[var(--font-outfit)] text-[32px] font-bold text-white">99.9%</div>
              <div className="text-[14px] text-[#6e6e8a] mt-0.5">Uptime</div>
            </div>
            <div>
              <div className="font-[var(--font-outfit)] text-[32px] font-bold text-white">&lt;50ms</div>
              <div className="text-[14px] text-[#6e6e8a] mt-0.5">Redirect speed</div>
            </div>
          </div>
        </div>
      </div>

      {/* Right panel — form */}
      <div className="flex-1 flex items-center justify-center px-8 py-12 relative z-10">
        <div className="w-full max-w-[420px] stagger">
          {/* Mobile logo */}
          <div className="flex lg:hidden items-center gap-3 mb-14">
            <div className="w-10 h-10 rounded-xl bg-[#22d3ee] flex items-center justify-center">
              <svg className="w-5 h-5 text-[#1a1a2e]" fill="none" stroke="currentColor" strokeWidth={2.5} viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" />
              </svg>
            </div>
            <span className="font-[var(--font-outfit)] text-[18px] font-bold text-white">shorten.it</span>
          </div>

          {/* Toggle */}
          <div className="flex gap-1 p-1.5 bg-[#232340] rounded-xl mb-10 border border-[#2e2e4a]">
            <button
              type="button"
              onClick={() => { setMode("login"); setError(""); }}
              className={`flex-1 py-2.5 text-[15px] font-medium rounded-lg transition-all duration-200 ${
                mode === "login"
                  ? "bg-[#2e2e4a] text-white shadow-sm"
                  : "text-[#6e6e8a] hover:text-[#a1a1aa]"
              }`}
            >
              Sign in
            </button>
            <button
              type="button"
              onClick={() => { setMode("register"); setError(""); }}
              className={`flex-1 py-2.5 text-[15px] font-medium rounded-lg transition-all duration-200 ${
                mode === "register"
                  ? "bg-[#2e2e4a] text-white shadow-sm"
                  : "text-[#6e6e8a] hover:text-[#a1a1aa]"
              }`}
            >
              Create account
            </button>
          </div>

          {/* Title */}
          <div className="mb-8">
            <h1 className="font-[var(--font-outfit)] text-[30px] font-bold text-white tracking-tight">
              {mode === "login" ? "Welcome back" : "Get started"}
            </h1>
            <p className="text-[15px] text-[#6e6e8a] mt-1.5">
              {mode === "login"
                ? "Sign in to your account to continue."
                : "Create a new account to get started."}
            </p>
          </div>

          {/* Login */}
          {mode === "login" ? (
            <form onSubmit={handleLogin} className="space-y-5">
              <div>
                <label className="block text-[14px] font-medium text-[#a1a1aa] mb-2">Email address</label>
                <input
                  className="w-full h-12 bg-[#232340] border border-[#2e2e4a] rounded-xl px-4 text-[15px] text-white focus:border-[#22d3ee]/50 focus:outline-none transition-all placeholder:text-[#52526e]"
                  placeholder="you@example.com"
                  type="email"
                  value={loginEmail}
                  onChange={(e) => setLoginEmail(e.target.value)}
                  required
                />
              </div>
              <div>
                <label className="block text-[14px] font-medium text-[#a1a1aa] mb-2">Password</label>
                <input
                  className="w-full h-12 bg-[#232340] border border-[#2e2e4a] rounded-xl px-4 text-[15px] text-white focus:border-[#22d3ee]/50 focus:outline-none transition-all placeholder:text-[#52526e]"
                  placeholder="Enter your password"
                  type="password"
                  value={loginPassword}
                  onChange={(e) => setLoginPassword(e.target.value)}
                  required
                />
              </div>

              {error && (
                <div className="text-[14px] text-[#f43f5e] bg-[#f43f5e]/[0.08] border border-[#f43f5e]/15 rounded-xl px-4 py-3">
                  {error}
                </div>
              )}

              <button
                type="submit"
                disabled={loading}
                className="btn-press w-full h-12 bg-[#22d3ee] hover:bg-[#06b6d4] text-[#1a1a2e] text-[15px] font-bold rounded-xl transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed mt-2"
              >
                {loading ? (
                  <span className="flex items-center justify-center gap-2">
                    <div className="w-4 h-4 border-2 border-[#1a1a2e]/20 border-t-[#1a1a2e] rounded-full animate-spin" />
                    Signing in...
                  </span>
                ) : "Sign in"}
              </button>
            </form>
          ) : (
            <form onSubmit={handleRegister} className="space-y-5">
              <div>
                <label className="block text-[14px] font-medium text-[#a1a1aa] mb-2">Email address</label>
                <input
                  className="w-full h-12 bg-[#232340] border border-[#2e2e4a] rounded-xl px-4 text-[15px] text-white focus:border-[#22d3ee]/50 focus:outline-none transition-all placeholder:text-[#52526e]"
                  placeholder="you@example.com"
                  type="email"
                  value={regEmail}
                  onChange={(e) => setRegEmail(e.target.value)}
                  required
                />
              </div>
              <div>
                <label className="block text-[14px] font-medium text-[#a1a1aa] mb-2">Password</label>
                <input
                  className="w-full h-12 bg-[#232340] border border-[#2e2e4a] rounded-xl px-4 text-[15px] text-white focus:border-[#22d3ee]/50 focus:outline-none transition-all placeholder:text-[#52526e]"
                  placeholder="Min 8 characters"
                  type="password"
                  value={regPassword}
                  onChange={(e) => setRegPassword(e.target.value)}
                  required
                />
              </div>
              <div>
                <label className="block text-[14px] font-medium text-[#a1a1aa] mb-2">Confirm password</label>
                <input
                  className="w-full h-12 bg-[#232340] border border-[#2e2e4a] rounded-xl px-4 text-[15px] text-white focus:border-[#22d3ee]/50 focus:outline-none transition-all placeholder:text-[#52526e]"
                  placeholder="Repeat password"
                  type="password"
                  value={regConfirm}
                  onChange={(e) => setRegConfirm(e.target.value)}
                  required
                />
              </div>

              {error && (
                <div className="text-[14px] text-[#f43f5e] bg-[#f43f5e]/[0.08] border border-[#f43f5e]/15 rounded-xl px-4 py-3">
                  {error}
                </div>
              )}

              <button
                type="submit"
                disabled={loading}
                className="btn-press w-full h-12 bg-[#22d3ee] hover:bg-[#06b6d4] text-[#1a1a2e] text-[15px] font-bold rounded-xl transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed mt-2"
              >
                {loading ? (
                  <span className="flex items-center justify-center gap-2">
                    <div className="w-4 h-4 border-2 border-[#1a1a2e]/20 border-t-[#1a1a2e] rounded-full animate-spin" />
                    Creating account...
                  </span>
                ) : "Create account"}
              </button>
            </form>
          )}

          <p className="text-[12px] text-[#52526e] text-center mt-10">
            By continuing, you agree to our Terms of Service.
          </p>
        </div>
      </div>
    </div>
  );
}
