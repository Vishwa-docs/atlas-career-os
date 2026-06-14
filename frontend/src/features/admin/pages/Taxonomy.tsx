import { useState } from "react";
import { ArrowLeftRight, Boxes, Briefcase, Search, Tags } from "lucide-react";
import { PageHeader, SectionHeading, StatCard, EmptyState, Spinner } from "@/components/common";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { formatCurrency } from "@/lib/utils";
import {
  useAdminTaxonomy,
  useTaxonomySkills,
  useTaxonomyOccupations,
  asArray,
  type TaxonomySkill,
  type TaxonomyOccupation,
} from "../api";

function SkillsBrowser() {
  const [draft, setDraft] = useState("");
  const [q, setQ] = useState("");
  const { data, isLoading, isFetching, isError } = useTaxonomySkills(q);
  const skills = asArray<TaxonomySkill>(data);

  return (
    <BrowserShell
      placeholder="Search skills…"
      draft={draft}
      setDraft={setDraft}
      onSubmit={() => setQ(draft.trim())}
      isFetching={isFetching}
    >
      {isLoading ? (
        <BrowserSkeleton />
      ) : isError ? (
        <EmptyState icon={Tags} title="Couldn't load skills" />
      ) : skills.length === 0 ? (
        <EmptyState icon={Tags} title={q ? "No matching skills" : "No skills yet"} />
      ) : (
        <div className="flex flex-wrap gap-2">
          {skills.map((s) => (
            <Badge key={s.id} variant="secondary" className="gap-1.5 py-1">
              {s.name}
              {s.category && (
                <span className="text-[10px] uppercase tracking-wide text-muted-foreground">
                  {s.category}
                </span>
              )}
            </Badge>
          ))}
        </div>
      )}
    </BrowserShell>
  );
}

function OccupationsBrowser() {
  const [draft, setDraft] = useState("");
  const [q, setQ] = useState("");
  const { data, isLoading, isFetching, isError } = useTaxonomyOccupations(q);
  const occupations = asArray<TaxonomyOccupation>(data);

  return (
    <BrowserShell
      placeholder="Search occupations…"
      draft={draft}
      setDraft={setDraft}
      onSubmit={() => setQ(draft.trim())}
      isFetching={isFetching}
    >
      {isLoading ? (
        <BrowserSkeleton />
      ) : isError ? (
        <EmptyState icon={Briefcase} title="Couldn't load occupations" />
      ) : occupations.length === 0 ? (
        <EmptyState icon={Briefcase} title={q ? "No matching occupations" : "No occupations yet"} />
      ) : (
        <ul className="divide-y rounded-lg border">
          {occupations.map((o) => (
            <li key={o.id} className="flex items-center justify-between gap-3 px-4 py-3">
              <span className="font-medium text-foreground">{o.title}</span>
              {o.median_salary != null && (
                <span className="shrink-0 text-sm text-muted-foreground tabular-nums">
                  {formatCurrency(o.median_salary, o.currency ?? "MYR")} median
                </span>
              )}
            </li>
          ))}
        </ul>
      )}
    </BrowserShell>
  );
}

function BrowserShell({
  placeholder,
  draft,
  setDraft,
  onSubmit,
  isFetching,
  children,
}: {
  placeholder: string;
  draft: string;
  setDraft: (v: string) => void;
  onSubmit: () => void;
  isFetching: boolean;
  children: React.ReactNode;
}) {
  return (
    <Card>
      <CardContent className="space-y-4 p-5">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            onSubmit();
          }}
          className="relative max-w-md"
        >
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            placeholder={placeholder}
            className="pl-9"
          />
        </form>
        {isFetching && (
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <Spinner /> Searching…
          </div>
        )}
        {children}
      </CardContent>
    </Card>
  );
}

function BrowserSkeleton() {
  return (
    <div className="flex flex-wrap gap-2">
      {Array.from({ length: 12 }).map((_, i) => (
        <Skeleton key={i} className="h-7 w-24 rounded-full" />
      ))}
    </div>
  );
}

export default function Taxonomy() {
  const { data, isLoading } = useAdminTaxonomy();

  return (
    <div className="animate-fade-in">
      <PageHeader
        eyebrow="Mission Control"
        title="Career Graph taxonomy"
        description="The shared backbone of Atlas — skills, occupations and the transitions that connect them."
      />

      <div className="grid gap-4 sm:grid-cols-3">
        {isLoading ? (
          Array.from({ length: 3 }).map((_, i) => <Skeleton key={i} className="h-28 rounded-xl" />)
        ) : (
          <>
            <StatCard
              label="Skills"
              value={(data?.skills ?? 0).toLocaleString()}
              hint={data?.skill_categories != null ? `${data.skill_categories} categories` : undefined}
              icon={Tags}
              tone="brand"
            />
            <StatCard
              label="Occupations"
              value={(data?.occupations ?? 0).toLocaleString()}
              icon={Briefcase}
            />
            <StatCard
              label="Transitions"
              value={(data?.transitions ?? 0).toLocaleString()}
              hint="Modelled career moves"
              icon={ArrowLeftRight}
            />
          </>
        )}
      </div>

      <div className="mt-8">
        <SectionHeading title="Browse the graph" description="Search live skill and occupation records" />
        <Tabs defaultValue="skills">
          <TabsList>
            <TabsTrigger value="skills">
              <Tags className="h-4 w-4" /> Skills
            </TabsTrigger>
            <TabsTrigger value="occupations">
              <Briefcase className="h-4 w-4" /> Occupations
            </TabsTrigger>
          </TabsList>
          <TabsContent value="skills">
            <SkillsBrowser />
          </TabsContent>
          <TabsContent value="occupations">
            <OccupationsBrowser />
          </TabsContent>
        </Tabs>
      </div>

      {!isLoading && data?.last_updated && (
        <p className="mt-6 flex items-center gap-1.5 text-xs text-muted-foreground">
          <Boxes className="h-3.5 w-3.5" /> Taxonomy last updated{" "}
          {new Date(data.last_updated).toLocaleDateString()}
        </p>
      )}
    </div>
  );
}
