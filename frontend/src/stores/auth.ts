/** Global auth state. Tokens live in tokenStore; this holds the hydrated user
 * and the auth lifecycle (login / register / logout / hydrate). */

import { create } from "zustand";
import { api } from "@/lib/apiClient";
import { clearTokens, getTokens, setTokens } from "@/lib/tokenStore";
import type { Role, TokenPair, User } from "@/types/api";

type Status = "idle" | "loading" | "authenticated" | "unauthenticated";

interface RegisterPayload {
  email: string;
  password: string;
  full_name: string;
  role: Role;
  org_name?: string;
}

interface AuthState {
  user: User | null;
  status: Status;
  login: (email: string, password: string) => Promise<User>;
  register: (payload: RegisterPayload) => Promise<User>;
  logout: () => Promise<void>;
  hydrate: () => Promise<void>;
  setUser: (user: User) => void;
}

export const useAuth = create<AuthState>((set, get) => ({
  user: null,
  status: "idle",

  async login(email, password) {
    const tokens = await api.post<TokenPair>(
      "/auth/login",
      { username: email, password },
      { auth: false, formUrlEncoded: true },
    );
    setTokens(tokens);
    await get().hydrate();
    const user = get().user;
    if (!user) throw new Error("Failed to load profile after login.");
    return user;
  },

  async register(payload) {
    await api.post("/auth/register", payload, { auth: false });
    return get().login(payload.email, payload.password);
  },

  async logout() {
    try {
      await api.post("/auth/logout");
    } catch {
      /* best-effort */
    }
    clearTokens();
    set({ user: null, status: "unauthenticated" });
  },

  async hydrate() {
    if (!getTokens()?.access_token) {
      set({ status: "unauthenticated", user: null });
      return;
    }
    set({ status: "loading" });
    try {
      const user = await api.get<User>("/auth/me");
      set({ user, status: "authenticated" });
    } catch {
      clearTokens();
      set({ user: null, status: "unauthenticated" });
    }
  },

  setUser(user) {
    set({ user });
  },
}));
