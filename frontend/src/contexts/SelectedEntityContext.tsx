import { createContext, useContext, useState, ReactNode } from "react";

type SelectedEntityContextType = {
  selectedEntityId: string | null;
  setSelectedEntityId: (id: string | null) => void;
};

const SelectedEntityContext = createContext<SelectedEntityContextType | undefined>(undefined);

export function SelectedEntityProvider({ children }: { children: ReactNode }) {
  const [selectedEntityId, setSelectedEntityId] = useState<string | null>(null);

  return (
    <SelectedEntityContext.Provider value={{ selectedEntityId, setSelectedEntityId }}>
      {children}
    </SelectedEntityContext.Provider>
  );
}

export function useSelectedEntity() {
  const context = useContext(SelectedEntityContext);
  if (!context) {
    throw new Error("useSelectedEntity must be used within a SelectedEntityProvider");
  }
  return context;
}
