import Header from "@/components/DashboardHeader";
import NetworkGraph from "@/components/NetworkGraph";
import DataTable from "@/components/DataTable";
import ChatPanel from "@/components/ChatPanel";
import { useLanguage } from "@/contexts/LanguageContext";
import { useState } from "react";
import { ChevronUp, ChevronDown } from "lucide-react";

const Index = () => {
  const { t } = useLanguage();
  const [isPanelsOpen, setIsPanelsOpen] = useState(true);

  return (
    <div className="h-screen flex flex-col bg-background overflow-hidden">
      <Header />

      <main className="relative flex-1 pt-14 flex flex-col min-h-0">
        {/* Network Graph - Full height, behind overlay */}
        <section 
          id="graph" 
          className="flex-1 p-4 min-h-0 relative z-0"
        >
          <div className="h-full glass-card rounded-lg p-3 flex flex-col">
            <div className="flex items-center justify-between mb-2">
              <div>
                <span className="font-mono text-xs tracking-wider uppercase text-muted-foreground">
                  {t("liveNetwork") as string}
                </span>
                <h2 className="text-lg font-semibold text-foreground -mt-0.5">
                  {t("ownershipGraph") as string}
                </h2>
              </div>
              <span className="font-mono text-xs text-muted-foreground">
                {t("hoverToExplore") as string}
              </span>
            </div>
            <div className="flex-1 min-h-0">
              <NetworkGraph isPanelsOpen={isPanelsOpen} />
            </div>
            {/* Hint texts at bottom */}
            <div className="flex items-center justify-between mt-2 pt-2 border-t border-border/40">
              <span className="font-mono text-xs text-muted-foreground">
                {t("liveNetwork") as string}
              </span>
              <span className="font-mono text-xs text-muted-foreground">
                {t("hoverToExplore") as string}
              </span>
            </div>
          </div>
        </section>

        {/* Collapsible Panels Overlay - Higher z-index to float above graph */}
        <div 
          className={`absolute bottom-0 left-0 right-0 transition-all duration-300 ease-out z-10 ${
            isPanelsOpen 
              ? "translate-y-0 opacity-100 pointer-events-auto" 
              : "translate-y-full opacity-0 pointer-events-none"
          }`}
          style={{
            height: "50%",
            top: "auto",
          }}
        >
          {/* Collapse Button - Center Top of Panels */}
          <div className="flex justify-center absolute -top-8 left-0 right-0 z-20">
            <button
              onClick={() => setIsPanelsOpen(false)}
              className="p-2 hover:bg-muted rounded-full transition-colors bg-background/90 backdrop-blur-sm border border-border/40"
              title="Collapse panels"
            >
              <ChevronUp className="w-5 h-5" />
            </button>
          </div>

          {/* Panels Content */}
          <div className="h-full p-4 pt-2 flex flex-col gap-4 bg-background/95 backdrop-blur-sm border-t border-border/40">
            {/* Data Table and Chat Panel - Flex container */}
            <div className="flex-1 min-h-0 flex gap-4">
              {/* 75% - Data Table */}
              <div className="w-3/4 min-w-0">
                <DataTable />
              </div>

              {/* 25% - Chat Panel */}
              <div id="chat" className="w-1/4 min-w-[260px]">
                <ChatPanel />
              </div>
            </div>
          </div>
        </div>

        {/* Bottom Tab - Show when collapsed */}
        {!isPanelsOpen && (
          <div className="absolute bottom-0 left-0 right-0 h-12 p-2 border-t border-border/40 flex justify-center items-center bg-background/90 backdrop-blur-sm z-10">
            <button
              onClick={() => setIsPanelsOpen(true)}
              className="flex items-center gap-2 px-3 py-1 bg-muted hover:bg-muted/80 rounded text-sm transition-colors"
            >
              <ChevronDown className="w-4 h-4" />
              Show Panels
            </button>
          </div>
        )}
      </main>
    </div>
  );
};

export default Index;
