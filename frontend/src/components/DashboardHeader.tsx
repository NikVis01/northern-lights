import { Activity, User, Settings, LogOut, Globe, ChevronDown, Check, AlertCircle } from "lucide-react";
import { Button } from "./ui/button";
import { useNavigate } from "react-router-dom";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
  DropdownMenuSub,
  DropdownMenuSubTrigger,
  DropdownMenuSubContent,
} from "./ui/dropdown-menu";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "./ui/tooltip";
import { ThemeToggle } from "./ThemeToggle";
import { useLanguage } from "@/contexts/LanguageContext";
import { useBackendHealth } from "@/hooks/useBackendHealth";

const Header = () => {
  const navigate = useNavigate();
  const { language, setLanguage, t } = useLanguage();
  const { isHealthy, lastChecked } = useBackendHealth();

  const handleLogout = () => {
    // TODO: Implement actual logout with Supabase
    console.log("Logout clicked");
    window.location.href = "/";
  };

  const formatTimestamp = (date: Date | null) => {
    if (!date) return "";
    return date.toLocaleTimeString('en-US', { 
      hour: '2-digit', 
      minute: '2-digit', 
      second: '2-digit',
      hour12: false 
    });
  };

  return (
    <header className="fixed top-0 left-0 right-0 z-50 border-b border-border/50 bg-background/90 backdrop-blur-sm">
      <div className="container mx-auto px-6 h-14 flex items-center justify-between">
        <div 
          onClick={() => navigate("/")}
          className="flex items-center gap-2 hover:opacity-80 transition-opacity cursor-pointer"
        >
          <div className="w-2 h-2 rounded-full bg-foreground" />
          <span className="font-mono text-sm tracking-wider uppercase text-foreground">
            Northern Lights
          </span>
        </div>

        <nav className="hidden md:flex items-center gap-8">
          <a href="#graph" className="text-sm text-muted-foreground hover:text-foreground transition-colors">
            {t("network") as string}
          </a>
          <a href="#data" className="text-sm text-muted-foreground hover:text-foreground transition-colors">
            {t("data") as string}
          </a>
          <a href="#chat" className="text-sm text-muted-foreground hover:text-foreground transition-colors">
            {t("agent") as string}
          </a>
        </nav>

        <div className="flex items-center gap-3">
          {/* Connection Status */}
          <TooltipProvider>
            <Tooltip>
              <TooltipTrigger asChild>
                <div className={`hidden sm:flex items-center gap-2 text-xs font-mono cursor-help ${isHealthy ? "text-green-500" : "text-destructive"}`}>
                  {isHealthy ? (
                    <>
                      <Activity className="w-3 h-3" />
                      <span>LIVE</span>
                    </>
                  ) : (
                    <>
                      <AlertCircle className="w-3 h-3" />
                      <span>ERROR</span>
                    </>
                  )}
                </div>
              </TooltipTrigger>
              <TooltipContent>
                {isHealthy ? (
                  <p className="text-xs">
                    Connected: {formatTimestamp(lastChecked)} last updated
                  </p>
                ) : (
                  <p className="text-xs">
                    Couldn't connect to backend, please contact administration
                  </p>
                )}
              </TooltipContent>
            </Tooltip>
          </TooltipProvider>
          
          <ThemeToggle />

          {/* Account Dropdown */}
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="outline" size="sm" className="gap-2">
                <User className="h-4 w-4" />
                <span className="hidden sm:inline">{t("account") as string}</span>
                <ChevronDown className="h-3 w-3 opacity-50" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-48 bg-popover border-border">
              <DropdownMenuItem className="gap-2 cursor-pointer">
                <Settings className="h-4 w-4" />
                {t("settings") as string}
              </DropdownMenuItem>
              
              <DropdownMenuSub>
                <DropdownMenuSubTrigger className="gap-2 cursor-pointer">
                  <Globe className="h-4 w-4" />
                  {t("language") as string}
                </DropdownMenuSubTrigger>
                <DropdownMenuSubContent className="bg-popover border-border">
                  <DropdownMenuItem 
                    className="cursor-pointer justify-between"
                    onClick={() => setLanguage("en")}
                  >
                    {t("english") as string}
                    {language === "en" && <Check className="h-4 w-4" />}
                  </DropdownMenuItem>
                  <DropdownMenuItem 
                    className="cursor-pointer justify-between"
                    onClick={() => setLanguage("sv")}
                  >
                    {t("swedish") as string}
                    {language === "sv" && <Check className="h-4 w-4" />}
                  </DropdownMenuItem>
                </DropdownMenuSubContent>
              </DropdownMenuSub>
              
              <DropdownMenuSeparator />
              
              <DropdownMenuItem 
                className="gap-2 cursor-pointer text-destructive focus:text-destructive"
                onClick={handleLogout}
              >
                <LogOut className="h-4 w-4" />
                {t("logout") as string}
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </div>
    </header>
  );
};

export default Header;
