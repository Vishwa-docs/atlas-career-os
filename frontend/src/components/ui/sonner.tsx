import { Toaster as Sonner } from "sonner";

export function Toaster() {
  return (
    <Sonner
      position="top-right"
      toastOptions={{
        classNames: {
          toast:
            "group rounded-xl border bg-card text-card-foreground shadow-lg",
          description: "text-muted-foreground",
        },
      }}
    />
  );
}
