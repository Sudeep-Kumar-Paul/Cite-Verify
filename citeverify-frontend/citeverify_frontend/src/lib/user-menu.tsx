import React, { useState } from "react";
import { useAuth } from "./auth-context";
import { Button } from "@/button";
import { Avatar, AvatarFallback, AvatarImage } from "@/avatar";
import {
  DropdownMenu,
  DropdownMenuTrigger,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
} from "@/dropdown-menu";
import { AuthDialog } from "./auth-dialog";
import { LogIn, LogOut, User, ShieldCheck, Sparkles } from "lucide-react";

export function UserMenu() {
  const { user, signOut, loading } = useAuth();
  const [authDialogOpen, setAuthDialogOpen] = useState(false);

  if (loading) {
    return (
      <div className="h-8 w-8 rounded-full bg-muted animate-pulse" />
    );
  }

  if (!user) {
    return (
      <>
        <Button
          variant="outline"
          size="sm"
          onClick={() => setAuthDialogOpen(true)}
          className="gap-2 text-xs font-semibold h-8 rounded-full px-3.5 border-primary/20 hover:border-primary/40 hover:bg-primary/5 transition-all"
        >
          <LogIn className="h-3.5 w-3.5 text-primary" />
          <span>Sign In</span>
        </Button>
        <AuthDialog open={authDialogOpen} onOpenChange={setAuthDialogOpen} />
      </>
    );
  }

  // Get user initials for avatar fallback
  const initials = user.displayName
    ? user.displayName
        .split(" ")
        .map((n) => n[0])
        .join("")
        .substring(0, 2)
        .toUpperCase()
    : (user.email?.[0] || "U").toUpperCase();

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <button
          className="flex items-center gap-2 rounded-full p-0.5 hover:ring-2 hover:ring-primary/20 transition-all focus:outline-none cursor-pointer"
          aria-label="User profile options"
        >
          <Avatar className="h-8 w-8 border border-border/80 shadow-xs">
            {user.photoURL && <AvatarImage src={user.photoURL} alt={user.displayName || "User"} />}
            <AvatarFallback className="bg-primary/10 text-primary font-semibold text-xs">
              {initials}
            </AvatarFallback>
          </Avatar>
        </button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-56 p-2 shadow-lg">
        <DropdownMenuLabel className="font-normal">
          <div className="flex flex-col space-y-1">
            <p className="text-sm font-semibold leading-none text-foreground flex items-center gap-1.5">
              <span>{user.displayName || "Researcher"}</span>
              {user.isDemo && (
                <span className="text-[10px] uppercase font-bold tracking-wider px-1.5 py-0.2 rounded bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300">
                  Demo
                </span>
              )}
            </p>
            <p className="text-xs leading-none text-muted-foreground truncate">
              {user.email || "No email available"}
            </p>
            <p className="text-[11px] text-muted-foreground/80 flex items-center gap-1 pt-1">
              {user.providerId === "google.com" ? (
                <>
                  <svg className="h-3 w-3 shrink-0" viewBox="0 0 24 24">
                    <path
                      fill="#4285F4"
                      d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
                    />
                    <path
                      fill="#34A853"
                      d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
                    />
                    <path
                      fill="#FBBC05"
                      d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z"
                    />
                    <path
                      fill="#EA4335"
                      d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z"
                    />
                  </svg>
                  <span>Google Account</span>
                </>
              ) : (
                <>
                  <ShieldCheck className="h-3 w-3 text-primary shrink-0" />
                  <span>Email Verified</span>
                </>
              )}
            </p>
          </div>
        </DropdownMenuLabel>
        <DropdownMenuSeparator />
        <DropdownMenuItem
          onClick={() => signOut()}
          className="cursor-pointer text-destructive focus:text-destructive focus:bg-destructive/10 gap-2"
        >
          <LogOut className="h-4 w-4" />
          <span>Sign Out</span>
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
