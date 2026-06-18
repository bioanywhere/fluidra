// Minimal Firebase Authentication via the REST API — no SDK dependency.
// Active only when NEXT_PUBLIC_FIREBASE_API_KEY is set; otherwise the app runs
// anonymously (current dev behavior). Email/password sign-in; ID tokens are
// refreshed on demand. (Add the Firebase JS SDK later for social providers.)

const API_KEY = process.env.NEXT_PUBLIC_FIREBASE_API_KEY ?? "";
const STORE = "fluidra_fb_auth";

export function firebaseEnabled(): boolean {
  return Boolean(API_KEY);
}

type Session = {
  idToken: string;
  refreshToken: string;
  expiresAt: number; // epoch ms
  email: string;
  uid: string;
};

function read(): Session | null {
  try {
    const s = localStorage.getItem(STORE);
    return s ? (JSON.parse(s) as Session) : null;
  } catch {
    return null;
  }
}

function write(s: Session | null) {
  try {
    if (s) localStorage.setItem(STORE, JSON.stringify(s));
    else localStorage.removeItem(STORE);
  } catch {
    /* ignore */
  }
  if (typeof window !== "undefined") window.dispatchEvent(new Event("fb-auth"));
}

export function currentUser(): { email: string; uid: string } | null {
  const s = read();
  return s ? { email: s.email, uid: s.uid } : null;
}

export async function signIn(email: string, password: string): Promise<void> {
  const res = await fetch(
    `https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key=${API_KEY}`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password, returnSecureToken: true }),
    },
  );
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data?.error?.message || "Sign-in failed");
  write({
    idToken: data.idToken,
    refreshToken: data.refreshToken,
    expiresAt: Date.now() + (Number(data.expiresIn) - 30) * 1000,
    email: data.email,
    uid: data.localId,
  });
}

export function signOut(): void {
  write(null);
}

// Returns a valid ID token (refreshing if expired), or null if not signed in.
export async function getIdToken(): Promise<string | null> {
  const s = read();
  if (!s) return null;
  if (Date.now() < s.expiresAt) return s.idToken;
  try {
    const res = await fetch(`https://securetoken.googleapis.com/v1/token?key=${API_KEY}`, {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: `grant_type=refresh_token&refresh_token=${encodeURIComponent(s.refreshToken)}`,
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      write(null);
      return null;
    }
    const next: Session = {
      ...s,
      idToken: data.id_token,
      refreshToken: data.refresh_token,
      expiresAt: Date.now() + (Number(data.expires_in) - 30) * 1000,
    };
    write(next);
    return next.idToken;
  } catch {
    return null;
  }
}
