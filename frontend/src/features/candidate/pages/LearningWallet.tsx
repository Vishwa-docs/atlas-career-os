import { ModulePreview } from "@/components/module-preview";

export default function LearningWallet() {
  return (
    <ModulePreview
      eyebrow="Learning Wallet"
      title="Verifiable credentials wallet"
      description="A tamper-evident wallet for the credentials, courses, and micro-certifications you earn — portable across employers and universities, and verifiable in one tap."
      capabilities={[
        "Hold verifiable credentials issued by universities and training partners",
        "Cryptographic proof of authenticity — no PDF screenshots",
        "Share a credential or a verifiable link with any employer",
        "Auto-map credentials to skills in your Career Graph",
        "Track expiring certifications and renewal nudges",
        "Selective disclosure — reveal only what a role requires",
      ]}
      tier="C"
    />
  );
}
