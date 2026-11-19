import { initializeApp, getApps, getApp, type FirebaseApp } from "firebase/app";
import {
  getAuth,
  GoogleAuthProvider,
  signInWithPopup,
  signInWithEmailAndPassword,
  createUserWithEmailAndPassword,
  signOut as firebaseSignOut,
  sendPasswordResetEmail,
  updateProfile,
  onAuthStateChanged,
  type Auth,
  type User,
  type UserCredential,
} from "firebase/auth";

// Read environment variables
const env = import.meta.env;

export const firebaseConfig = {
  apiKey: env.VITE_FIREBASE_API_KEY || "",
  authDomain: env.VITE_FIREBASE_AUTH_DOMAIN || "",
  projectId: env.VITE_FIREBASE_PROJECT_ID || "",
  storageBucket: env.VITE_FIREBASE_STORAGE_BUCKET || "",
  messagingSenderId: env.VITE_FIREBASE_MESSAGING_SENDER_ID || "",
  appId: env.VITE_FIREBASE_APP_ID || "",
  measurementId: env.VITE_FIREBASE_MEASUREMENT_ID || "",
};

// Check if valid Firebase configuration is provided
export const isFirebaseConfigured: boolean = Boolean(
  firebaseConfig.apiKey &&
    firebaseConfig.apiKey !== "your_firebase_api_key_here" &&
    firebaseConfig.projectId &&
    firebaseConfig.projectId !== "your_firebase_project_id_here",
);

let app: FirebaseApp | null = null;
let auth: Auth | null = null;
let googleProvider: GoogleAuthProvider | null = null;

if (isFirebaseConfigured) {
  try {
    app = getApps().length > 0 ? getApp() : initializeApp(firebaseConfig);
    auth = getAuth(app);
    googleProvider = new GoogleAuthProvider();
    googleProvider.setCustomParameters({ prompt: "select_account" });
  } catch (error) {
    console.error("Failed to initialize Firebase:", error);
  }
}

/**
 * Format common Firebase authentication error codes into clear, actionable messages
 */
export function getFirebaseErrorMessage(errorCode: string, rawMessage?: string): string {
  let code = errorCode || "";
  if ((!code || code === "undefined") && rawMessage) {
    const match = rawMessage.match(/\((auth\/[^)]+)\)/);
    if (match) {
      code = match[1];
    }
  }

  switch (code) {
    case "auth/unauthorized-domain":
      return "This domain (127.0.0.1) is not authorized in Firebase. Open http://localhost:5173 in your browser, or add 127.0.0.1 to Firebase Console → Authentication → Settings → Authorized domains.";
    case "auth/operation-not-allowed":
      return "This sign-in provider (Google or Email) is not enabled in Firebase Console. Go to Authentication → Sign-in method and enable it.";
    case "auth/invalid-email":
      return "The email address is invalid.";
    case "auth/user-disabled":
      return "This user account has been disabled.";
    case "auth/user-not-found":
      return "No account found with this email. Click the 'Create Account' tab to register.";
    case "auth/wrong-password":
      return "Incorrect password. Please try again or use 'Forgot password?'.";
    case "auth/invalid-credential":
      return "Invalid email or password. If you haven't created an account yet, click the 'Create Account' tab above.";
    case "auth/email-already-in-use":
      return "An account with this email address already exists. Please sign in instead.";
    case "auth/weak-password":
      return "Password should be at least 6 characters.";
    case "auth/popup-closed-by-user":
      return "The Google sign-in window was closed before completion.";
    case "auth/cancelled-popup-request":
      return "Google sign-in popup was cancelled.";
    case "auth/popup-blocked":
      return "Google sign-in popup was blocked by your browser. Please allow popups for this site.";
    case "auth/network-request-failed":
      return "Network error. Please check your internet connection.";
    case "auth/too-many-requests":
      return "Too many unsuccessful attempts. Please try again in a few minutes.";
    case "auth/configuration-not-found":
      return "Firebase Authentication is not enabled for this project. Please enable it in the Firebase Console.";
    case "auth/project-not-found":
      return "Firebase project not found. Please verify your Project ID in .env.";
    case "auth/invalid-api-key":
      return "Invalid Firebase API key in .env. Please check your Firebase Project Settings.";
    case "auth/account-exists-with-different-credential":
      return "An account already exists with the same email using a different sign-in method.";
    default:
      if (rawMessage && !rawMessage.startsWith("Firebase: Error")) {
        return rawMessage;
      }
      if (errorCode) {
        return `Firebase error (${errorCode}). ${rawMessage || "Please check your Firebase project configuration."}`;
      }
      return rawMessage || "Authentication error. Please try again.";
  }
}

export {
  app,
  auth,
  googleProvider,
  signInWithPopup,
  signInWithEmailAndPassword,
  createUserWithEmailAndPassword,
  firebaseSignOut,
  sendPasswordResetEmail,
  updateProfile,
  onAuthStateChanged,
  type User,
  type UserCredential,
};
