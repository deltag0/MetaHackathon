const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "";

async function request<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const token =
    typeof window !== "undefined" ? localStorage.getItem("session_token") : null;

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...((options.headers as Record<string, string>) || {}),
  };

  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const res = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers,
  });

  const data = await res.json();

  if (!res.ok) {
    throw new Error(data.error || "Something went wrong");
  }

  return data as T;
}

// Auth
export interface AuthResponse {
  session_token: string;
  user: { id: number; email: string };
}

export function login(email: string, password: string) {
  return request<AuthResponse>("/api/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
}

export function register(email: string, password: string) {
  return request<AuthResponse>("/api/auth/register", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
}

// Links
export interface Link {
  short_code: string;
  original_url: string;
  title: string | null;
  created_at: string;
  short_url?: string;
  updated_at?: string;
}

export interface LinksResponse {
  total: number;
  page: number;
  per_page: number;
  links: Link[];
}

export function getLinks(page = 1, perPage = 20) {
  return request<LinksResponse>(
    `/api/links?page=${page}&per_page=${perPage}`
  );
}

export function shortenUrl(url: string, title?: string) {
  return request<Link>("/shorten", {
    method: "POST",
    body: JSON.stringify({ url, title: title || undefined }),
  });
}

export function updateLink(code: string, url?: string, title?: string) {
  return request<Link>(`/api/links/${code}`, {
    method: "PUT",
    body: JSON.stringify({
      ...(url ? { url } : {}),
      ...(title ? { title } : {}),
    }),
  });
}

export function deleteLink(code: string) {
  return request<{ message: string }>(`/api/links/${code}`, {
    method: "DELETE",
  });
}
