import { createClient } from "@supabase/supabase-js";

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL ?? "";
const supabaseKey = import.meta.env.VITE_SUPABASE_PUBLISHABLE_KEY ?? "";

export const supabase = createClient(supabaseUrl, supabaseKey);

export async function signInWithGoogle() {
  return supabase.auth.signInWithOAuth({
    provider: "google",
    options: { redirectTo: `${window.location.origin}/dashboard` },
  });
}

export async function signInWithGitHub() {
  return supabase.auth.signInWithOAuth({
    provider: "github",
    options: { redirectTo: `${window.location.origin}/dashboard` },
  });
}

export async function signInWithEmail(email: string, password: string) {
  return supabase.auth.signInWithPassword({ email, password });
}

export async function signUpWithEmail(email: string, password: string) {
  return supabase.auth.signUp({
    email,
    password,
    options: { emailRedirectTo: `${window.location.origin}/dashboard` },
  });
}

export async function signOut() {
  return supabase.auth.signOut();
}

export async function getSession() {
  return supabase.auth.getSession();
}

export async function uploadDocument(file: File, userId: string, documentId: string) {
  const path = `${userId}/${documentId}/${file.name}`;
  return supabase.storage.from("documents").upload(path, file, {
    cacheControl: "3600",
    upsert: false,
  });
}

export async function getDocumentUrl(path: string, expiresIn = 3600) {
  return supabase.storage.from("documents").createSignedUrl(path, expiresIn);
}
