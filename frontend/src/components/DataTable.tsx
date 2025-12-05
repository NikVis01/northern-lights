import { useState, useMemo } from "react";
import { Building2, Landmark, Users, Search, ArrowUpDown, ChevronDown, ExternalLink } from "lucide-react";
import { Button } from "./ui/button";
import { Input } from "./ui/input";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "./ui/table";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "./ui/dropdown-menu";
import { Badge } from "./ui/badge";
import { ScrollArea } from "./ui/scroll-area";
import { useLanguage } from "@/contexts/LanguageContext";
import { useSelectedEntity } from "@/contexts/SelectedEntityContext";

type EntityType = "company" | "fund";
type FilterType = "all" | "companies" | "investors";

interface Entity {
  id: string;
  name: string;
  type: EntityType;
  orgNumber: string;
  sector: string;
  cluster: number;
  ownership?: string;
  country: string;
}

const sampleData: Entity[] = [
  { id: "1", name: "Volvo AB", type: "company", orgNumber: "556012-5790", sector: "Automotive", cluster: 1, ownership: "Geely Holdings (82%)", country: "SE" },
  { id: "2", name: "Geely Holdings", type: "fund", orgNumber: "HK-0175", sector: "Investment", cluster: 1, country: "HK" },
  { id: "3", name: "Spotify AB", type: "company", orgNumber: "556703-7485", sector: "Technology", cluster: 2, ownership: "Tencent (9%)", country: "SE" },
  { id: "4", name: "Tencent Holdings", type: "fund", orgNumber: "HK-0700", sector: "Investment", cluster: 2, country: "HK" },
  { id: "5", name: "Ericsson AB", type: "company", orgNumber: "556016-0680", sector: "Telecom", cluster: 3, ownership: "Investor AB (22%)", country: "SE" },
  { id: "6", name: "Investor AB", type: "fund", orgNumber: "556013-8298", sector: "Investment", cluster: 1, country: "SE" },
  { id: "7", name: "H&M Group", type: "company", orgNumber: "556042-7220", sector: "Retail", cluster: 4, ownership: "Persson Family (45%)", country: "SE" },
  { id: "8", name: "Persson Family", type: "fund", orgNumber: "N/A", sector: "Family Office", cluster: 4, country: "SE" },
  { id: "9", name: "Klarna AB", type: "company", orgNumber: "556737-0431", sector: "FinTech", cluster: 2, ownership: "Sequoia (12%)", country: "SE" },
  { id: "10", name: "Sequoia Capital", type: "fund", orgNumber: "US-SEQ", sector: "Venture Capital", cluster: 2, country: "US" },
  { id: "11", name: "IKEA Holding", type: "company", orgNumber: "556074-7569", sector: "Retail", cluster: 5, ownership: "Stichting INGKA (100%)", country: "SE" },
  { id: "12", name: "Stichting INGKA", type: "fund", orgNumber: "NL-INGKA", sector: "Foundation", cluster: 5, country: "NL" },
  { id: "13", name: "Northvolt AB", type: "company", orgNumber: "559015-8894", sector: "CleanTech", cluster: 3, ownership: "Goldman Sachs (15%)", country: "SE" },
  { id: "14", name: "Goldman Sachs", type: "fund", orgNumber: "US-GS", sector: "Investment Bank", cluster: 3, country: "US" },
  { id: "15", name: "Atlas Copco", type: "company", orgNumber: "556014-2720", sector: "Industrial", cluster: 1, ownership: "Investor AB (17%)", country: "SE" },
  { id: "16", name: "Einride AB", type: "company", orgNumber: "559123-4567", sector: "Autonomous", cluster: 3, country: "SE" },
  { id: "17", name: "Peltarion AB", type: "company", orgNumber: "559234-5678", sector: "AI/ML", cluster: 2, country: "SE" },
  { id: "18", name: "Hedvig AB", type: "company", orgNumber: "559345-6789", sector: "InsurTech", cluster: 2, country: "SE" },
];

type SortField = "name" | "sector" | "cluster" | "country";
type SortDirection = "asc" | "desc";

const DataTable = () => {
  const { t } = useLanguage();
  const { selectedEntityId, setSelectedEntityId } = useSelectedEntity();
  const [filter, setFilter] = useState<FilterType>("all");
  const [searchQuery, setSearchQuery] = useState("");
  const [sortField, setSortField] = useState<SortField>("name");
  const [sortDirection, setSortDirection] = useState<SortDirection>("asc");

  const filteredData = useMemo(() => {
    let data = sampleData;

    if (filter === "companies") {
      data = data.filter((e) => e.type === "company");
    } else if (filter === "investors") {
      data = data.filter((e) => e.type === "fund");
    }

    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      data = data.filter(
        (e) =>
          e.name.toLowerCase().includes(query) ||
          e.sector.toLowerCase().includes(query) ||
          e.orgNumber.toLowerCase().includes(query)
      );
    }

    data = [...data].sort((a, b) => {
      const aVal = a[sortField];
      const bVal = b[sortField];
      if (typeof aVal === "string" && typeof bVal === "string") {
        return sortDirection === "asc"
          ? aVal.localeCompare(bVal)
          : bVal.localeCompare(aVal);
      }
      if (typeof aVal === "number" && typeof bVal === "number") {
        return sortDirection === "asc" ? aVal - bVal : bVal - aVal;
      }
      return 0;
    });

    return data;
  }, [filter, searchQuery, sortField, sortDirection]);

  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortDirection(sortDirection === "asc" ? "desc" : "asc");
    } else {
      setSortField(field);
      setSortDirection("asc");
    }
  };

  const handleRowClick = (entity: Entity) => {
    // Toggle selection - deselect if already selected
    setSelectedEntityId(entity.id === selectedEntityId ? null : entity.id);
  };

  const getFilterLabel = () => {
    switch (filter) {
      case "companies": return t("companies") as string;
      case "investors": return t("investors") as string;
      default: return t("allEntities") as string;
    }
  };

  return (
    <div className="flex flex-col h-full glass-card rounded-lg overflow-hidden">
      {/* Toolbar */}
      <div className="flex items-center justify-between gap-3 p-3 border-b border-border/50">
        <div className="flex items-center gap-2">
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="outline" size="sm" className="gap-2 h-8 text-xs font-mono">
                {getFilterLabel()}
                <ChevronDown className="w-3 h-3 opacity-50" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="start">
              <DropdownMenuItem onClick={() => setFilter("all")}>
                <Users className="w-3.5 h-3.5 mr-2" />
                {t("allEntities") as string}
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => setFilter("companies")}>
                <Building2 className="w-3.5 h-3.5 mr-2" />
                {t("companies") as string}
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => setFilter("investors")}>
                <Landmark className="w-3.5 h-3.5 mr-2" />
                {t("investors") as string}
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>

          <span className="text-xs text-muted-foreground font-mono">
            {filteredData.length} {t("results") as string}
          </span>
        </div>

        <div className="relative flex-1 max-w-[200px]">
          <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-muted-foreground" />
          <Input
            placeholder={t("search") as string}
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-8 h-8 text-xs bg-secondary/50 border-border/50"
          />
        </div>
      </div>

      {/* Table */}
      <ScrollArea className="flex-1">
        <Table>
          <TableHeader className="sticky top-0 bg-card z-10">
            <TableRow className="border-border/30 hover:bg-transparent">
              <TableHead className="w-10 text-muted-foreground text-xs font-mono">{t("type") as string}</TableHead>
              <TableHead>
                <Button variant="ghost" size="sm" className="gap-1 -ml-2 h-7 text-xs font-mono text-muted-foreground hover:text-foreground" onClick={() => handleSort("name")}>
                  {t("name") as string} <ArrowUpDown className="w-3 h-3" />
                </Button>
              </TableHead>
              <TableHead className="text-muted-foreground text-xs font-mono">{t("orgNo") as string}</TableHead>
              <TableHead>
                <Button variant="ghost" size="sm" className="gap-1 -ml-2 h-7 text-xs font-mono text-muted-foreground hover:text-foreground" onClick={() => handleSort("sector")}>
                  {t("sector") as string} <ArrowUpDown className="w-3 h-3" />
                </Button>
              </TableHead>
              <TableHead className="text-muted-foreground text-xs font-mono">{t("cluster") as string}</TableHead>
              <TableHead className="text-muted-foreground text-xs font-mono">{t("ownership") as string}</TableHead>
              <TableHead className="text-muted-foreground text-xs font-mono">{t("country") as string}</TableHead>
              <TableHead className="w-8"></TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {filteredData.map((entity) => (
              <TableRow 
                key={entity.id} 
                className={`border-border/20 cursor-pointer group transition-colors ${
                  selectedEntityId === entity.id 
                    ? "bg-primary/10 hover:bg-primary/15" 
                    : "hover:bg-secondary/30"
                }`}
                onClick={() => handleRowClick(entity)}
              >
                <TableCell>
                  <div className={`w-5 h-5 rounded flex items-center justify-center ${entity.type === "fund" ? "bg-muted-foreground/20" : "bg-foreground/10"}`}>
                    {entity.type === "fund" ? (
                      <Landmark className="w-3 h-3 text-muted-foreground" />
                    ) : (
                      <Building2 className="w-3 h-3 text-foreground/70" />
                    )}
                  </div>
                </TableCell>
                <TableCell className="font-medium text-foreground text-sm">{entity.name}</TableCell>
                <TableCell className="font-mono text-xs text-muted-foreground">{entity.orgNumber}</TableCell>
                <TableCell>
                  <Badge variant="secondary" className="text-xs font-normal bg-secondary/50">{entity.sector}</Badge>
                </TableCell>
                <TableCell className="font-mono text-xs text-muted-foreground">#{entity.cluster}</TableCell>
                <TableCell className="text-xs text-muted-foreground">{entity.ownership || "—"}</TableCell>
                <TableCell>
                  <Badge variant="outline" className="text-xs font-mono">{entity.country}</Badge>
                </TableCell>
                <TableCell>
                  <Button 
                    variant="ghost" 
                    size="icon" 
                    className="w-6 h-6 opacity-0 group-hover:opacity-100 transition-opacity"
                    onClick={(e) => e.stopPropagation()}
                  >
                    <ExternalLink className="w-3 h-3" />
                  </Button>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </ScrollArea>
    </div>
  );
};

export default DataTable;
