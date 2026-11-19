import React, { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import {
  auth,
  googleProvider,
  isFirebaseConfigured,
  signInWithPopup,
  signInWithEmailAndPassword,
  createUserWithEmailAndPassword,
  firebaseSignOut,
  sendPasswordResetEmail,
  updateProfile,
  onAuthStateChanged,
  getFirebaseErrorMessage,
  type User,
} from "./firebase";
import { setAuthTokenProvider } from "./api";

export interface AuthUser {
  uid: string;
  email: string | null;
  displayName: string | null;
  photoURL: string | null;
  providerId: string;
  isDemo?: boolean;
}

interface AuthContextType {
  user: AuthUser | null;
  rawFirebaseUser: User | null;
  loading: boolean;
  isConfigured: boolean;
  signInWithEmail: (email: string, pass: string) => Promise<void>;
  signUpWithEmail: (email: string, pass: string, name?: string) => Promise<void>;
  signInWithGoogle: () => Promise<void>;
  signOut: () => Promise<void>;
  sendPasswordReset: (email: string) => Promise<void>;
  loginDemoUser: (customEmail?: string, customName?: string) => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

const DEMO_USER_STORAGE_KEY = "citeverify_demo_user";

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [rawFirebaseUser, setRawFirebaseUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  // Initialize Auth Token Provider for API calls
  useEffect(() => {
    setAuthTokenProvider(async () => {
      if (rawFirebaseUser) {
        try {
          return await rawFirebaseUser.getIdToken();
        } catch {
          return null;
        }
      }
      if (user?.isDemo) {
        return `demo-token-${user.uid}`;
      }
      return null;
    });
  }, [rawFirebaseUser, user]);

  useEffect(() => {
    if (isFirebaseConfigured && auth) {
      // Listen to real Firebase Auth state changes
      const unsubscribe = onAuthStateChanged(auth, (firebaseUser) => {
        setRawFirebaseUser(firebaseUser);
        if (firebaseUser) {
          const provider = firebaseUser.providerData[0]?.providerId || "password";
          setUser({
            uid: firebaseUser.uid,
            email: firebaseUser.email,
            displayName: firebaseUser.displayName || (firebaseUser.email ? firebaseUser.email.split("@")[0] : "Researcher"),
            photoURL: firebaseUser.photoURL,
            providerId: provider,
            isDemo: false,
          });
        } else {
          setUser(null);
        }
        setLoading(false);
      });

      return () => unsubscribe();
    } else {
      // Check for saved demo user in localStorage
      if (typeof window !== "undefined") {
        try {
          const saved = localStorage.getItem(DEMO_USER_STORAGE_KEY);
          if (saved) {
            setUser(JSON.parse(saved));
          }
        } catch {
          // Ignore localStorage errors
        }
      }
      setLoading(false);
    }
  }, []);

  // Email & Password Sign In
  const handleSignInWithEmail = async (email: string, pass: string) => {
    if (!isFirebaseConfigured || !auth) {
      loginDemoUser(email, email.split("@")[0]);
      return;
    }
    try {
      await signInWithEmailAndPassword(auth, email.trim(), pass);
    } catch (err: any) {
      const message = getFirebaseErrorMessage(err?.code || "", err?.message);
      throw new Error(message || err?.message || "Failed to sign in.");
    }
  };

  // Email & Password Sign Up
  const handleSignUpWithEmail = async (email: string, pass: string, name?: string) => {
    if (!isFirebaseConfigured || !auth) {
      loginDemoUser(email, name || email.split("@")[0]);
      return;
    }
    try {
      const userCredential = await createUserWithEmailAndPassword(auth, email.trim(), pass);
      if (name && userCredential.user) {
        await updateProfile(userCredential.user, { displayName: name });
        setUser({
          uid: userCredential.user.uid,
          email: userCredential.user.email,
          displayName: name,
          photoURL: userCredential.user.photoURL,
          providerId: "password",
          isDemo: false,
        });
      }
    } catch (err: any) {
      const message = getFirebaseErrorMessage(err?.code || "", err?.message);
      throw new Error(message || err?.message || "Failed to create account.");
    }
  };

  // Google Sign In
  const handleSignInWithGoogle = async () => {
    if (!isFirebaseConfigured || !auth || !googleProvider) {
      loginDemoUser("researcher@gmail.com", "Google Researcher");
      return;
    }
    try {
      await signInWithPopup(auth, googleProvider);
    } catch (err: any) {
      const message = getFirebaseErrorMessage(err?.code || "", err?.message);
      throw new Error(message || err?.message || "Failed to sign in with Google.");
    }
  };

  // Sign Out
  const handleSignOut = async () => {
    if (isFirebaseConfigured && auth) {
      await firebaseSignOut(auth);
    }
    setUser(null);
    setRawFirebaseUser(null);
    if (typeof window !== "undefined") {
      try {
        localStorage.removeItem(DEMO_USER_STORAGE_KEY);
      } catch {
        // Ignore
      }
    }
  };

  // Password Reset
  const handleSendPasswordReset = async (email: string) => {
    if (!isFirebaseConfigured || !auth) {
      return;
    }
    try {
      await sendPasswordResetEmail(auth, email.trim());
    } catch (err: any) {
      const message = getFirebaseErrorMessage(err?.code || "", err?.message);
      throw new Error(message || err?.message || "Failed to send password reset email.");
    }
  };

  // Demo user login (for quick preview/testing before Firebase API keys are configured)
  const loginDemoUser = (customEmail?: string, customName?: string) => {
    const demoUser: AuthUser = {
      uid: "demo-user-" + Math.random().toString(36).substring(2, 9),
      email: customEmail || "researcher@citeverify.org",
      displayName: customName || "Dr. Alex Vance",
      photoURL: null,
      providerId: customEmail?.includes("gmail.com") ? "google.com" : "password",
      isDemo: true,
    };
    setUser(demoUser);
    if (typeof window !== "undefined") {
      try {
        localStorage.setItem(DEMO_USER_STORAGE_KEY, JSON.stringify(demoUser));
      } catch {
        // Ignore
      }
    }
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        rawFirebaseUser,
        loading,
        isConfigured: isFirebaseConfigured,
        signInWithEmail: handleSignInWithEmail,
        signUpWithEmail: handleSignUpWithEmail,
        signInWithGoogle: handleSignInWithGoogle,
        signOut: handleSignOut,
        sendPasswordReset: handleSendPasswordReset,
        loginDemoUser,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextType {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
