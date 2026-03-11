import { NavSection }      from "@/components/sections/nav-section"
import { HeroSection }     from "@/components/sections/hero-section"
import { SocialSection }   from "@/components/sections/social-section"
import { CopilotSection }  from "@/components/sections/copilot-section"
import { FeaturesSection } from "@/components/sections/features-section"
import { PricingSection }  from "@/components/sections/pricing-section"
import { FooterSection }   from "@/components/sections/footer-section"

export default function LandingPage() {
  return (
    <>
      <style>{`
        *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
        html { scroll-behavior: smooth; }
        body { font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display", "Helvetica Neue", Arial, sans-serif; background: #000; -webkit-font-smoothing: antialiased; moz-osx-font-smoothing: grayscale; overflow-x: hidden; }
        .tw-cursor { animation: twBlink 1.05s step-end infinite; }
        @keyframes twBlink { 0%, 100% { opacity: 1; } 50% { opacity: 0; } }
        @keyframes ttIn { from { opacity: 0; transform: translateX(-50%) translateY(6px); } to { opacity: 1; transform: translateX(-50%) translateY(0); } }
        @keyframes orbDrift { from { transform: translate(0,0) scale(1); } to { transform: translate(20px,-30px) scale(1.08); } }
        @keyframes scrollGrow { 0%, 100% { transform: scaleY(1); opacity: 0.3; } 50% { transform: scaleY(1.3); opacity: 1; } }
      `}</style>
      <NavSection />
      <main>
        <HeroSection />
        <SocialSection />
        <CopilotSection />
        <FeaturesSection />
        <PricingSection />
      </main>
      <FooterSection />
    </>
  );
}
