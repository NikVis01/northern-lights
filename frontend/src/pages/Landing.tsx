import { ArrowRight, Database, Network, Zap, Shield, Search, TrendingUp } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { ThemeToggle } from "@/components/ThemeToggle";
import { LanguageToggle } from "@/components/LanguageToggle";
import { useLanguage } from "@/contexts/LanguageContext";
import NetworkGraph from "@/components/LandingGraph";

const Index = () => {
  const { t } = useLanguage();
  const navigate = useNavigate();

  // ... (rest of the component)

  // In the header button:
  // <Button 
  //   variant="outline" 
  //   size="sm" 
  //   className="font-mono text-xs border-border/50 bg-background/30 hover:bg-background/50"
  //   onClick={() => navigate("/dashboard")}
  // >
  //   {t("nav.requestAccess")}
  // </Button>

  const features = [
    {
      icon: Network,
      titleKey: "features.ownership.title",
      descKey: "features.ownership.desc",
    },
    {
      icon: Search,
      titleKey: "features.mapping.title",
      descKey: "features.mapping.desc",
    },
    {
      icon: TrendingUp,
      titleKey: "features.leads.title",
      descKey: "features.leads.desc",
    },
    {
      icon: Database,
      titleKey: "features.database.title",
      descKey: "features.database.desc",
    },
    {
      icon: Zap,
      titleKey: "features.api.title",
      descKey: "features.api.desc",
    },
    {
      icon: Shield,
      titleKey: "features.security.title",
      descKey: "features.security.desc",
    },
  ];

  const stats = [
    { value: "100K+", labelKey: "stats.entities" },
    { value: "SE", labelKey: "stats.scope" },
    { value: "<100ms", labelKey: "stats.response" },
    { value: t("stats.realtime"), labelKey: "stats.updates" },
  ];

  const archItems = [
    { labelKey: "arch.data.label", valueKey: "arch.data.value" },
    { labelKey: "arch.intelligence.label", valueKey: "arch.intelligence.value" },
    { labelKey: "arch.clustering.label", valueKey: "arch.clustering.value" },
    { labelKey: "arch.delivery.label", valueKey: "arch.delivery.value" },
  ];

  return (
    <div className="relative min-h-screen navy-gradient overflow-hidden">
      {/* Grain overlay */}
      <div className="grain-overlay" />
      
      {/* Grid pattern */}
      <div className="fixed inset-0 grid-pattern opacity-50" />
      
      {/* Gradient overlays for depth */}
      <div className="fixed inset-0 bg-gradient-to-b from-transparent via-background/50 to-background/50" />
      
      {/* Content */}
      <div className="relative z-10">
        {/* Header */}
        <header className="border-b border-border/40 backdrop-blur-sm bg-background/20">
          <div className="container flex h-16 items-center justify-between">
            <div className="flex items-center gap-2">
              <div className="h-2 w-2 rounded-full bg-foreground animate-pulse" />
              <span className="font-mono text-sm tracking-widest uppercase">Northern Lights</span>
            </div>
            <nav className="hidden md:flex items-center gap-8">
              <a href="#graph" className="text-sm text-muted-foreground hover:text-foreground transition-colors">{t("nav.network")}</a>
              <a href="#features" className="text-sm text-muted-foreground hover:text-foreground transition-colors">{t("nav.features")}</a>
              <a href="#architecture" className="text-sm text-muted-foreground hover:text-foreground transition-colors">{t("nav.architecture")}</a>
            </nav>
            <div className="flex items-center gap-3">
              <LanguageToggle />
              <ThemeToggle />
              {/* Push to /dashboard */}
              <Button 
                variant="outline" 
                size="sm" 
                className="font-mono text-xs border-border/50 bg-background/30 hover:bg-background/50"
                onClick={() => navigate("/dashboard")}
              >
                {t("nav.requestAccess")}
              </Button>
            </div>
          </div>
        </header>

        {/* Hero */}
        <section className="container py-24 md:py-32">
          <div className="max-w-4xl">
            <div className="opacity-0 animate-fade-up">
              <p className="font-mono text-xs text-muted-foreground tracking-widest uppercase mb-6">
                {t("hero.subtitle")}
              </p>
            </div>
            
            <h1 className="opacity-0 animate-fade-up animate-delay-100 text-4xl md:text-6xl lg:text-7xl font-light tracking-tight leading-[1.1] mb-8 text-glow">
              {t("hero.title1")}
              <span className="block font-medium">{t("hero.title2")}</span>
            </h1>
            
            <p className="opacity-0 animate-fade-up animate-delay-200 text-lg md:text-xl text-muted-foreground max-w-2xl mb-12 leading-relaxed">
              {t("hero.description")}
            </p>
            
            <div className="opacity-0 animate-fade-up animate-delay-300 flex flex-col sm:flex-row gap-4">
              <Button size="lg" className="font-mono text-sm group">
                {t("hero.exploreGraph")}
                <ArrowRight className="ml-2 h-4 w-4 group-hover:translate-x-1 transition-transform" />
              </Button>
              <Button variant="outline" size="lg" className="font-mono text-sm border-border/50 bg-background/20 hover:bg-background/40">
                {t("hero.viewDocs")}
              </Button>
            </div>
          </div>
        </section>

        {/* Interactive Graph Visualization */}
        <section id="graph" className="relative border-y border-border/40">
          <div className="absolute inset-0 bg-gradient-to-b from-transparent via-card/30 to-transparent" />
          <div className="container py-16">
            <div className="mb-8">
              <p className="font-mono text-xs text-muted-foreground tracking-widest uppercase mb-4">{t("graph.subtitle")}</p>
              <h2 className="text-2xl md:text-3xl font-light">{t("graph.title")}</h2>
            </div>
            
            <div className="relative rounded-lg border border-border/40 bg-card/20 backdrop-blur-sm overflow-hidden">
              {/* Decorative corner elements */}
              <div className="absolute top-0 left-0 w-8 h-8 border-l-2 border-t-2 border-foreground/20" />
              <div className="absolute top-0 right-0 w-8 h-8 border-r-2 border-t-2 border-foreground/20" />
              <div className="absolute bottom-0 left-0 w-8 h-8 border-l-2 border-b-2 border-foreground/20" />
              <div className="absolute bottom-0 right-0 w-8 h-8 border-r-2 border-b-2 border-foreground/20" />
              
              <NetworkGraph />
            </div>
          </div>
        </section>

        {/* Stats */}
        <section className="border-b border-border/40">
          <div className="container grid grid-cols-2 md:grid-cols-4 divide-x divide-border/40">
            {stats.map((stat, i) => (
              <div key={i} className="py-12 px-6 text-center">
                <p className="font-mono text-3xl md:text-4xl font-medium mb-2">{stat.value}</p>
                <p className="text-xs text-muted-foreground uppercase tracking-widest">{t(stat.labelKey)}</p>
              </div>
            ))}
          </div>
        </section>

        {/* Features */}
        <section id="features" className="container py-32">
          <div className="mb-16">
            <p className="font-mono text-xs text-muted-foreground tracking-widest uppercase mb-4">{t("features.subtitle")}</p>
            <h2 className="text-3xl md:text-4xl font-light">{t("features.title")}</h2>
          </div>
          
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-px bg-border/30 rounded-lg overflow-hidden">
            {features.map((feature, i) => (
              <div 
                key={i} 
                className="bg-card/40 backdrop-blur-sm p-8 md:p-12 group hover:bg-card/60 transition-all duration-300"
              >
                <feature.icon className="h-5 w-5 text-muted-foreground mb-6 group-hover:text-foreground transition-colors" />
                <h3 className="text-lg font-medium mb-3">{t(feature.titleKey)}</h3>
                <p className="text-sm text-muted-foreground leading-relaxed">{t(feature.descKey)}</p>
              </div>
            ))}
          </div>
        </section>

        {/* Architecture */}
        <section id="architecture" className="border-t border-border/40">
          <div className="container py-32">
            <div className="mb-16">
              <p className="font-mono text-xs text-muted-foreground tracking-widest uppercase mb-4">{t("arch.subtitle")}</p>
              <h2 className="text-3xl md:text-4xl font-light">{t("arch.title")}</h2>
            </div>
            
            <div className="grid lg:grid-cols-2 gap-16">
              <div className="space-y-8">
                {archItems.map((item, i) => (
                  <div key={i} className="border-l-2 border-border/60 pl-6 py-2 hover:border-foreground/50 transition-colors">
                    <p className="font-mono text-s uppercase tracking-widest mb-2"><strong>{t(item.labelKey)}</strong></p>
                    <p className="text-foreground">{t(item.valueKey)}</p>
                  </div>
                ))}
              </div>
              
              <div className="bg-card/30 border border-border/40 rounded-lg p-8 font-mono text-xs backdrop-blur-sm">
                <pre className="overflow-x-auto">
{`┌─────────────────────────────────────┐
│     Cloud Endpoints (API Keys)      │
└─────────────────────────────────────┘
                    │
┌─────────────────────────────────────┐
│    Cloud Run (FastAPI Backend)      │
│  ┌────────┐ ┌────────┐ ┌────────┐   │
│  │/search │ │/leads  │ │/company│   │
│  └────────┘ └────────┘ └────────┘   │
└─────────────────────────────────────┘
                    │
┌─────────────────────────────────────┐
│         Neo4j Aura DB               │
│  ┌─────────┐    ┌──────────────┐    │
│  │ Graph   │    │ Vector Index │    │
│  │ Store   │    │ + Leiden     │    │
│  └─────────┘    └──────────────┘    │
└─────────────────────────────────────┘`}
                </pre>
              </div>
            </div>
          </div>
        </section>

        {/* CTA */}
        <section className="border-t border-border/40">
          <div className="container py-32 text-center">
            <h2 className="text-3xl md:text-4xl font-light mb-6">
              {t("cta.title")}
            </h2>
            <p className="text-muted-foreground mb-12 max-w-xl mx-auto">
              {t("cta.description")}
            </p>
            <Button size="lg" className="font-mono text-sm">
              {t("cta.button")}
              <ArrowRight className="ml-2 h-4 w-4" />
            </Button>
          </div>
        </section>

        {/* Footer */}
        <footer className="border-t border-border/40">
          <div className="container py-12 flex flex-col md:flex-row justify-between items-center gap-6">
            <div className="flex items-center gap-2">
              <div className="h-1.5 w-1.5 rounded-full bg-foreground" />
              <span className="font-mono text-xs tracking-widest uppercase">Northern Lights</span>
            </div>
            <p className="text-xs text-muted-foreground">
              {t("footer.tagline")}
            </p>
          </div>
        </footer>
      </div>
    </div>
  );
};

export default Index;
