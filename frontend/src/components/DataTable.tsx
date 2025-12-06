import { useState, useMemo, useEffect } from "react";
import { Building2, Landmark, Users, Search, ArrowUpDown, ChevronDown, ExternalLink, AlertCircle, Copy } from "lucide-react";
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
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "./ui/tooltip";
import { useBackendHealth } from "@/hooks/useBackendHealth";
import { getBackendUrl } from "@/lib/api";

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
  website?: string;
}



type SortField = "name" | "sector" | "cluster" | "country";
type SortDirection = "asc" | "desc";

const DataTable = () => {
  const { t } = useLanguage();
  const { selectedEntityId, setSelectedEntityId } = useSelectedEntity();
  const { isHealthy } = useBackendHealth();
  const [filter, setFilter] = useState<FilterType>("all");
  const [searchQuery, setSearchQuery] = useState("");
  const [sortField, setSortField] = useState<SortField>("name");
  const [sortDirection, setSortDirection] = useState<SortDirection>("asc");
  const [entities, setEntities] = useState<Entity[]>([]);
  const [hasError, setHasError] = useState(false);

  useEffect(() => {
    const fetchEntities = async () => {
      try {
        setHasError(false);
        const response = await fetch(getBackendUrl("/api/v1/search/all"), {
          headers: {
            "access_token": "dev"
          }
        });
        
        if (response.ok) {
          const { nodes, links } = await response.json();
          
          // Map for lookup
          const nodeMap = new Map<string, any>(nodes.map((n: any) => [n.id, n]));
          
          const processedEntities = nodes.map((node: any) => {
            const nodeLinks = links.filter((l: any) => l.target === node.id);
            const ownership = nodeLinks.map((l: any) => {
              const sourceName = nodeMap.get(l.source)?.name || "Unknown";
              return `${sourceName} (${l.ownership}%)`;
            }).join(", ");
            
            return {
              id: node.id,
              name: node.name,
              type: node.type,
              orgNumber: node.orgNumber || "-",
              sector: node.sector && node.sector !== "Unknown" ? node.sector : "—",
              cluster: node.cluster || 0,
              country: node.country || "Unknown",
              ownership: ownership || undefined,
              website: node.website || undefined
            };
          });
          setEntities(processedEntities);
        } else {
          setHasError(true);
        }
      } catch (error) {
        console.error("Failed to fetch entities:", error);
        setHasError(true);
      }
    };

    fetchEntities();
  }, []);

  // Refetch when backend comes back online
  useEffect(() => {
    if (isHealthy && hasError) {
      console.log("Backend is back online, refetching table data...");
      const fetchEntities = async () => {
        try {
          setHasError(false);
          const response = await fetch(getBackendUrl("/api/v1/search/all"), {
            headers: {
              "access_token": "dev"
            }
          });
          
          if (response.ok) {
            const { nodes, links } = await response.json();
            
            const nodeMap = new Map<string, any>(nodes.map((n: any) => [n.id, n]));
            
            const processedEntities = nodes.map((node: any) => {
              const nodeLinks = links.filter((l: any) => l.target === node.id);
              const ownership = nodeLinks.map((l: any) => {
                const sourceName = nodeMap.get(l.source)?.name || "Unknown";
                return `${sourceName} (${l.ownership}%)`;
              }).join(", ");
              
              return {
                id: node.id,
                name: node.name,
                type: node.type,
                orgNumber: node.orgNumber || "-",
                sector: node.sector && node.sector !== "Unknown" ? node.sector : "—",
                cluster: node.cluster || 0,
                country: node.country || "Unknown",
                ownership: ownership || undefined
              };
            });
            setEntities(processedEntities);
          } else {
            setHasError(true);
          }
        } catch (error) {
          console.error("Failed to fetch entities:", error);
          setHasError(true);
        }
      };

      fetchEntities();
    }
  }, [isHealthy, hasError]);

  const filteredData = useMemo(() => {
    let data = entities;

    if (filter === "companies") {
      data = data.filter((e) => e.type === "company");
    } else if (filter === "investors") {
      data = data.filter((e) => e.type === "fund");
    }

    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      data = data.filter(
        (e) =>
          (e.name && e.name.toLowerCase().includes(query)) ||
          (e.sector && e.sector.toLowerCase().includes(query)) ||
          (e.orgNumber && e.orgNumber.toLowerCase().includes(query))
      );
    }

    data = [...data].sort((a, b) => {
      const aVal = a[sortField] || "";
      const bVal = b[sortField] || "";
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
  }, [entities, filter, searchQuery, sortField, sortDirection]);

  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortDirection(sortDirection === "asc" ? "desc" : "asc");
    } else {
      setSortField(field);
      setSortDirection("asc");
    }
  };

  const handleCopy = (text: string, e: React.MouseEvent) => {
    e.stopPropagation();
    navigator.clipboard.writeText(text);
    
    // Simple toast notification
    const toast = document.createElement('div');
    toast.className = 'fixed bottom-4 right-4 bg-primary text-primary-foreground px-4 py-2 rounded-lg shadow-lg z-50 animate-in fade-in slide-in-from-bottom-2';
    toast.textContent = 'Copied to clipboard!';
    document.body.appendChild(toast);
    setTimeout(() => {
      toast.classList.add('animate-out', 'fade-out', 'slide-out-to-bottom-2');
      setTimeout(() => document.body.removeChild(toast), 200);
    }, 2000);
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
    <div className="flex flex-col h-full glass-card rounded-lg overflow-hidden relative">
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

      {/* Error Overlay */}
      {hasError && (
        <div className="absolute inset-0 flex items-center justify-center bg-background/80 backdrop-blur-sm rounded-lg z-50">
          <div className="flex flex-col items-center gap-3 text-center px-6">
            <div className="w-12 h-12 rounded-full bg-destructive/10 flex items-center justify-center">
              <AlertCircle className="w-6 h-6 text-destructive" />
            </div>
            <div>
              <h3 className="text-sm font-semibold text-foreground mb-1">Connection error</h3>
              <p className="text-xs text-muted-foreground">Unable to load table data</p>
            </div>
          </div>
        </div>
      )}

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
                  <TooltipProvider>
                    <Tooltip>
                      <TooltipTrigger asChild>
                        <div className={`w-5 h-5 rounded flex items-center justify-center ${entity.type === "fund" ? "bg-muted-foreground/20" : "bg-foreground/10"}`}>
                          {entity.type === "fund" ? (
                            <Landmark className="w-3 h-3 text-muted-foreground" />
                          ) : (
                            <Building2 className="w-3 h-3 text-foreground/70" />
                          )}
                        </div>
                      </TooltipTrigger>
                      <TooltipContent>
                        <p>{entity.type === "fund" ? "Fund" : "Company"}</p>
                      </TooltipContent>
                    </Tooltip>
                  </TooltipProvider>
                </TableCell>
                <TableCell className="font-medium text-foreground text-sm">
                  <div className="flex items-center gap-2 group/name">
                    <span>{entity.name}</span>
                    <button
                      onClick={(e) => handleCopy(entity.name, e)}
                      className="opacity-0 group-hover/name:opacity-100 transition-opacity p-1 hover:bg-primary/10 rounded"
                      title="Copy name"
                    >
                      <svg
                        xmlns="http://www.w3.org/2000/svg"
                        width="14"
                        height="14"
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="currentColor"
                        strokeWidth="2"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        className="text-muted-foreground hover:text-foreground"
                      >
                        <rect width="14" height="14" x="8" y="8" rx="2" ry="2" />
                        <path d="M4 16c-1.1 0-2-.9-2-2V4c0-1.1.9-2 2-2h10c1.1 0 2 .9 2 2" />
                      </svg>
                    </button>
                  </div>
                </TableCell>
                <TableCell className="font-mono text-xs text-muted-foreground">
                  <div className="flex items-center gap-2 group/org">
                    <span>{entity.orgNumber}</span>
                    {entity.orgNumber !== "-" && (
                      <button
                        onClick={(e) => handleCopy(entity.orgNumber, e)}
                        className="opacity-0 group-hover/org:opacity-100 transition-opacity p-1 hover:bg-primary/10 rounded"
                        title="Copy org number"
                      >
                        <svg
                          xmlns="http://www.w3.org/2000/svg"
                          width="14"
                          height="14"
                          viewBox="0 0 24 24"
                          fill="none"
                          stroke="currentColor"
                          strokeWidth="2"
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          className="text-muted-foreground hover:text-foreground"
                        >
                          <rect width="14" height="14" x="8" y="8" rx="2" ry="2" />
                          <path d="M4 16c-1.1 0-2-.9-2-2V4c0-1.1.9-2 2-2h10c1.1 0 2 .9 2 2" />
                        </svg>
                      </button>
                    )}
                  </div>
                </TableCell>
                <TableCell>
                  <Badge variant="secondary" className="text-xs font-normal bg-secondary/50">{entity.sector}</Badge>
                </TableCell>
                <TableCell className="font-mono text-xs text-muted-foreground">#{entity.cluster}</TableCell>
                <TableCell className="text-xs text-muted-foreground">{entity.ownership || "—"}</TableCell>
                <TableCell>
                  <Badge variant="outline" className="text-xs font-mono">{entity.country}</Badge>
                </TableCell>
                <TableCell 
                  className="p-0"
                  onClick={(e) => e.stopPropagation()}
                >
                  {entity.website ? (
                    <button
                      onClick={() => window.open(entity.website, '_blank')}
                      className="w-full h-full px-4 py-2 flex items-center justify-center opacity-100 transition-opacity hover:text-blue-500 hover:bg-secondary/50 rounded"
                      title={`Visit ${entity.website}`}
                    >
                      <ExternalLink className="w-4 h-4" />
                    </button>
                  ) : (
                    <div className="w-full h-full px-4 py-2 flex items-center justify-center text-muted-foreground opacity-30">
                    NA
                    </div>
                  )}
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
