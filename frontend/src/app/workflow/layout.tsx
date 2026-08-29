import { AuthProvider } from "@/lib/auth-context";

export default function WorkflowLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <AuthProvider>
      {children}
    </AuthProvider>
  );
}
