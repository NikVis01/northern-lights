import { Activity, User, Settings, LogOut, Globe, ChevronDown, Check } from "lucide-react";
import { Button } from "./ui/button";
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
import { ThemeToggle } from "./ThemeToggle";
import { useLanguage } from "@/contexts/LanguageContext";

const Header = () => {
  const { language, setLanguage, t } = useLanguage();

  const handleLogout = () => {
    // TODO: Implement actual logout with Supabase
    console.log("Logout clicked");
  };

  return (
    <header className="fixed top-0 left-0 right-0 z-50 border-b border-border/50 bg-background/90 backdrop-blur-sm">
      <div className="container mx-auto px-6 h-14 flex items-center justify-between">
        <div className="flex items-center gap-2">
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
          <div className="hidden sm:flex items-center gap-2 text-xs text-muted-foreground">
            <Activity className="w-3 h-3" />
            <span className="font-mono">{t("live") as string}</span>
          </div>
          
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
