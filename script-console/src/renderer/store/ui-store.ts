import { create } from "zustand";

interface UiState {
  globalSearch: string;
  scriptsView: "cards" | "table";
  setGlobalSearch: (value: string) => void;
  setScriptsView: (value: "cards" | "table") => void;
}

export const useUiStore = create<UiState>((set) => ({
  globalSearch: "",
  scriptsView: "cards",
  setGlobalSearch: (globalSearch) => set({ globalSearch }),
  setScriptsView: (scriptsView) => set({ scriptsView }),
}));
