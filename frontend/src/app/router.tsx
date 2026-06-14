import { lazy } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import { RequireAuth } from "./RequireAuth";
import { AppShell } from "./AppShell";

// Public
const LandingPage = lazy(() => import("@/features/marketing/LandingPage"));
const LoginPage = lazy(() => import("@/features/auth/LoginPage"));
const RegisterPage = lazy(() => import("@/features/auth/RegisterPage"));
const NotFound = lazy(() => import("@/features/marketing/NotFound"));

// Candidate · Navigator
const CandidateDashboard = lazy(() => import("@/features/candidate/pages/Dashboard"));
const TrajectoryAtlas = lazy(() => import("@/features/candidate/pages/TrajectoryAtlas"));
const CareerCopilot = lazy(() => import("@/features/candidate/pages/CareerCopilot"));
const CareerWeather = lazy(() => import("@/features/candidate/pages/CareerWeather"));
const JobDiscovery = lazy(() => import("@/features/candidate/pages/JobDiscovery"));
const JobDetail = lazy(() => import("@/features/candidate/pages/JobDetail"));
const Applications = lazy(() => import("@/features/candidate/pages/Applications"));
const FairPay = lazy(() => import("@/features/candidate/pages/FairPay"));
const ProfileBuilder = lazy(() => import("@/features/candidate/pages/ProfileBuilder"));
const LivingPortfolio = lazy(() => import("@/features/candidate/pages/LivingPortfolio"));
const LifeChapters = lazy(() => import("@/features/candidate/pages/LifeChapters"));
const LearningWallet = lazy(() => import("@/features/candidate/pages/LearningWallet"));
const ConsentCenter = lazy(() => import("@/features/candidate/pages/ConsentCenter"));

// Employer · Talent Radar
const EmployerDashboard = lazy(() => import("@/features/employer/pages/Dashboard"));
const TalentSearch = lazy(() => import("@/features/employer/pages/TalentSearch"));
const EmployerJobs = lazy(() => import("@/features/employer/pages/Jobs"));
const Pipeline = lazy(() => import("@/features/employer/pages/Pipeline"));
const RetentionSignals = lazy(() => import("@/features/employer/pages/RetentionSignals"));
const ReEngagement = lazy(() => import("@/features/employer/pages/ReEngagement"));
const OnboardingRisk = lazy(() => import("@/features/employer/pages/OnboardingRisk"));
const WorkforceResilience = lazy(() => import("@/features/employer/pages/WorkforceResilience"));

// University · Outcomes Studio
const UniversityDashboard = lazy(() => import("@/features/university/pages/Dashboard"));
const OutcomeLoop = lazy(() => import("@/features/university/pages/OutcomeLoop"));
const Students = lazy(() => import("@/features/university/pages/Students"));
const ReadinessProfiles = lazy(() => import("@/features/university/pages/ReadinessProfiles"));
const CurriculumEngine = lazy(() => import("@/features/university/pages/CurriculumEngine"));
const Internships = lazy(() => import("@/features/university/pages/Internships"));
const Credentials = lazy(() => import("@/features/university/pages/Credentials"));

// Admin · Mission Control
const AdminOverview = lazy(() => import("@/features/admin/pages/Overview"));
const AdminTenants = lazy(() => import("@/features/admin/pages/Tenants"));
const AdminUsers = lazy(() => import("@/features/admin/pages/Users"));
const AdminTaxonomy = lazy(() => import("@/features/admin/pages/Taxonomy"));
const AdminAiUsage = lazy(() => import("@/features/admin/pages/AiUsage"));
const AdminAudit = lazy(() => import("@/features/admin/pages/Audit"));

export function AppRoutes() {
  return (
    <Routes>
      {/* Public */}
      <Route path="/" element={<LandingPage />} />
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />

      {/* Candidate workspace */}
      <Route
        path="/app"
        element={
          <RequireAuth roles={["candidate"]}>
            <AppShell />
          </RequireAuth>
        }
      >
        <Route index element={<CandidateDashboard />} />
        <Route path="atlas" element={<TrajectoryAtlas />} />
        <Route path="coach" element={<CareerCopilot />} />
        <Route path="weather" element={<CareerWeather />} />
        <Route path="jobs" element={<JobDiscovery />} />
        <Route path="jobs/:jobId" element={<JobDetail />} />
        <Route path="applications" element={<Applications />} />
        <Route path="pay" element={<FairPay />} />
        <Route path="profile" element={<ProfileBuilder />} />
        <Route path="portfolio" element={<LivingPortfolio />} />
        <Route path="life-chapters" element={<LifeChapters />} />
        <Route path="wallet" element={<LearningWallet />} />
        <Route path="consent" element={<ConsentCenter />} />
      </Route>

      {/* Employer workspace */}
      <Route
        path="/employer"
        element={
          <RequireAuth roles={["employer_recruiter", "employer_admin"]}>
            <AppShell />
          </RequireAuth>
        }
      >
        <Route index element={<EmployerDashboard />} />
        <Route path="candidates" element={<TalentSearch />} />
        <Route path="jobs" element={<EmployerJobs />} />
        <Route path="pipeline" element={<Pipeline />} />
        <Route path="retention" element={<RetentionSignals />} />
        <Route path="reengage" element={<ReEngagement />} />
        <Route path="onboarding" element={<OnboardingRisk />} />
        <Route path="workforce" element={<WorkforceResilience />} />
      </Route>

      {/* University workspace */}
      <Route
        path="/university"
        element={
          <RequireAuth roles={["university_staff", "university_admin"]}>
            <AppShell />
          </RequireAuth>
        }
      >
        <Route index element={<UniversityDashboard />} />
        <Route path="outcomes" element={<OutcomeLoop />} />
        <Route path="students" element={<Students />} />
        <Route path="readiness" element={<ReadinessProfiles />} />
        <Route path="curriculum" element={<CurriculumEngine />} />
        <Route path="internships" element={<Internships />} />
        <Route path="credentials" element={<Credentials />} />
      </Route>

      {/* Admin workspace */}
      <Route
        path="/admin"
        element={
          <RequireAuth roles={["platform_admin"]}>
            <AppShell />
          </RequireAuth>
        }
      >
        <Route index element={<AdminOverview />} />
        <Route path="tenants" element={<AdminTenants />} />
        <Route path="users" element={<AdminUsers />} />
        <Route path="taxonomy" element={<AdminTaxonomy />} />
        <Route path="ai-usage" element={<AdminAiUsage />} />
        <Route path="audit" element={<AdminAudit />} />
      </Route>

      <Route path="/404" element={<NotFound />} />
      <Route path="*" element={<Navigate to="/404" replace />} />
    </Routes>
  );
}
