import { Link } from "react-router-dom";
import { Compass } from "lucide-react";
import { Button } from "@/components/ui/button";
import { AtlasWordmark } from "@/components/logo";

export default function NotFound() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-6 px-6 text-center">
      <AtlasWordmark />
      <Compass className="h-16 w-16 text-brand" />
      <div>
        <h1 className="font-display text-4xl font-bold">Off the map</h1>
        <p className="mt-2 text-muted-foreground">
          This route doesn't exist — but every other path is still open to you.
        </p>
      </div>
      <Button variant="brand" asChild>
        <Link to="/">Back to safe ground</Link>
      </Button>
    </div>
  );
}
