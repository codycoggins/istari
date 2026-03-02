import { apiFetch } from "./client";

export async function login(password: string): Promise<void> {
  await apiFetch("/auth/login", {
    method: "POST",
    body: JSON.stringify({ password }),
  });
}

export async function logout(): Promise<void> {
  await apiFetch("/auth/logout", { method: "POST" });
}

export async function checkAuth(): Promise<boolean> {
  try {
    await apiFetch("/auth/me");
    return true;
  } catch {
    return false;
  }
}
