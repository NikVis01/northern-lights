import Header from "@/components/DashboardHeader";
import NetworkGraph from "@/components/NetworkGraph";
import DataTable from "@/components/DataTable";
import ChatPanel from "@/components/ChatPanel";
import { useLanguage } from "@/contexts/LanguageContext";

const Index = () => {
  const { t } = useLanguage();

  return (
    <div className="h-screen flex flex-col bg-background overflow-hidden">
      <Header />

      <main className="relative flex-1 pt-14 flex flex-col min-h-0">
        {/* Top Half: Network Graph */}
        <section id="graph" className="h-1/2 p-4 pb-2">
          <div className="h-full glass-card rounded-lg p-3">
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
            <div className="h-[calc(100%-48px)]">
              <NetworkGraph />
            </div>
          </div>
        </section>

        {/* Bottom Half: 75/25 Split */}
        <section id="data" className="h-1/2 p-4 pt-2 flex gap-4">
          {/* 75% - Data Table */}
          <div className="w-3/4 min-w-0">
            <DataTable />
          </div>

          {/* 25% - Chat Panel */}
          <div id="chat" className="w-1/4 min-w-[260px]">
            <ChatPanel />
          </div>
        </section>
      </main>
    </div>
  );
};

export default Index;
