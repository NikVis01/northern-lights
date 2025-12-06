import { useCallback, useRef, useEffect, useState } from "react";
import ForceGraph2D, { ForceGraphMethods } from "react-force-graph-2d";
import { ZoomIn, ZoomOut, Maximize2 } from "lucide-react";
import { Button } from "./ui/button";
import { useTheme } from "./ThemeProvider";
import { useSelectedEntity } from "@/contexts/SelectedEntityContext";
import { useLanguage } from "@/contexts/LanguageContext";

interface Node {
  id: string;
  name: string;
  type: "company" | "fund";
  cluster?: number;
  val?: number;
  x?: number;
  y?: number;
  orgNumber?: string;
  sector?: string;
  country?: string;
}

interface Link {
  source: string;
  target: string;
  ownership?: number;
}

interface GraphData {
  nodes: Node[];
  links: Link[];
}



const NetworkGraph = () => {
  const fgRef = useRef<ForceGraphMethods>();
  const containerRef = useRef<HTMLDivElement>(null);
  const [dimensions, setDimensions] = useState({ width: 800, height: 400 });
  const [hoveredNode, setHoveredNode] = useState<Node | null>(null);
  const { theme } = useTheme();
  const { selectedEntityId, setSelectedEntityId } = useSelectedEntity();
  const { t } = useLanguage();
  
  // Determine if we're in dark mode
  const [isDark, setIsDark] = useState(true);

  // Graph data state
  const [graphData, setGraphData] = useState<GraphData>({ nodes: [], links: [] });

  // Fetch graph data
  useEffect(() => {
    const fetchGraphData = async () => {
      try {
        // Use proxy URL to avoid CORS
        const response = await fetch("/api/v1/search/all", {
          headers: {
            "access_token": "dev" // Using dev token for now as per plan
          }
        });
        
        if (!response.ok) {
          console.error("Failed to fetch graph data");
          return;
        }

        const data = await response.json();
        setGraphData(data);
      } catch (error) {
        console.error("Error fetching graph data:", error);
      }
    };

    fetchGraphData();
  }, []);
  
  useEffect(() => {
    const checkDarkMode = () => {
      if (theme === "system") {
        setIsDark(window.matchMedia("(prefers-color-scheme: dark)").matches);
      } else {
        setIsDark(theme === "dark");
      }
    };
    checkDarkMode();
    
    const mediaQuery = window.matchMedia("(prefers-color-scheme: dark)");
    mediaQuery.addEventListener("change", checkDarkMode);
    return () => mediaQuery.removeEventListener("change", checkDarkMode);
  }, [theme]);

  useEffect(() => {
    const updateDimensions = () => {
      if (containerRef.current) {
        setDimensions({
          width: containerRef.current.clientWidth,
          height: containerRef.current.clientHeight,
        });
      }
    };

    updateDimensions();
    window.addEventListener("resize", updateDimensions);
    return () => window.removeEventListener("resize", updateDimensions);
  }, []);

  // Focus on selected entity when it changes
  useEffect(() => {
    if (selectedEntityId && fgRef.current) {
      const node = graphData.nodes.find(n => n.id === selectedEntityId);
      if (node && typeof node.x === "number" && typeof node.y === "number") {
        fgRef.current.centerAt(node.x, node.y, 800);
        fgRef.current.zoom(2.5, 800);
      }
    }
  }, [selectedEntityId, graphData]);

  const handleZoomIn = useCallback(() => {
    if (fgRef.current) {
      const currentZoom = fgRef.current.zoom();
      fgRef.current.zoom(currentZoom * 1.5, 400);
    }
  }, []);

  const handleZoomOut = useCallback(() => {
    if (fgRef.current) {
      const currentZoom = fgRef.current.zoom();
      fgRef.current.zoom(currentZoom * 0.67, 400);
    }
  }, []);

  const handleCenter = useCallback(() => {
    fgRef.current?.zoomToFit(400, 50);
    setSelectedEntityId(null);
  }, [setSelectedEntityId]);

  const nodeCanvasObject = useCallback(
    (node: any, ctx: CanvasRenderingContext2D, globalScale: number) => {
      if (typeof node.x !== "number" || typeof node.y !== "number" || !isFinite(node.x) || !isFinite(node.y)) {
        return;
      }

      const nodeSize = node.val ? Math.sqrt(node.val) * 1.5 : 6;
      const isCompany = node.type === "company";
      const isSelected = node.id === selectedEntityId;

      // Theme-aware colors
      const companyGlow = isDark ? "rgba(180, 180, 190, 0.15)" : "rgba(50, 50, 70, 0.12)";
      const fundGlow = isDark ? "rgba(120, 120, 140, 0.15)" : "rgba(100, 100, 130, 0.12)";
      const companyFill = isDark ? "rgba(200, 200, 210, 0.9)" : "rgba(40, 40, 60, 0.85)";
      const fundFill = isDark ? "rgba(100, 100, 120, 0.8)" : "rgba(100, 100, 130, 0.7)";
      const labelColor = isDark ? "rgba(255, 255, 255, 0.7)" : "rgba(30, 30, 50, 0.8)";
      const selectedGlow = isDark ? "rgba(100, 180, 255, 0.6)" : "rgba(50, 130, 220, 0.5)";
      const selectedRing = isDark ? "rgba(100, 180, 255, 0.9)" : "rgba(50, 130, 220, 0.85)";

      // Draw selected highlight ring
      if (isSelected) {
        // Outer glow for selected
        const selectedGradient = ctx.createRadialGradient(
          node.x, node.y, 0,
          node.x, node.y, nodeSize * 4
        );
        selectedGradient.addColorStop(0, selectedGlow);
        selectedGradient.addColorStop(1, "rgba(0, 0, 0, 0)");
        ctx.beginPath();
        ctx.arc(node.x, node.y, nodeSize * 4, 0, 2 * Math.PI);
        ctx.fillStyle = selectedGradient;
        ctx.fill();

        // Selection ring
        ctx.beginPath();
        ctx.arc(node.x, node.y, nodeSize + 4, 0, 2 * Math.PI);
        ctx.strokeStyle = selectedRing;
        ctx.lineWidth = 2;
        ctx.stroke();
      }

      // Draw subtle glow
      const gradient = ctx.createRadialGradient(
        node.x, node.y, 0,
        node.x, node.y, nodeSize * 2.5
      );
      gradient.addColorStop(0, isCompany ? companyGlow : fundGlow);
      gradient.addColorStop(1, "rgba(0, 0, 0, 0)");
      ctx.beginPath();
      ctx.arc(node.x, node.y, nodeSize * 2.5, 0, 2 * Math.PI);
      ctx.fillStyle = gradient;
      ctx.fill();

      // Draw node
      ctx.beginPath();
      ctx.arc(node.x, node.y, nodeSize, 0, 2 * Math.PI);
      ctx.fillStyle = isCompany ? companyFill : fundFill;
      ctx.fill();

      // Draw label on hover, selected, or if zoomed in
      if (globalScale > 0.8 || isSelected) {
        const fontSize = Math.max(9 / globalScale, 3);
        ctx.font = `${isSelected ? "bold " : ""}${fontSize}px Inter, sans-serif`;
        ctx.textAlign = "center";
        ctx.textBaseline = "top";
        ctx.fillStyle = isSelected ? selectedRing : labelColor;
        ctx.fillText(node.name, node.x, node.y + nodeSize + 4);
      }
    },
    [isDark, selectedEntityId]
  );

  const handleNodeClick = useCallback((node: any) => {
    setSelectedEntityId(node.id === selectedEntityId ? null : node.id);
  }, [selectedEntityId, setSelectedEntityId]);

  const linkColor = isDark ? "rgba(60, 60, 80, 0.4)" : "rgba(150, 150, 170, 0.35)";
  const particleColor = isDark ? "rgba(150, 150, 170, 0.6)" : "rgba(80, 80, 120, 0.5)";

  return (
    <div className="relative h-full" ref={containerRef}>
      <div className="absolute inset-0 rounded-lg overflow-hidden">
        <ForceGraph2D
          ref={fgRef}
          graphData={graphData}
          width={dimensions.width}
          height={dimensions.height}
          nodeRelSize={5}
          nodeCanvasObject={nodeCanvasObject}
          linkColor={() => linkColor}
          linkWidth={1}
          linkDirectionalParticles={1}
          linkDirectionalParticleWidth={2}
          linkDirectionalParticleSpeed={0.003}
          linkDirectionalParticleColor={() => particleColor}
          backgroundColor="transparent"
          onNodeHover={(node) => setHoveredNode(node as Node | null)}
          onNodeClick={handleNodeClick}
          cooldownTicks={100}
          d3AlphaDecay={0.02}
          d3VelocityDecay={0.3}
        />
      </div>

      {/* Controls */}
      <div className="absolute top-3 right-3 flex flex-col gap-1">
        <Button variant="ghost" size="icon" onClick={handleZoomIn} className="h-7 w-7">
          <ZoomIn className="h-3.5 w-3.5" />
        </Button>
        <Button variant="ghost" size="icon" onClick={handleZoomOut} className="h-7 w-7">
          <ZoomOut className="h-3.5 w-3.5" />
        </Button>
        <Button variant="ghost" size="icon" onClick={handleCenter} className="h-7 w-7">
          <Maximize2 className="h-3.5 w-3.5" />
        </Button>
      </div>

      {/* Legend */}
      <div className="absolute bottom-3 left-3 flex items-center gap-4 text-xs text-muted-foreground font-mono">
        <div className="flex items-center gap-1.5">
          <div className="w-2 h-2 rounded-full bg-foreground/70" />
          <span>{t("companies") as string}</span>
        </div>
        <div className="flex items-center gap-1.5">
          <div className="w-2 h-2 rounded-full bg-muted-foreground/60" />
          <span>{t("investors") as string}</span>
        </div>
      </div>

      {/* Hover Info */}
      {hoveredNode && (
        <div className="absolute top-3 left-3 px-3 py-2 rounded-md bg-card border border-border text-xs shadow-lg z-50 pointer-events-none">
          <p className="font-medium text-foreground">{hoveredNode.name}</p>
          <div className="text-muted-foreground font-mono space-y-0.5 mt-1">
            <p className="uppercase">{hoveredNode.type}</p>
            {hoveredNode.orgNumber && <p>Org: {hoveredNode.orgNumber}</p>}
            {hoveredNode.sector && <p>Sector: {hoveredNode.sector}</p>}
            {hoveredNode.country && <p>Country: {hoveredNode.country}</p>}
          </div>
        </div>
      )}
    </div>
  );
};

export default NetworkGraph;
