import { useRef, useMemo, useState } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import { Float, Line, Html } from '@react-three/drei';
import * as THREE from 'three';

interface NodeData {
  id: string;
  position: [number, number, number];
  label: string;
  type: 'company' | 'fund' | 'person';
  connections: string[];
}

// Generate mock ownership network data
const generateNetworkData = (): NodeData[] => {
  const nodes: NodeData[] = [
    { id: 'fund1', position: [0, 2, 0], label: 'Nordic Capital', type: 'fund', connections: ['comp1', 'comp2', 'comp3'] },
    { id: 'fund2', position: [-3, 1, 1], label: 'EQT Partners', type: 'fund', connections: ['comp2', 'comp4'] },
    { id: 'fund3', position: [3, 1, -1], label: 'Investor AB', type: 'fund', connections: ['comp1', 'comp5'] },
    { id: 'comp1', position: [-1, -1, 2], label: 'Volvo', type: 'company', connections: [] },
    { id: 'comp2', position: [1, 0, -2], label: 'Ericsson', type: 'company', connections: [] },
    { id: 'comp3', position: [-2, -2, 0], label: 'H&M', type: 'company', connections: [] },
    { id: 'comp4', position: [2, -1, 1], label: 'Spotify', type: 'company', connections: [] },
    { id: 'comp5', position: [0, -2, -1], label: 'Atlas Copco', type: 'company', connections: [] },
    { id: 'person1', position: [-4, 0, -2], label: 'Wallenberg', type: 'person', connections: ['fund3', 'comp1'] },
    { id: 'person2', position: [4, 0, 2], label: 'Persson', type: 'person', connections: ['comp3'] },
  ];
  return nodes;
};

interface NodeProps {
  node: NodeData;
  isHovered: boolean;
  onHover: (id: string | null) => void;
}

function Node({ node, isHovered, onHover }: NodeProps) {
  const meshRef = useRef<THREE.Mesh>(null);
  const [localHover, setLocalHover] = useState(false);
  
  const color = useMemo(() => {
    switch (node.type) {
      case 'fund': return '#ffffff';
      case 'company': return '#6b7280';
      case 'person': return '#4b5563';
      default: return '#ffffff';
    }
  }, [node.type]);

  const size = node.type === 'fund' ? 0.25 : node.type === 'company' ? 0.2 : 0.15;

  useFrame((state) => {
    if (meshRef.current) {
      const scale = localHover || isHovered ? 1.3 : 1;
      meshRef.current.scale.lerp(new THREE.Vector3(scale, scale, scale), 0.1);
    }
  });

  return (
    <Float speed={2} rotationIntensity={0.2} floatIntensity={0.5}>
      <group position={node.position}>
        <mesh
          ref={meshRef}
          onPointerEnter={() => { setLocalHover(true); onHover(node.id); }}
          onPointerLeave={() => { setLocalHover(false); onHover(null); }}
        >
          <sphereGeometry args={[size, 32, 32]} />
          <meshStandardMaterial
            color={color}
            emissive={color}
            emissiveIntensity={localHover || isHovered ? 0.8 : 0.3}
            transparent
            opacity={0.9}
          />
        </mesh>
        
        {/* Glow effect */}
        <mesh scale={1.5}>
          <sphereGeometry args={[size, 16, 16]} />
          <meshBasicMaterial
            color={color}
            transparent
            opacity={localHover || isHovered ? 0.15 : 0.05}
          />
        </mesh>
        
        {/* Label - 2D HTML overlay */}
        {(localHover || isHovered) && (
          <Html
            position={[0, size + 0.3, 0]}
            center
            style={{
              pointerEvents: 'none',
              whiteSpace: 'nowrap',
            }}
          >
            <div className="px-2 py-1 rounded bg-background/80 backdrop-blur-sm border border-border text-foreground text-xs font-mono">
              {node.label}
            </div>
          </Html>
        )}
      </group>
    </Float>
  );
}

interface EdgeProps {
  start: [number, number, number];
  end: [number, number, number];
  isHighlighted: boolean;
}

function Edge({ start, end, isHighlighted }: EdgeProps) {
  const points = useMemo(() => {
    const curve = new THREE.QuadraticBezierCurve3(
      new THREE.Vector3(...start),
      new THREE.Vector3(
        (start[0] + end[0]) / 2,
        (start[1] + end[1]) / 2 + 0.5,
        (start[2] + end[2]) / 2
      ),
      new THREE.Vector3(...end)
    );
    return curve.getPoints(20);
  }, [start, end]);

  return (
    <Line
      points={points}
      color={isHighlighted ? "#ffffff" : "#374151"}
      lineWidth={isHighlighted ? 2 : 1}
      transparent
      opacity={isHighlighted ? 0.8 : 0.3}
    />
  );
}

function NetworkScene() {
  const groupRef = useRef<THREE.Group>(null);
  const [hoveredNode, setHoveredNode] = useState<string | null>(null);
  
  const nodes = useMemo(() => generateNetworkData(), []);
  
  const edges = useMemo(() => {
    const edgeList: { start: [number, number, number]; end: [number, number, number]; sourceId: string; targetId: string }[] = [];
    nodes.forEach(node => {
      node.connections.forEach(targetId => {
        const targetNode = nodes.find(n => n.id === targetId);
        if (targetNode) {
          edgeList.push({
            start: node.position,
            end: targetNode.position,
            sourceId: node.id,
            targetId: targetId
          });
        }
      });
    });
    return edgeList;
  }, [nodes]);

  useFrame((state) => {
    if (groupRef.current) {
      groupRef.current.rotation.y = state.clock.elapsedTime * 0.05;
    }
  });

  const isNodeHighlighted = (nodeId: string) => {
    if (!hoveredNode) return false;
    if (nodeId === hoveredNode) return true;
    const hoveredNodeData = nodes.find(n => n.id === hoveredNode);
    if (hoveredNodeData?.connections.includes(nodeId)) return true;
    const node = nodes.find(n => n.id === nodeId);
    if (node?.connections.includes(hoveredNode)) return true;
    return false;
  };

  const isEdgeHighlighted = (sourceId: string, targetId: string) => {
    if (!hoveredNode) return false;
    return sourceId === hoveredNode || targetId === hoveredNode;
  };

  return (
    <group ref={groupRef}>
      {/* Edges */}
      {edges.map((edge, i) => (
        <Edge
          key={i}
          start={edge.start}
          end={edge.end}
          isHighlighted={isEdgeHighlighted(edge.sourceId, edge.targetId)}
        />
      ))}
      
      {/* Nodes */}
      {nodes.map(node => (
        <Node
          key={node.id}
          node={node}
          isHovered={isNodeHighlighted(node.id)}
          onHover={setHoveredNode}
        />
      ))}
      
      {/* Ambient particles */}
      <Particles />
    </group>
  );
}

function Particles() {
  const particlesRef = useRef<THREE.Points>(null);
  
  const [positions] = useMemo(() => {
    const positions = new Float32Array(200 * 3);
    for (let i = 0; i < 200; i++) {
      positions[i * 3] = (Math.random() - 0.5) * 15;
      positions[i * 3 + 1] = (Math.random() - 0.5) * 15;
      positions[i * 3 + 2] = (Math.random() - 0.5) * 15;
    }
    return [positions];
  }, []);

  useFrame((state) => {
    if (particlesRef.current) {
      particlesRef.current.rotation.y = state.clock.elapsedTime * 0.02;
    }
  });

  return (
    <points ref={particlesRef}>
      <bufferGeometry>
        <bufferAttribute
          attach="attributes-position"
          args={[positions, 3]}
        />
      </bufferGeometry>
      <pointsMaterial
        size={0.02}
        color="#4b5563"
        transparent
        opacity={0.4}
        sizeAttenuation
      />
    </points>
  );
}

export default function NetworkGraph() {
  return (
    <div className="w-full h-[600px] relative">
      <Canvas
        camera={{ position: [0, 0, 8], fov: 50 }}
        dpr={[1, 2]}
      >
        <color attach="background" args={['transparent']} />
        <ambientLight intensity={0.5} />
        <pointLight position={[10, 10, 10]} intensity={1} />
        <pointLight position={[-10, -10, -10]} intensity={0.5} />
        
        <NetworkScene />
      </Canvas>
      
      {/* Legend */}
      <div className="absolute bottom-6 left-6 flex flex-col gap-2 font-mono text-xs">
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded-full bg-foreground" />
          <span className="text-muted-foreground">Funds</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-2.5 h-2.5 rounded-full bg-muted-foreground" />
          <span className="text-muted-foreground">Companies</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 rounded-full bg-muted" />
          <span className="text-muted-foreground">Beneficial Owners</span>
        </div>
      </div>
      
      {/* Interaction hint */}
      <div className="absolute bottom-6 right-6 font-mono text-xs text-muted-foreground">
        Hover to explore connections
      </div>
    </div>
  );
}
