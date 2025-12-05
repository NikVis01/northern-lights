import { Button } from "@/components/ui/button";
import { useLanguage } from "@/contexts/LanguageContext";

export function LanguageToggle() {
  const { language, setLanguage } = useLanguage();

  return (
    <Button
      variant="outline"
      size="sm"
      onClick={() => setLanguage(language === "en" ? "sv" : "en")}
      className="font-mono text-xs border-border/50 bg-background/30 hover:bg-background/50 w-10"
    >
      {language === "en" ? "SV" : "EN"}
    </Button>
  );
}
